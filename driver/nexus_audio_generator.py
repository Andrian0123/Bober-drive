#!/usr/bin/env python3
"""
Audio Generator - Week 6 Implementation
Text-to-Speech synthesis for VaultCore entries
Supports multiple TTS engines (gTTS, Ollama, local)

Architecture:
- Multiple TTS backend support (gTTS, Ollama, pyttsx3)
- Batch processing with progress tracking
- MP3/WAV output with metadata
- Playlist generation (M3U format)
- Voice customization (speed, pitch, language)
- Cache management to avoid re-synthesis
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import os
import hashlib

logger = logging.getLogger(__name__)


class TTSEngine(Enum):
    """Available TTS engines"""
    GTTS = "gtts"  # Google Text-to-Speech (online)
    OLLAMA = "ollama"  # Local Ollama TTS
    PYTTSX3 = "pyttsx3"  # Local pyttsx3 (simple)


class AudioFormat(Enum):
    """Output audio formats"""
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"


class VoiceSettings:
    """Voice configuration"""
    def __init__(self, language: str = "en", speed: float = 1.0, 
                 pitch: float = 1.0, volume: float = 1.0):
        self.language = language
        self.speed = max(0.5, min(2.0, speed))  # Clamp 0.5-2.0
        self.pitch = max(0.5, min(2.0, pitch))  # Clamp 0.5-2.0
        self.volume = max(0.0, min(1.0, volume))  # Clamp 0.0-1.0


@dataclass
class AudioFile:
    """Represents a generated audio file"""
    file_id: str
    filename: str
    filepath: Path
    format: AudioFormat
    duration_seconds: Optional[float] = None
    bitrate: Optional[str] = None  # e.g., "128k"
    sample_rate: Optional[int] = None
    text_length: int = 0
    engine_used: str = "unknown"
    voice_settings: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source_entry_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "filepath": str(self.filepath),
            "format": self.format.value
        }


class AudioGenerator:
    """Main audio synthesis engine"""
    
    def __init__(self, output_dir: Path, engine: TTSEngine = TTSEngine.GTTS, 
                 vault_core=None):
        """
        Initialize Audio Generator
        
        Args:
            output_dir: Directory for audio files
            engine: TTS engine to use
            vault_core: Optional VaultCore instance
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.engine = engine
        self.vault_core = vault_core
        self.cache: Dict[str, AudioFile] = {}
        self.metadata_file = self.output_dir / "audio_metadata.json"
        
        self._load_metadata()
        logger.info(f"AudioGenerator initialized with {engine.value} engine")
    
    def synthesize(self, text: str, voice_settings: Optional[VoiceSettings] = None,
                   entry_id: Optional[str] = None, format: AudioFormat = AudioFormat.MP3) -> Optional[AudioFile]:
        """
        Synthesize text to audio
        
        Args:
            text: Text to synthesize
            voice_settings: Voice configuration
            entry_id: Optional entry ID for reference
            format: Output format
            
        Returns:
            AudioFile if successful
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for synthesis")
            return None
        
        # Check cache
        text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
        cache_key = f"{text_hash}_{self.engine.value}"
        
        if cache_key in self.cache:
            logger.debug(f"Using cached audio for text hash {text_hash}")
            return self.cache[cache_key]
        
        voice_settings = voice_settings or VoiceSettings()
        
        try:
            if self.engine == TTSEngine.GTTS:
                audio_file = self._synthesize_gtts(text, voice_settings, entry_id, format)
            elif self.engine == TTSEngine.OLLAMA:
                audio_file = self._synthesize_ollama(text, voice_settings, entry_id, format)
            elif self.engine == TTSEngine.PYTTSX3:
                audio_file = self._synthesize_pyttsx3(text, voice_settings, entry_id, format)
            else:
                logger.error(f"Unknown engine: {self.engine}")
                return None
            
            if audio_file:
                self.cache[cache_key] = audio_file
                self._save_metadata()
                return audio_file
        
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
        
        return None
    
    def _synthesize_gtts(self, text: str, voice_settings: VoiceSettings,
                        entry_id: Optional[str], format: AudioFormat) -> Optional[AudioFile]:
        """Synthesize using Google Text-to-Speech"""
        try:
            from gtts import gTTS
            
            # Limit text length
            if len(text) > 5000:
                text = text[:5000] + "..."
                logger.warning("Text truncated for gTTS (max 5000 chars)")
            
            # Create TTS object
            tts = gTTS(text=text, lang=voice_settings.language, slow=False)
            
            # Generate filename
            text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
            filename = f"audio_{text_hash}.{format.value}"
            filepath = self.output_dir / filename
            
            # Save
            tts.save(str(filepath))
            
            # Get file size (rough duration estimate)
            file_size = filepath.stat().st_size
            duration_estimate = (len(text) / 150) * 60  # Rough estimate
            
            audio_file = AudioFile(
                file_id=f"audio_{text_hash}",
                filename=filename,
                filepath=filepath,
                format=format,
                duration_seconds=duration_estimate,
                bitrate="128k",
                text_length=len(text),
                engine_used="gtts",
                voice_settings={
                    "language": voice_settings.language,
                    "speed": voice_settings.speed
                },
                source_entry_id=entry_id
            )
            
            logger.info(f"Generated audio: {filename}")
            return audio_file
        
        except ImportError:
            logger.error("gTTS not installed. Install with: pip install gtts")
            return None
        except Exception as e:
            logger.error(f"gTTS synthesis failed: {e}")
            return None
    
    def _synthesize_ollama(self, text: str, voice_settings: VoiceSettings,
                          entry_id: Optional[str], format: AudioFormat) -> Optional[AudioFile]:
        """Synthesize using Ollama TTS (local)"""
        try:
            import requests
            
            # This is a placeholder - actual Ollama integration would depend on their TTS API
            logger.warning("Ollama TTS not fully implemented yet, using fallback")
            
            # Fallback to pyttsx3
            return self._synthesize_pyttsx3(text, voice_settings, entry_id, format)
        
        except Exception as e:
            logger.error(f"Ollama synthesis failed: {e}")
            return None
    
    def _synthesize_pyttsx3(self, text: str, voice_settings: VoiceSettings,
                           entry_id: Optional[str], format: AudioFormat) -> Optional[AudioFile]:
        """Synthesize using pyttsx3 (local)"""
        try:
            import pyttsx3
            
            # Create engine
            engine = pyttsx3.init()
            
            # Configure voice settings
            engine.setProperty('rate', 150 * voice_settings.speed)
            engine.setProperty('volume', voice_settings.volume)
            
            # Generate filename
            text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
            filename = f"audio_{text_hash}.{format.value}"
            filepath = self.output_dir / filename
            
            # Save to file
            engine.save_to_file(text, str(filepath))
            engine.runAndWait()
            engine.stop()
            
            # Estimate duration
            duration_estimate = (len(text) / 150) * 60
            
            audio_file = AudioFile(
                file_id=f"audio_{text_hash}",
                filename=filename,
                filepath=filepath,
                format=format,
                duration_seconds=duration_estimate,
                text_length=len(text),
                engine_used="pyttsx3",
                voice_settings={
                    "language": voice_settings.language,
                    "speed": voice_settings.speed,
                    "volume": voice_settings.volume
                },
                source_entry_id=entry_id
            )
            
            logger.info(f"Generated audio: {filename}")
            return audio_file
        
        except ImportError:
            logger.error("pyttsx3 not installed. Install with: pip install pyttsx3")
            return None
        except Exception as e:
            logger.error(f"pyttsx3 synthesis failed: {e}")
            return None
    
    def batch_generate(self, entries: List[Tuple[str, str]], 
                      voice_settings: Optional[VoiceSettings] = None) -> List[AudioFile]:
        """
        Batch generate audio for multiple entries
        
        Args:
            entries: List of (entry_id, text) tuples
            voice_settings: Voice configuration
            
        Returns:
            List of generated AudioFile objects
        """
        audio_files = []
        total = len(entries)
        
        for idx, (entry_id, text) in enumerate(entries, 1):
            logger.info(f"Synthesizing {idx}/{total}: {entry_id[:50]}")
            
            audio_file = self.synthesize(
                text=text,
                voice_settings=voice_settings,
                entry_id=entry_id
            )
            
            if audio_file:
                audio_files.append(audio_file)
        
        logger.info(f"Batch generation complete: {len(audio_files)}/{total} successful")
        return audio_files
    
    def create_playlist(self, audio_files: List[AudioFile], 
                       playlist_name: str = "generated") -> Optional[Path]:
        """
        Create M3U playlist from audio files
        
        Args:
            audio_files: List of AudioFile objects
            playlist_name: Name for playlist
            
        Returns:
            Path to created playlist
        """
        try:
            playlist_path = self.output_dir / f"{playlist_name}.m3u"
            
            lines = [
                "#EXTM3U",
                f"# Generated: {datetime.utcnow().isoformat()}",
                f"# Total tracks: {len(audio_files)}"
            ]
            
            for audio_file in audio_files:
                duration = int(audio_file.duration_seconds or 0)
                title = audio_file.filename.replace('.mp3', '').replace('audio_', '')
                
                lines.append(f"#EXTINF:{duration},{title}")
                lines.append(audio_file.filename)
            
            playlist_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            logger.info(f"Created playlist: {playlist_path}")
            
            return playlist_path
        
        except Exception as e:
            logger.error(f"Failed to create playlist: {e}")
            return None
    
    def generate_for_vault_entry(self, entry_id: str, 
                                voice_settings: Optional[VoiceSettings] = None) -> Optional[AudioFile]:
        """
        Generate audio for a specific VaultCore entry
        
        Args:
            entry_id: Entry ID from VaultCore
            voice_settings: Voice settings
            
        Returns:
            AudioFile if successful
        """
        if not self.vault_core:
            logger.error("VaultCore not available")
            return None
        
        try:
            entry = self.vault_core.retrieve(entry_id)
            if not entry:
                logger.warning(f"Entry not found: {entry_id}")
                return None
            
            # Use title + content or summary
            text = entry.title
            if entry.summary:
                text += "\n\n" + entry.summary
            if entry.content and len(entry.content) < 3000:
                text += "\n\n" + entry.content
            
            audio_file = self.synthesize(
                text=text,
                voice_settings=voice_settings,
                entry_id=entry_id
            )
            
            # Update VaultCore with audio reference
            if audio_file and hasattr(entry, 'metadata'):
                try:
                    entry.metadata = entry.metadata or {}
                    entry.metadata['audio_file'] = str(audio_file.filepath)
                    entry.metadata['audio_id'] = audio_file.file_id
                    self.vault_core.store(entry)
                except:
                    pass
            
            return audio_file
        
        except Exception as e:
            logger.error(f"Failed to generate audio for {entry_id}: {e}")
            return None
    
    def batch_generate_from_vault(self, entry_ids: List[str],
                                 voice_settings: Optional[VoiceSettings] = None) -> List[AudioFile]:
        """Generate audio for multiple VaultCore entries"""
        audio_files = []
        
        for entry_id in entry_ids:
            audio_file = self.generate_for_vault_entry(entry_id, voice_settings)
            if audio_file:
                audio_files.append(audio_file)
        
        logger.info(f"Generated audio for {len(audio_files)}/{len(entry_ids)} entries")
        return audio_files
    
    def _load_metadata(self):
        """Load audio metadata from file"""
        if self.metadata_file.exists():
            try:
                data = json.loads(self.metadata_file.read_text(encoding='utf-8'))
                for key, value in data.items():
                    # Reconstruct AudioFile objects
                    if 'filepath' in value:
                        value['filepath'] = Path(value['filepath'])
                        if 'format' in value:
                            value['format'] = AudioFormat[value['format'].upper()]
                        # Create AudioFile from dict
                        audio_file = AudioFile(**value)
                        self.cache[key] = audio_file
                logger.debug(f"Loaded {len(self.cache)} cached audio files")
            except Exception as e:
                logger.warning(f"Failed to load metadata: {e}")
    
    def _save_metadata(self):
        """Save audio metadata to file"""
        try:
            data = {}
            for key, audio_file in self.cache.items():
                file_dict = audio_file.to_dict()
                data[key] = file_dict
            
            self.metadata_file.write_text(
                json.dumps(data, indent=2, default=str),
                encoding='utf-8'
            )
        except Exception as e:
            logger.warning(f"Failed to save metadata: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics"""
        total_size = sum(
            f.stat().st_size for f in self.output_dir.glob('*.mp3')
            if f.is_file()
        )
        
        return {
            "cached_files": len(self.cache),
            "total_audio_size_mb": round(total_size / (1024 * 1024), 2),
            "engine": self.engine.value,
            "output_directory": str(self.output_dir),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def cleanup_cache(self, max_age_days: int = 30) -> int:
        """Clean up old cached audio files"""
        from datetime import timedelta
        import time
        
        cutoff_time = time.time() - (max_age_days * 86400)
        removed = 0
        
        try:
            for audio_file in self.cache.values():
                if audio_file.filepath.exists():
                    mtime = audio_file.filepath.stat().st_mtime
                    if mtime < cutoff_time:
                        audio_file.filepath.unlink()
                        removed += 1
            
            logger.info(f"Cleaned up {removed} old audio files")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        
        return removed


if __name__ == "__main__":
    # Demo
    logging.basicConfig(level=logging.DEBUG)
    
    audio_dir = Path("./audio_output")
    generator = AudioGenerator(audio_dir, engine=TTSEngine.GTTS)
    
    # Example
    test_text = "This is a test of the audio generation system"
    audio_file = generator.synthesize(test_text)
    
    if audio_file:
        print(f"\nGenerated: {audio_file.filepath}")
        print(f"Duration: {audio_file.duration_seconds:.1f}s")
    else:
        print("Audio generation failed - check dependencies")
