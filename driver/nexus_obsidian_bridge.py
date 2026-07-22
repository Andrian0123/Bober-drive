#!/usr/bin/env python3
"""
Obsidian Bridge - Week 6 Implementation
Exports VaultCore knowledge graph to Obsidian vault format (.md files with wikilinks)

Architecture:
- Converts VaultEntry objects to Markdown files
- Transforms VaultEdge relationships into Obsidian wikilinks
- Generates YAML front matter with metadata
- Creates folder structure matching graph hierarchy
- Supports bidirectional relationship export
- Watch mode for continuous sync (future)
"""

import logging
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class LinkType(Enum):
    """Types of Obsidian links"""
    FORWARD = "forward"  # [Title](Page.md)
    BACKLINK = "backlink"  # Referenced by other notes
    BIDIRECTIONAL = "bidirectional"  # Two-way relationship


@dataclass
class ObsidianNote:
    """Represents a markdown note for Obsidian"""
    filename: str
    title: str
    content: str
    front_matter: Dict[str, Any]
    links: List[str] = None  # List of linked note filenames
    tags: List[str] = None
    folder_path: str = ""
    
    def to_markdown(self) -> str:
        """Generate markdown content with front matter"""
        # YAML front matter
        yaml_lines = ["---"]
        for key, value in self.front_matter.items():
            if isinstance(value, list):
                yaml_lines.append(f"{key}:")
                for item in value:
                    yaml_lines.append(f"  - {item}")
            elif isinstance(value, str) and '\n' in value:
                yaml_lines.append(f'{key}: |')
                for line in value.split('\n'):
                    yaml_lines.append(f'  {line}')
            else:
                yaml_lines.append(f"{key}: {value}")
        yaml_lines.append("---")
        
        markdown = '\n'.join(yaml_lines) + '\n\n'
        markdown += f"# {self.title}\n\n"
        markdown += self.content
        
        return markdown


class ObsidianBridge:
    """Main bridge for exporting to Obsidian format"""
    
    # Regex pattern to sanitize filenames
    INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')
    
    def __init__(self, vault_core=None):
        """
        Initialize Obsidian Bridge
        
        Args:
            vault_core: VaultCore instance to read from
        """
        self.vault_core = vault_core
        self.obsidian_path = None
        self.notes: Dict[str, ObsidianNote] = {}
        logger.info("ObsidianBridge initialized")
    
    def export_vault(self, output_dir: Path, filter_type: Optional[str] = None) -> bool:
        """
        Export entire VaultCore to Obsidian vault format
        
        Args:
            output_dir: Output directory for Obsidian vault
            filter_type: Optional entry type filter (e.g., "DOCUMENTATION")
            
        Returns:
            True if successful
        """
        if not self.vault_core:
            logger.error("VaultCore not available")
            return False
        
        try:
            self.obsidian_path = Path(output_dir)
            self.obsidian_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Starting export to {self.obsidian_path}")
            
            # Create folder structure
            self._create_folder_structure()
            
            # Get entries from VaultCore
            entries = self.vault_core.list_entries(limit=10000)
            
            # Convert entries to notes
            for entry in entries:
                if filter_type and entry.entry_type.value != filter_type:
                    continue
                
                note = self._entry_to_note(entry)
                if note:
                    self.notes[note.filename] = note
            
            # Get edges and create links
            edges = self.vault_core.list_edges() if hasattr(self.vault_core, 'list_edges') else []
            self._create_links(edges)
            
            # Write notes to files
            written = 0
            for note in self.notes.values():
                if self._write_note(note):
                    written += 1
            
            # Create index file
            self._create_index()
            
            logger.info(f"Export complete: {written} notes written")
            return True
        
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def _create_folder_structure(self):
        """Create standard Obsidian vault folder structure"""
        folders = [
            "001_Inbox",
            "002_Reference",
            "003_Projects",
            "004_Archive",
            "_Attachments",
            "_Templates"
        ]
        
        for folder in folders:
            (self.obsidian_path / folder).mkdir(exist_ok=True)
    
    def _entry_to_note(self, entry) -> Optional[ObsidianNote]:
        """Convert VaultEntry to ObsidianNote"""
        try:
            # Sanitize filename
            filename = self._sanitize_filename(entry.title)
            if not filename:
                filename = entry.entry_id
            
            # Determine folder based on entry type
            folder_path = self._get_folder_for_type(entry.entry_type.value)
            
            # Create front matter
            front_matter = {
                "id": entry.entry_id,
                "type": entry.entry_type.value,
                "created": entry.created_at,
                "modified": entry.modified_at,
                "author": entry.created_by,
                "tags": entry.tags if entry.tags else [],
                "access_level": entry.access_level.value
            }
            
            if entry.summary:
                front_matter["summary"] = entry.summary
            
            note = ObsidianNote(
                filename=f"{filename}.md",
                title=entry.title,
                content=entry.content or "",
                front_matter=front_matter,
                tags=entry.tags or [],
                folder_path=folder_path
            )
            
            return note
        
        except Exception as e:
            logger.debug(f"Failed to convert entry to note: {e}")
            return None
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title to valid filename"""
        # Remove invalid characters
        filename = self.INVALID_CHARS.sub('_', title)
        
        # Limit length
        filename = filename[:200]
        
        # Remove trailing spaces and dots
        filename = filename.rstrip('. ')
        
        return filename
    
    def _get_folder_for_type(self, entry_type: str) -> str:
        """Determine folder based on entry type"""
        type_mapping = {
            "DOCUMENTATION": "002_Reference",
            "RULE": "003_Projects",
            "PROJECT_METADATA": "003_Projects",
            "CODE": "003_Projects",
            "DECISION": "002_Reference",
            "MEMORY": "001_Inbox",
            "SKILL": "002_Reference",
            "WORKFLOW": "003_Projects",
            "CONFIG": "003_Projects",
            "RELATIONSHIP": "002_Reference"
        }
        
        return type_mapping.get(entry_type, "002_Reference")
    
    def _create_links(self, edges: List[Any]):
        """Create wikilinks from VaultEdges"""
        link_map: Dict[str, Set[str]] = {}
        
        for edge in edges:
            try:
                # Find notes for source and target
                source_id = edge.source_id
                target_id = edge.target_id
                relationship = edge.relationship_type
                
                # Map IDs to filenames
                source_filename = self._find_note_filename(source_id)
                target_filename = self._find_note_filename(target_id)
                
                if source_filename and target_filename:
                    if source_filename not in link_map:
                        link_map[source_filename] = set()
                    
                    # Create wikilink reference
                    link_text = f"[[{target_filename.replace('.md', '')}|{relationship}]]"
                    link_map[source_filename].add(link_text)
            
            except Exception as e:
                logger.debug(f"Failed to create link from edge: {e}")
        
        # Add links to notes
        for filename, links in link_map.items():
            if filename in self.notes:
                if self.notes[filename].content:
                    self.notes[filename].content += "\n\n## References\n\n"
                
                for link in sorted(links):
                    self.notes[filename].content += f"- {link}\n"
    
    def _find_note_filename(self, entry_id: str) -> Optional[str]:
        """Find note filename by entry ID"""
        for filename, note in self.notes.items():
            if note.front_matter.get("id") == entry_id:
                return filename
        return None
    
    def _write_note(self, note: ObsidianNote) -> bool:
        """Write note to markdown file"""
        try:
            if note.folder_path:
                note_path = self.obsidian_path / note.folder_path / note.filename
            else:
                note_path = self.obsidian_path / note.filename
            
            note_path.write_text(note.to_markdown(), encoding='utf-8')
            logger.debug(f"Wrote note: {note_path}")
            return True
        
        except Exception as e:
            logger.warning(f"Failed to write note {note.filename}: {e}")
            return False
    
    def _create_index(self):
        """Create index/README file for Obsidian vault"""
        try:
            index_content = """# Nexus Driver Knowledge Vault

This is an Obsidian vault exported from the Nexus Driver knowledge graph system.

## Structure

- **001_Inbox** — New notes and temporary entries
- **002_Reference** — Documentation and reference material
- **003_Projects** — Active projects and workflows
- **004_Archive** — Archived content
- **_Attachments** — Media and attachments
- **_Templates** — Note templates

## Features

- Full-text search: Use Obsidian's search feature to find content
- Graph view: Visualize relationships between notes
- Backlinks: See what references each note
- Tags: Organized by tags and entry types
- Time tracking: Each note includes creation and modification dates

## Integration

This vault is automatically synced from the Nexus Driver vault system.
Modifications here can be imported back into the system.

---

Last updated: {timestamp}
Total notes: {total}
"""
            
            index_content = index_content.format(
                timestamp=datetime.utcnow().isoformat(),
                total=len(self.notes)
            )
            
            index_path = self.obsidian_path / "README.md"
            index_path.write_text(index_content, encoding='utf-8')
            logger.info(f"Created index at {index_path}")
        
        except Exception as e:
            logger.warning(f"Failed to create index: {e}")
    
    def selective_export(self, output_dir: Path, entry_ids: List[str]) -> bool:
        """Export specific entries by ID"""
        if not self.vault_core:
            logger.error("VaultCore not available")
            return False
        
        try:
            self.obsidian_path = Path(output_dir)
            self.obsidian_path.mkdir(parents=True, exist_ok=True)
            
            # Fetch specific entries
            for entry_id in entry_ids:
                try:
                    entry = self.vault_core.retrieve(entry_id)
                    if entry:
                        note = self._entry_to_note(entry)
                        if note:
                            self.notes[note.filename] = note
                except:
                    pass
            
            # Write notes
            written = sum(1 for note in self.notes.values() if self._write_note(note))
            
            logger.info(f"Selective export complete: {written} notes")
            return True
        
        except Exception as e:
            logger.error(f"Selective export failed: {e}")
            return False
    
    def export_by_type(self, output_dir: Path, entry_type: str) -> bool:
        """Export all entries of specific type"""
        return self.export_vault(output_dir, filter_type=entry_type)
    
    def create_markdown_index(self, output_path: Path) -> bool:
        """Create a markdown index of all exported notes"""
        try:
            index_lines = ["# Notes Index\n"]
            
            # Group by folder
            by_folder: Dict[str, List[ObsidianNote]] = {}
            for note in self.notes.values():
                folder = note.folder_path or "Root"
                if folder not in by_folder:
                    by_folder[folder] = []
                by_folder[folder].append(note)
            
            # Create index
            for folder in sorted(by_folder.keys()):
                index_lines.append(f"\n## {folder}\n")
                for note in sorted(by_folder[folder], key=lambda n: n.title):
                    safe_filename = note.filename.replace("'", "\\'")
                    index_lines.append(f"- [[{note.filename.replace('.md', '')}|{note.title}]]")
            
            output_path.write_text('\n'.join(index_lines), encoding='utf-8')
            logger.info(f"Created markdown index at {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False
    
    def export_graph_structure(self, output_path: Path) -> bool:
        """Export graph structure as JSON for graph visualization"""
        try:
            if not self.vault_core or not hasattr(self.vault_core, 'list_edges'):
                logger.warning("Cannot export graph without edge information")
                return False
            
            edges = self.vault_core.list_edges()
            nodes = []
            links = []
            
            # Create nodes from entries
            for note in self.notes.values():
                nodes.append({
                    "id": note.front_matter.get("id"),
                    "title": note.title,
                    "type": note.front_matter.get("type", "unknown"),
                    "url": f"{note.folder_path}/{note.filename}" if note.folder_path else note.filename
                })
            
            # Create links from edges
            for edge in edges:
                links.append({
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "relationship": edge.relationship_type,
                    "weight": edge.weight if hasattr(edge, 'weight') else 1.0
                })
            
            graph_data = {
                "nodes": nodes,
                "links": links,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            output_path.write_text(json.dumps(graph_data, indent=2), encoding='utf-8')
            logger.info(f"Exported graph structure to {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export graph: {e}")
            return False
    
    def validate_obsidian_format(self) -> Dict[str, Any]:
        """Validate exported vault format"""
        issues = []
        warnings = []
        
        for note in self.notes.values():
            # Check for broken wikilinks
            wikilinks = re.findall(r'\[\[([^\]]+)\]\]', note.content)
            for link in wikilinks:
                target = link.split('|')[0].strip()
                if not any(n.filename.startswith(target) for n in self.notes.values()):
                    warnings.append(f"Potential broken link: {link} in {note.filename}")
            
            # Check front matter
            if not note.front_matter.get("id"):
                issues.append(f"Missing ID in {note.filename}")
            
            # Check title
            if not note.title:
                issues.append(f"Missing title in {note.filename}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_notes": len(self.notes),
            "validation_time": datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    # Demo
    import sys
    logging.basicConfig(level=logging.DEBUG)
    
    output_dir = Path("./obsidian_export")
    bridge = ObsidianBridge()
    
    print("Obsidian Bridge ready")
    print(f"Would export to: {output_dir}")
    print("To export: bridge.export_vault(output_dir)")
