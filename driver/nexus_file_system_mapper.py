#!/usr/bin/env python3
"""
File System Mapper - Week 4 Implementation
Scans and indexes project file structure with .gitignore support
Stores project metadata in VaultCore for contextual awareness

Architecture:
- Recursive directory scanning with .gitignore/negignore support
- File classification (code/docs/config/media/other)
- Folder role detection (pages, components, libs, tests, etc.)
- Project metadata stored as PROJECT_METADATA entries in VaultCore
- Lightweight dependency graph for folder relationships
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import fnmatch
import os

logger = logging.getLogger(__name__)


class FileType(Enum):
    """Classification of files"""
    PYTHON_CODE = "python_code"
    JAVASCRIPT_CODE = "javascript_code"
    TYPESCRIPT_CODE = "typescript_code"
    JAVA_CODE = "java_code"
    CSHARP_CODE = "csharp_code"
    GO_CODE = "go_code"
    RUST_CODE = "rust_code"
    CCODE = "c_code"
    SQL = "sql"
    CONFIG = "config"
    MARKDOWN = "markdown"
    HTML = "html"
    CSS = "css"
    JSON_FILE = "json"
    YAML = "yaml"
    TOML = "toml"
    XML = "xml"
    DOCKERFILE = "dockerfile"
    MAKEFILE = "makefile"
    SHELL_SCRIPT = "shell_script"
    BINARY = "binary"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"


class FolderRole(Enum):
    """Detected role of folders"""
    PAGES = "pages"  # Frontend pages/routes
    COMPONENTS = "components"  # Reusable components
    LIBRARIES = "libraries"  # Shared libraries
    TESTS = "tests"  # Test suites
    FIXTURES = "fixtures"  # Test fixtures/data
    CONFIGS = "configs"  # Configuration files
    DOCS = "docs"  # Documentation
    BUILD = "build"  # Build outputs
    DIST = "dist"  # Distribution files
    NODE_MODULES = "node_modules"  # Dependencies
    UTILS = "utils"  # Utility functions
    SERVICES = "services"  # Business logic services
    MODELS = "models"  # Data models/schemas
    CONTROLLERS = "controllers"  # API controllers
    HOOKS = "hooks"  # React hooks or similar
    MIDDLEWARE = "middleware"  # Middleware functions
    TYPES = "types"  # Type definitions
    CONSTANTS = "constants"  # Constants
    OTHER = "other"


@dataclass
class FileInfo:
    """Information about a single file"""
    path: Path
    relative_path: str
    size: int
    file_type: FileType
    language: Optional[str] = None
    line_count: Optional[int] = None
    last_modified: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "path": str(self.path),
            "relative_path": str(self.relative_path),
            "file_type": self.file_type.value
        }


@dataclass
class FolderInfo:
    """Information about a folder"""
    path: Path
    relative_path: str
    name: str
    role: FolderRole
    file_count: int
    subfolder_count: int
    total_size: int
    contains_files: List[str] = field(default_factory=list)  # relative paths
    children: List[str] = field(default_factory=list)  # subfolder names
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "path": str(self.path),
            "relative_path": str(self.relative_path),
            "role": self.role.value
        }


class GitignoreParser:
    """Parse and apply .gitignore rules"""
    
    def __init__(self, root_path: Path):
        self.root_path = Path(root_path)
        self.patterns: List[Tuple[str, bool]] = []  # (pattern, is_negation)
        self._load_gitignore()
    
    def _load_gitignore(self):
        """Load .gitignore patterns"""
        gitignore_path = self.root_path / ".gitignore"
        if gitignore_path.exists():
            try:
                content = gitignore_path.read_text(encoding='utf-8')
                for line in content.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    is_negation = line.startswith('!')
                    if is_negation:
                        line = line[1:]
                    
                    self.patterns.append((line, is_negation))
                
                logger.debug(f"Loaded {len(self.patterns)} gitignore patterns")
            except Exception as e:
                logger.warning(f"Failed to parse .gitignore: {e}")
    
    def should_ignore(self, path: Path, is_dir: bool = False) -> bool:
        """Check if path should be ignored"""
        relative = path.relative_to(self.root_path)
        path_str = str(relative).replace('\\', '/')
        
        ignored = False
        for pattern, is_negation in self.patterns:
            if self._matches_pattern(path_str, pattern, is_dir):
                ignored = not is_negation
        
        return ignored
    
    def _matches_pattern(self, path: str, pattern: str, is_dir: bool) -> bool:
        """Check if path matches gitignore pattern"""
        if pattern.endswith('/'):
            if not is_dir:
                return False
            pattern = pattern[:-1]
        
        if '/' in pattern:
            # Full path pattern
            return fnmatch.fnmatch(path, pattern)
        else:
            # Match any component
            for component in path.split('/'):
                if fnmatch.fnmatch(component, pattern):
                    return True
        
        return False


class FileSystemMapper:
    """Main file system mapping engine"""
    
    COMMON_IGNORE_DIRS = {
        '.git', '.gitignore', '.venv', 'venv', 'env',
        'node_modules', '__pycache__', '.pytest_cache',
        '.tox', 'dist', 'build', '*.egg-info',
        '.idea', '.vscode', '.DS_Store',
        '.nexus', '.cache', 'tmp', 'temp'
    }
    
    FILE_TYPE_MAPPING = {
        # Python
        '.py': FileType.PYTHON_CODE,
        # JavaScript/TypeScript
        '.js': FileType.JAVASCRIPT_CODE,
        '.jsx': FileType.JAVASCRIPT_CODE,
        '.ts': FileType.TYPESCRIPT_CODE,
        '.tsx': FileType.TYPESCRIPT_CODE,
        # Java
        '.java': FileType.JAVA_CODE,
        # C#
        '.cs': FileType.CSHARP_CODE,
        # Go
        '.go': FileType.GO_CODE,
        # Rust
        '.rs': FileType.RUST_CODE,
        # C
        '.c': FileType.CCODE,
        '.h': FileType.CCODE,
        # SQL
        '.sql': FileType.SQL,
        # Markup
        '.md': FileType.MARKDOWN,
        '.html': FileType.HTML,
        '.htm': FileType.HTML,
        '.css': FileType.CSS,
        '.scss': FileType.CSS,
        '.less': FileType.CSS,
        # Data
        '.json': FileType.JSON_FILE,
        '.yaml': FileType.YAML,
        '.yml': FileType.YAML,
        '.toml': FileType.TOML,
        '.xml': FileType.XML,
        # Docker & Build
        'Dockerfile': FileType.DOCKERFILE,
        'Makefile': FileType.MAKEFILE,
        # Scripts
        '.sh': FileType.SHELL_SCRIPT,
        '.ps1': FileType.SHELL_SCRIPT,
        '.bat': FileType.SHELL_SCRIPT,
        # Media
        '.png': FileType.IMAGE,
        '.jpg': FileType.IMAGE,
        '.jpeg': FileType.IMAGE,
        '.gif': FileType.IMAGE,
        '.svg': FileType.IMAGE,
        '.mp4': FileType.VIDEO,
        '.webm': FileType.VIDEO,
        '.mp3': FileType.AUDIO,
        '.wav': FileType.AUDIO,
        '.m4a': FileType.AUDIO,
        # Archives
        '.zip': FileType.ARCHIVE,
        '.tar': FileType.ARCHIVE,
        '.gz': FileType.ARCHIVE,
        '.rar': FileType.ARCHIVE,
        '.7z': FileType.ARCHIVE,
    }
    
    FOLDER_ROLE_PATTERNS = {
        FolderRole.PAGES: ['pages', 'page', 'screens', 'views'],
        FolderRole.COMPONENTS: ['components', 'component', 'cmps', 'widgets'],
        FolderRole.LIBRARIES: ['lib', 'libs', 'libraries', 'packages'],
        FolderRole.TESTS: ['tests', 'test', '__tests__', 'specs', 'spec'],
        FolderRole.FIXTURES: ['fixtures', 'fixture', 'data', 'testdata'],
        FolderRole.CONFIGS: ['config', 'configs', 'conf', 'settings', '.config'],
        FolderRole.DOCS: ['docs', 'doc', 'documentation'],
        FolderRole.BUILD: ['build', 'dist', 'out', '.build'],
        FolderRole.UTILS: ['utils', 'util', 'helpers', 'helper', 'common'],
        FolderRole.SERVICES: ['services', 'service', 'api', 'server'],
        FolderRole.MODELS: ['models', 'model', 'schemas', 'schema'],
        FolderRole.CONTROLLERS: ['controllers', 'controller', 'handlers'],
        FolderRole.HOOKS: ['hooks', 'hook'],
        FolderRole.MIDDLEWARE: ['middleware', 'middlewares'],
        FolderRole.TYPES: ['types', 'type', 'interfaces', 'interface'],
        FolderRole.CONSTANTS: ['constants', 'constant', 'consts'],
    }
    
    def __init__(self, project_root: Path, vault_core=None):
        """
        Initialize File System Mapper
        
        Args:
            project_root: Root path of project
            vault_core: Optional VaultCore instance for storing metadata
        """
        self.project_root = Path(project_root)
        self.vault_core = vault_core
        self.gitignore_parser = GitignoreParser(self.project_root)
        
        self.files: Dict[str, FileInfo] = {}
        self.folders: Dict[str, FolderInfo] = {}
        self.stats = {
            "total_files": 0,
            "total_size": 0,
            "by_type": {},
            "by_language": {},
            "by_role": {}
        }
        
        logger.info(f"FileSystemMapper initialized for {self.project_root}")
    
    def scan_project(self) -> Dict[str, FileInfo]:
        """
        Scan entire project and build file/folder index
        
        Returns:
            Dictionary of relative_path -> FileInfo
        """
        logger.info("Starting project file system scan...")
        
        self.files = {}
        self.folders = {}
        self.stats = {
            "total_files": 0,
            "total_size": 0,
            "by_type": {},
            "by_language": {},
            "by_role": {}
        }
        
        # Recursive scan
        self._scan_directory(self.project_root)
        
        # Build folder hierarchy
        self._analyze_folders()
        
        logger.info(f"Scan complete: {len(self.files)} files, {len(self.folders)} folders")
        return self.files
    
    def _scan_directory(self, directory: Path, depth: int = 0):
        """Recursively scan directory"""
        if depth > 20:  # Safety limit
            logger.warning(f"Max directory depth reached at {directory}")
            return
        
        try:
            for entry in sorted(directory.iterdir()):
                # Check if should ignore
                if self.gitignore_parser.should_ignore(entry, entry.is_dir()):
                    continue
                if entry.name in self.COMMON_IGNORE_DIRS:
                    continue
                if entry.name.startswith('.') and entry.is_dir():
                    continue
                
                if entry.is_file():
                    self._process_file(entry)
                elif entry.is_dir():
                    self._scan_directory(entry, depth + 1)
        
        except PermissionError:
            logger.debug(f"Permission denied for {directory}")
        except Exception as e:
            logger.warning(f"Error scanning {directory}: {e}")
    
    def _process_file(self, file_path: Path):
        """Process single file"""
        try:
            relative = file_path.relative_to(self.project_root)
            relative_str = str(relative).replace('\\', '/')
            
            file_type = self._classify_file(file_path)
            language = self._detect_language(file_type)
            
            size = file_path.stat().st_size
            last_mod = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            
            # Try to count lines for code files
            line_count = None
            if file_type in [FileType.PYTHON_CODE, FileType.JAVASCRIPT_CODE, 
                            FileType.TYPESCRIPT_CODE, FileType.MARKDOWN]:
                try:
                    line_count = sum(1 for _ in file_path.open('r', encoding='utf-8', errors='ignore'))
                except:
                    pass
            
            file_info = FileInfo(
                path=file_path,
                relative_path=relative_str,
                size=size,
                file_type=file_type,
                language=language,
                line_count=line_count,
                last_modified=last_mod,
                created_at=datetime.utcnow().isoformat()
            )
            
            self.files[relative_str] = file_info
            
            # Update stats
            self.stats["total_files"] += 1
            self.stats["total_size"] += size
            
            file_type_str = file_type.value
            self.stats["by_type"][file_type_str] = self.stats["by_type"].get(file_type_str, 0) + 1
            
            if language:
                self.stats["by_language"][language] = self.stats["by_language"].get(language, 0) + 1
        
        except Exception as e:
            logger.debug(f"Error processing file {file_path}: {e}")
    
    def _classify_file(self, file_path: Path) -> FileType:
        """Classify file by extension"""
        suffix = file_path.suffix.lower()
        
        # Check by full filename first (for files like Dockerfile, Makefile)
        if file_path.name in self.FILE_TYPE_MAPPING:
            return self.FILE_TYPE_MAPPING[file_path.name]
        
        # Then by extension
        if suffix in self.FILE_TYPE_MAPPING:
            return self.FILE_TYPE_MAPPING[suffix]
        
        # Binary detection
        if not suffix or suffix in ['.bin', '.exe', '.dll', '.so', '.o']:
            return FileType.BINARY
        
        return FileType.UNKNOWN
    
    def _detect_language(self, file_type: FileType) -> Optional[str]:
        """Detect programming language from file type"""
        language_map = {
            FileType.PYTHON_CODE: "python",
            FileType.JAVASCRIPT_CODE: "javascript",
            FileType.TYPESCRIPT_CODE: "typescript",
            FileType.JAVA_CODE: "java",
            FileType.CSHARP_CODE: "csharp",
            FileType.GO_CODE: "go",
            FileType.RUST_CODE: "rust",
            FileType.CCODE: "c",
            FileType.SQL: "sql",
        }
        return language_map.get(file_type)
    
    def _analyze_folders(self):
        """Analyze folder structure and detect roles"""
        folder_cache = {}
        
        for file_rel in self.files.keys():
            parts = Path(file_rel).parts
            
            for i, part in enumerate(parts[:-1]):  # Exclude filename
                folder_path = Path(*parts[:i+1])
                folder_path_abs = self.project_root / folder_path
                folder_key = str(folder_path).replace('\\', '/')
                
                if folder_key not in folder_cache:
                    role = self._detect_folder_role(part)
                    folder_cache[folder_key] = FolderInfo(
                        path=folder_path_abs,
                        relative_path=folder_key,
                        name=part,
                        role=role,
                        file_count=0,
                        subfolder_count=0,
                        total_size=0
                    )
                
                # Update folder stats
                folder_cache[folder_key].file_count += 1
                folder_cache[folder_key].total_size += self.files[file_rel].size
        
        self.folders = folder_cache
        
        # Update role statistics
        for folder in self.folders.values():
            role_str = folder.role.value
            self.stats["by_role"][role_str] = self.stats["by_role"].get(role_str, 0) + 1
    
    def _detect_folder_role(self, folder_name: str) -> FolderRole:
        """Detect folder role from name"""
        folder_lower = folder_name.lower()
        
        for role, patterns in self.FOLDER_ROLE_PATTERNS.items():
            if folder_lower in patterns or any(
                fnmatch.fnmatch(folder_lower, p.replace('*', '*').lower()) 
                for p in patterns
            ):
                return role
        
        return FolderRole.OTHER
    
    def save_to_vault(self):
        """Save file system metadata to VaultCore"""
        if not self.vault_core:
            logger.warning("VaultCore not available, skipping save")
            return
        
        try:
            from vault_core import VaultEntry, VaultEntryType
            
            # Save folder structure
            for folder_key, folder_info in self.folders.items():
                entry = VaultEntry(
                    entry_id=f"fs_folder_{folder_key.replace('/', '_')}",
                    entry_type=VaultEntryType.PROJECT_METADATA,
                    title=f"Folder: {folder_info.name}",
                    content=f"Role: {folder_info.role.value}\nFiles: {folder_info.file_count}\nSize: {folder_info.total_size} bytes",
                    summary=f"Project folder with role: {folder_info.role.value}",
                    tags=["file_system", folder_info.role.value],
                    created_by="FileSystemMapper"
                )
                self.vault_core.store(entry)
            
            # Save project stats
            stats_entry = VaultEntry(
                entry_id="fs_project_stats",
                entry_type=VaultEntryType.PROJECT_METADATA,
                title="Project File Statistics",
                content=json.dumps(self.stats, indent=2),
                summary=f"Total files: {self.stats['total_files']}, Total size: {self.stats['total_size']} bytes",
                tags=["file_system", "statistics"],
                created_by="FileSystemMapper"
            )
            self.vault_core.store(stats_entry)
            
            logger.info(f"Saved file system metadata to VaultCore")
        except Exception as e:
            logger.error(f"Failed to save to VaultCore: {e}")
    
    def get_file_by_type(self, file_type: FileType) -> List[FileInfo]:
        """Get all files of specific type"""
        return [f for f in self.files.values() if f.file_type == file_type]
    
    def get_files_by_language(self, language: str) -> List[FileInfo]:
        """Get all files for specific language"""
        return [f for f in self.files.values() if f.language == language]
    
    def get_folders_by_role(self, role: FolderRole) -> List[FolderInfo]:
        """Get all folders with specific role"""
        return [f for f in self.folders.values() if f.role == role]
    
    def export_metadata(self, output_path: Path) -> bool:
        """Export file system metadata to JSON"""
        try:
            metadata = {
                "scan_time": datetime.utcnow().isoformat(),
                "project_root": str(self.project_root),
                "statistics": self.stats,
                "files": {k: v.to_dict() for k, v in self.files.items()},
                "folders": {k: v.to_dict() for k, v in self.folders.items()}
            }
            
            output_path.write_text(
                json.dumps(metadata, indent=2, default=str),
                encoding='utf-8'
            )
            logger.info(f"Exported metadata to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export metadata: {e}")
            return False


if __name__ == "__main__":
    # Demo
    import sys
    logging.basicConfig(level=logging.DEBUG)
    
    project_root = Path.cwd()
    mapper = FileSystemMapper(project_root)
    
    files = mapper.scan_project()
    print(f"\nScanned {len(files)} files")
    print(json.dumps(mapper.stats, indent=2))
    
    # Show some stats
    print(f"\nTop 10 largest files:")
    sorted_files = sorted(files.values(), key=lambda f: f.size, reverse=True)[:10]
    for f in sorted_files:
        print(f"  {f.relative_path}: {f.size / 1024:.1f} KB")
