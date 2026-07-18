#!/usr/bin/env python3
"""
Nexus Auto-Updater - Automatic update checker and installer
Checks GitHub releases every 15 days and handles updates
"""

import threading
import time
import requests
import json
import logging
import shutil
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import subprocess
import sys
import os

logger = logging.getLogger(__name__)

# Configuration
GITHUB_API_URL = "https://api.github.com/repos/Andrian0123/Bober-drive"
CURRENT_VERSION = "3.0.0"
DEFAULT_CHECK_INTERVAL_DAYS = 15


@dataclass
class UpdateInfo:
    """Information about available update"""
    version: str
    release_date: str
    download_url: str
    changelog: str
    assets: list
    critical: bool = False
    size_bytes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AutoUpdater:
    """Automatic update checker and installer for Nexus Driver"""
    
    def __init__(
        self,
        check_interval_days: int = DEFAULT_CHECK_INTERVAL_DAYS,
        auto_install: bool = False,
        on_update_available: Optional[Callable] = None
    ):
        """
        Initialize AutoUpdater
        
        Args:
            check_interval_days: Days between update checks (default: 15)
            auto_install: Automatically install non-critical updates
            on_update_available: Callback when update is found
        """
        self.check_interval_days = check_interval_days
        self.auto_install = auto_install
        self.on_update_available = on_update_available
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_check: Optional[datetime] = None
        self.state_file = Path.home() / ".nexus" / "updater_state.json"
        self._load_state()
    
    def _load_state(self):
        """Load updater state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                    last_check_str = state.get("last_check")
                    if last_check_str:
                        self.last_check = datetime.fromisoformat(last_check_str)
                    logger.info(f"Loaded updater state: last check {self.last_check}")
            except Exception as e:
                logger.warning(f"Could not load updater state: {e}")
    
    def _save_state(self):
        """Save updater state to file"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    "last_check": self.last_check.isoformat() if self.last_check else None,
                    "current_version": CURRENT_VERSION,
                    "check_interval_days": self.check_interval_days
                }, f, indent=2)
            logger.debug("Saved updater state")
        except Exception as e:
            logger.warning(f"Could not save updater state: {e}")
    
    def check_for_updates(self) -> Optional[UpdateInfo]:
        """
        Check GitHub for new releases
        
        Returns:
            UpdateInfo if new version available, None otherwise
        """
        try:
            logger.info("Checking for Nexus Driver updates...")
            
            response = requests.get(
                f"{GITHUB_API_URL}/releases/latest",
                timeout=10,
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            response.raise_for_status()
            
            release = response.json()
            latest_version = release["tag_name"].lstrip("v")
            
            logger.info(f"Latest version: {latest_version}, Current: {CURRENT_VERSION}")
            
            if self._is_newer_version(latest_version, CURRENT_VERSION):
                update_info = UpdateInfo(
                    version=latest_version,
                    release_date=release["published_at"],
                    download_url=release["zipball_url"],
                    changelog=release.get("body", "No changelog available"),
                    assets=[asset["browser_download_url"] for asset in release.get("assets", [])],
                    critical="critical" in release.get("body", "").lower(),
                    size_bytes=release.get("assets", [{}])[0].get("size", 0) if release.get("assets") else 0
                )
                
                logger.info(f"New version available: {latest_version}")
                return update_info
            else:
                logger.info("No updates available")
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error checking for updates: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            return None
    
    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """
        Compare version strings (semver style)
        
        Args:
            version1: New version
            version2: Current version
            
        Returns:
            True if version1 is newer than version2
        """
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # Pad with zeros if needed
            while len(v1_parts) < 3:
                v1_parts.append(0)
            while len(v2_parts) < 3:
                v2_parts.append(0)
            
            return v1_parts > v2_parts
        except Exception as e:
            logger.warning(f"Error comparing versions: {e}")
            return False
    
    def download_update(self, update_info: UpdateInfo) -> Optional[Path]:
        """
        Download update package
        
        Args:
            update_info: Update information
            
        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            logger.info(f"Downloading update {update_info.version}...")
            
            # Create download directory
            download_dir = Path.home() / ".nexus" / "updates"
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # Download file
            response = requests.get(update_info.download_url, stream=True, timeout=300)
            response.raise_for_status()
            
            update_file = download_dir / f"nexus-{update_info.version}.zip"
            
            # Download with progress
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(update_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            logger.debug(f"Download progress: {progress:.1f}%")
            
            logger.info(f"Downloaded update to {update_file}")
            return update_file
            
        except Exception as e:
            logger.error(f"Failed to download update: {e}")
            return None
    
    def install_update(self, update_file: Path) -> bool:
        """
        Install update from downloaded file
        
        Args:
            update_file: Path to update package
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Installing update from {update_file}...")
            
            # Extract update
            extract_dir = update_file.parent / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(update_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find the root directory (GitHub zipballs have a wrapper folder)
            extracted_items = list(extract_dir.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                source_dir = extracted_items[0]
            else:
                source_dir = extract_dir
            
            # Get installation directory
            install_dir = Path(__file__).parent.parent
            
            # Backup current version
            backup_dir = Path.home() / ".nexus" / "backups" / f"nexus-{CURRENT_VERSION}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Backing up current version to {backup_dir}")
            
            # Copy driver directory to backup
            driver_backup = backup_dir / "driver"
            if (install_dir / "driver").exists():
                shutil.copytree(install_dir / "driver", driver_backup, dirs_exist_ok=True)
            
            # Install new version
            logger.info(f"Installing new version to {install_dir}")
            
            if (source_dir / "driver").exists():
                shutil.copytree(source_dir / "driver", install_dir / "driver", dirs_exist_ok=True)
            
            # Update VERSION.json
            version_file = install_dir / "VERSION.json"
            with open(version_file, 'w') as f:
                json.dump({
                    "version": CURRENT_VERSION,
                    "updated_at": datetime.now().isoformat(),
                    "auto_updated": True
                }, f, indent=2)
            
            logger.info("Update installed successfully")
            logger.warning("Restart Nexus Driver to apply changes")
            
            # Cleanup
            shutil.rmtree(extract_dir, ignore_errors=True)
            update_file.unlink(missing_ok=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to install update: {e}")
            return False
    
    def _update_loop(self):
        """Background update checker loop"""
        while self.running:
            try:
                # Check if it's time to check for updates
                should_check = (
                    self.last_check is None or
                    (datetime.now() - self.last_check).days >= self.check_interval_days
                )
                
                if should_check:
                    update_info = self.check_for_updates()
                    
                    if update_info:
                        # Call callback if provided
                        if self.on_update_available:
                            try:
                                self.on_update_available(update_info)
                            except Exception as e:
                                logger.error(f"Error in update callback: {e}")
                        
                        # Auto-install if enabled
                        if update_info.critical or self.auto_install:
                            logger.info("Auto-installing update...")
                            update_file = self.download_update(update_info)
                            
                            if update_file:
                                self.install_update(update_file)
                        else:
                            logger.info(
                                f"Update available: {update_info.version}. "
                                "Set auto_install=True to enable automatic updates."
                            )
                    
                    self.last_check = datetime.now()
                    self._save_state()
                
                # Sleep for 1 hour before next iteration
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                time.sleep(3600)
    
    def start(self):
        """Start background update checker"""
        if self.running:
            logger.warning("AutoUpdater already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True, name="AutoUpdater")
        self.thread.start()
        logger.info(f"AutoUpdater started (check every {self.check_interval_days} days)")
    
    def stop(self):
        """Stop background update checker"""
        if not self.running:
            return
        
        logger.info("Stopping AutoUpdater...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info("AutoUpdater stopped")
    
    def force_check(self) -> Optional[UpdateInfo]:
        """Force an immediate update check"""
        logger.info("Forcing update check...")
        update_info = self.check_for_updates()
        
        if update_info:
            self.last_check = datetime.now()
            self._save_state()
        
        return update_info
    
    def get_stats(self) -> Dict[str, Any]:
        """Get updater statistics"""
        return {
            "current_version": CURRENT_VERSION,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "check_interval_days": self.check_interval_days,
            "auto_install": self.auto_install,
            "running": self.running
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    def on_update(info: UpdateInfo):
        print(f"\n🎉 New version available: {info.version}")
        print(f"Released: {info.release_date}")
        print(f"Changelog:\n{info.changelog}")
    
    updater = AutoUpdater(
        check_interval_days=15,
        auto_install=False,
        on_update_available=on_update
    )
    
    # Force check immediately
    update = updater.force_check()
    
    if update:
        print(f"\nUpdate available: {update.version}")
        print("Run with auto_install=True to enable automatic updates")
    else:
        print("\nNo updates available")
