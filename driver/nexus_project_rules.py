#!/usr/bin/env python3
"""
Project Rules Engine - Week 4 Implementation
Parses project rules from CLAUDE.md, .cursorrules, AGENTS.md, .harvi/rules-*.md
Stores and enforces project constraints and guidelines.

Architecture:
- Scans project for rule files at initialization
- Stores rules as RULE entries in VaultCore
- Provides constraint checking for validation phase
- Integrates with Neural Reflex Engine for result filtering
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import yaml

logger = logging.getLogger(__name__)


class RuleLevel(Enum):
    """Priority level of rules"""
    HARD_CONSTRAINT = "hard"  # Must be followed, fail if violated
    SOFT_CONSTRAINT = "soft"  # Should be followed, warn if violated
    GUIDELINE = "guideline"   # Nice to have, informational


class RuleCategory(Enum):
    """Categories of rules"""
    CODE_STYLE = "code_style"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    PERFORMANCE = "performance"
    PROJECT_STRUCTURE = "structure"
    DEPLOYMENT = "deployment"
    OTHER = "other"


@dataclass
class ProjectRule:
    """Represents a single project rule"""
    rule_id: str
    title: str
    description: str
    level: RuleLevel
    category: RuleCategory
    source_file: str  # Which config file it came from
    applies_to: List[str]  # ["python", "javascript", "all"]
    pattern: Optional[str] = None  # Regex for code matching
    violation_message: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "level": self.level.value,
            "category": self.category.value
        }


@dataclass
class RuleViolation:
    """Represents a rule violation"""
    rule_id: str
    rule_title: str
    severity: str  # "error", "warning", "info"
    location: Optional[str] = None  # File path or context
    line_number: Optional[int] = None
    content: Optional[str] = None
    suggestion: Optional[str] = None


class ProjectRulesEngine:
    """Main engine for project rules management and enforcement"""
    
    RULE_FILES = [
        "CLAUDE.md",
        ".cursorrules",
        "AGENTS.md",
        ".nexusrules",
        ".harvi/rules.md"
    ]
    
    RULE_DIR_PATTERNS = [
        ".harvi/rules-*.md",
        ".rules/*.md",
        "rules/*.md"
    ]
    
    def __init__(self, project_root: Path, vault_core=None):
        """
        Initialize Project Rules Engine
        
        Args:
            project_root: Root path of project
            vault_core: Optional VaultCore instance for storing rules
        """
        self.project_root = Path(project_root)
        self.vault_core = vault_core
        self.rules: Dict[str, ProjectRule] = {}
        self.rule_index: Dict[str, List[str]] = {
            "by_category": {},
            "by_level": {},
            "by_applies_to": {}
        }
        logger.info(f"ProjectRulesEngine initialized for {self.project_root}")
    
    def scan_rules(self) -> Dict[str, ProjectRule]:
        """
        Scan project for rule files and parse them
        
        Returns:
            Dictionary of rule_id -> ProjectRule
        """
        logger.info("Scanning project for rule files...")
        
        rules_found = {}
        
        # Scan main rule files
        for rule_file in self.RULE_FILES:
            path = self.project_root / rule_file
            if path.exists():
                logger.debug(f"Found rule file: {path}")
                parsed = self._parse_rule_file(path)
                rules_found.update(parsed)
        
        # Scan rule directories
        for pattern in self.RULE_DIR_PATTERNS:
            import glob
            matches = glob.glob(str(self.project_root / pattern), recursive=True)
            for match_path in matches:
                path = Path(match_path)
                logger.debug(f"Found rule file: {path}")
                parsed = self._parse_rule_file(path)
                rules_found.update(parsed)
        
        self.rules = rules_found
        self._build_index()
        
        logger.info(f"Loaded {len(self.rules)} rules from project")
        return self.rules
    
    def _parse_rule_file(self, path: Path) -> Dict[str, ProjectRule]:
        """Parse a single rule file and extract rules"""
        rules = {}
        
        try:
            content = path.read_text(encoding='utf-8')
            
            if path.suffix == '.md':
                # Markdown parsing
                rules.update(self._parse_markdown_rules(content, str(path)))
            elif path.suffix in ['.yaml', '.yml']:
                # YAML parsing
                rules.update(self._parse_yaml_rules(content, str(path)))
            elif path.name in ['.cursorrules', '.nexusrules']:
                # Plain text rules
                rules.update(self._parse_text_rules(content, str(path)))
            
        except Exception as e:
            logger.warning(f"Failed to parse rule file {path}: {e}")
        
        return rules
    
    def _parse_markdown_rules(self, content: str, source: str) -> Dict[str, ProjectRule]:
        """Extract rules from Markdown format"""
        rules = {}
        lines = content.split('\n')
        
        current_title = None
        current_content = []
        
        for line in lines:
            # Check if line is a header (## or ###)
            if line.startswith('##'):
                # If we have a previous section, parse it
                if current_title and current_content:
                    rule = self._parse_markdown_section(
                        current_title,
                        '\n'.join(current_content),
                        source
                    )
                    if rule:
                        rules[rule.rule_id] = rule
                
                # Start new section
                current_title = line.lstrip('# ').strip()
                current_content = []
            elif current_title is not None:
                # Accumulate content under current header
                if line.strip():  # Skip empty lines at section boundaries
                    current_content.append(line)
        
        # Don't forget the last section
        if current_title and current_content:
            rule = self._parse_markdown_section(
                current_title,
                '\n'.join(current_content),
                source
            )
            if rule:
                rules[rule.rule_id] = rule
        
        return rules
    
    def _parse_markdown_section(self, title: str, content: str, source: str) -> Optional[ProjectRule]:
        """Parse a single markdown section as a rule"""
        try:
            # Extract key-value patterns from content
            lines = content.strip().split('\n')
            
            # Determine level (hard/soft/guideline) from content markers
            level = RuleLevel.GUIDELINE
            if 'MUST' in content.upper() or '❌' in content:
                level = RuleLevel.HARD_CONSTRAINT
            elif 'SHOULD' in content.upper():
                level = RuleLevel.SOFT_CONSTRAINT
            
            # Try to detect category
            category = self._detect_category(title, content)
            
            # Extract applies_to languages
            applies_to = self._extract_applies_to(content)
            if not applies_to:
                applies_to = ["all"]
            
            # Look for pattern (regex)
            pattern = None
            pattern_match = re.search(r'pattern:?\s*`([^`]+)`', content, re.IGNORECASE)
            if pattern_match:
                pattern = pattern_match.group(1)
            
            rule_id = re.sub(r'\s+', '_', title.lower())[:50]
            
            return ProjectRule(
                rule_id=rule_id,
                title=title,
                description=content[:200],  # First 200 chars
                level=level,
                category=category,
                source_file=source,
                applies_to=applies_to,
                pattern=pattern,
                tags=self._extract_tags(content)
            )
        except Exception as e:
            logger.debug(f"Could not parse markdown section '{title}': {e}")
            return None
    
    def _parse_yaml_rules(self, content: str, source: str) -> Dict[str, ProjectRule]:
        """Extract rules from YAML format"""
        rules = {}
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'rules' in data:
                for rule_data in data['rules']:
                    rule = self._create_rule_from_dict(rule_data, source)
                    if rule:
                        rules[rule.rule_id] = rule
        except Exception as e:
            logger.warning(f"YAML parsing failed for {source}: {e}")
        return rules
    
    def _parse_text_rules(self, content: str, source: str) -> Dict[str, ProjectRule]:
        """Extract rules from plain text format"""
        rules = {}
        
        # Simple line-by-line parsing
        lines = content.strip().split('\n')
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('#'):
                rule = ProjectRule(
                    rule_id=f"rule_{i}",
                    title=line[:60],
                    description=line,
                    level=RuleLevel.GUIDELINE,
                    category=RuleCategory.OTHER,
                    source_file=source,
                    applies_to=["all"]
                )
                rules[rule.rule_id] = rule
        
        return rules
    
    def _create_rule_from_dict(self, data: Dict, source: str) -> Optional[ProjectRule]:
        """Create ProjectRule from dictionary"""
        try:
            return ProjectRule(
                rule_id=data.get('id', 'rule_auto'),
                title=data.get('title', 'Untitled'),
                description=data.get('description', ''),
                level=RuleLevel[data.get('level', 'GUIDELINE').upper()] 
                      if data.get('level') else RuleLevel.GUIDELINE,
                category=RuleCategory[data.get('category', 'OTHER').upper()] 
                         if data.get('category') else RuleCategory.OTHER,
                source_file=source,
                applies_to=data.get('applies_to', ['all']),
                pattern=data.get('pattern'),
                violation_message=data.get('violation_message'),
                tags=data.get('tags', [])
            )
        except Exception as e:
            logger.warning(f"Failed to create rule from dict: {e}")
            return None
    
    def _detect_category(self, title: str, content: str) -> RuleCategory:
        """Detect rule category from title and content"""
        text = f"{title} {content}".lower()
        
        if any(w in text for w in ['style', 'format', 'naming', 'convention']):
            return RuleCategory.CODE_STYLE
        elif any(w in text for w in ['architecture', 'design', 'pattern', 'structure']):
            return RuleCategory.ARCHITECTURE
        elif any(w in text for w in ['test', 'coverage', 'unit', 'integration']):
            return RuleCategory.TESTING
        elif any(w in text for w in ['doc', 'comment', 'readme', 'annotation']):
            return RuleCategory.DOCUMENTATION
        elif any(w in text for w in ['security', 'auth', 'encrypt', 'vulnerability']):
            return RuleCategory.SECURITY
        elif any(w in text for w in ['performance', 'optimization', 'speed', 'memory']):
            return RuleCategory.PERFORMANCE
        elif any(w in text for w in ['folder', 'file', 'directory', 'organization']):
            return RuleCategory.PROJECT_STRUCTURE
        elif any(w in text for w in ['deploy', 'release', 'build', 'production']):
            return RuleCategory.DEPLOYMENT
        
        return RuleCategory.OTHER
    
    def _extract_applies_to(self, content: str) -> List[str]:
        """Extract language/framework applicability"""
        languages = []
        text = content.lower()
        
        lang_patterns = {
            'python': ['python', 'py', 'pytest'],
            'javascript': ['javascript', 'js', 'typescript', 'ts', 'node', 'react'],
            'java': ['java', 'junit', 'spring'],
            'go': ['go', 'golang'],
            'rust': ['rust'],
            'csharp': ['c#', 'csharp', '.net'],
            'sql': ['sql', 'database', 'query'],
            'html': ['html', 'css', 'web'],
            'all': ['all', 'general', 'universal']
        }
        
        for lang, patterns in lang_patterns.items():
            if any(p in text for p in patterns):
                languages.append(lang)
        
        return languages or []
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from content"""
        # Look for #hashtags
        tags = re.findall(r'#(\w+)', content)
        return list(set(tags))
    
    def _build_index(self):
        """Build indexes for quick rule lookups"""
        self.rule_index = {
            "by_category": {},
            "by_level": {},
            "by_applies_to": {}
        }
        
        for rule_id, rule in self.rules.items():
            # Index by category
            cat = rule.category.value
            if cat not in self.rule_index["by_category"]:
                self.rule_index["by_category"][cat] = []
            self.rule_index["by_category"][cat].append(rule_id)
            
            # Index by level
            lvl = rule.level.value
            if lvl not in self.rule_index["by_level"]:
                self.rule_index["by_level"][lvl] = []
            self.rule_index["by_level"][lvl].append(rule_id)
            
            # Index by applies_to
            for lang in rule.applies_to:
                if lang not in self.rule_index["by_applies_to"]:
                    self.rule_index["by_applies_to"][lang] = []
                self.rule_index["by_applies_to"][lang].append(rule_id)
    
    def get_applicable_rules(self, applies_to: str = "all", 
                            category: Optional[str] = None,
                            level: Optional[str] = None) -> List[ProjectRule]:
        """Get rules applicable to specific context"""
        applicable = []
        
        for rule_id, rule in self.rules.items():
            if applies_to != "all" and applies_to not in rule.applies_to and "all" not in rule.applies_to:
                continue
            if category and rule.category.value != category:
                continue
            if level and rule.level.value != level:
                continue
            applicable.append(rule)
        
        return applicable
    
    def validate_against_rules(self, content: str, rules_or_language = "all") -> List[RuleViolation]:
        """Check content against applicable rules
        
        Args:
            content: Text to validate
            rules_or_language: Either language string (default: "all") or list of ProjectRule objects
        """
        violations = []
        
        # Handle both cases: list of rules or language string
        if isinstance(rules_or_language, list):
            applicable_rules = rules_or_language
        else:
            applicable_rules = self.get_applicable_rules(applies_to=rules_or_language)
        
        for rule in applicable_rules:
            if rule.pattern:
                try:
                    # Simple logic: if pattern is found and rule title suggests "no", it's a violation
                    if "no" in rule.title.lower() or "must not" in rule.description.lower():
                        # This is a "must not have" rule
                        if re.search(rule.pattern, content):
                            violations.append(RuleViolation(
                                rule_id=rule.rule_id,
                                rule_title=rule.title,
                                severity="error" if rule.level == RuleLevel.HARD_CONSTRAINT else "warning",
                                content=content[:100],
                                suggestion=rule.violation_message or f"Found forbidden pattern: {rule.pattern}"
                            ))
                except re.error as e:
                    logger.warning(f"Invalid regex pattern in rule {rule.rule_id}: {e}")
        
        return violations
    
    def save_rules_to_vault(self):
        """Save parsed rules to VaultCore"""
        if not self.vault_core:
            logger.warning("VaultCore not available, skipping rule storage")
            return 0
        
        try:
            from vault_core import VaultEntry, VaultEntryType
            
            count = 0
            for rule in self.rules.values():
                entry = VaultEntry(
                    entry_id=f"rule_{rule.rule_id}",
                    entry_type=VaultEntryType.RULE,
                    title=rule.title,
                    content=rule.description,
                    summary=f"Level: {rule.level.value}, Category: {rule.category.value}",
                    tags=rule.tags + [rule.category.value, rule.level.value],
                    created_by="ProjectRulesEngine"
                )
                self.vault_core.store(entry)
                logger.debug(f"Stored rule {rule.rule_id} in VaultCore")
                count += 1
            
            logger.info(f"Saved {len(self.rules)} rules to VaultCore")
            return count
        except Exception as e:
            logger.error(f"Failed to save rules to VaultCore: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded rules"""
        return {
            "total_rules": len(self.rules),
            "by_level": {
                level.value: len(ids) for level, ids in self.rule_index.get("by_level", {}).items()
            },
            "by_category": {
                cat: len(ids) for cat, ids in self.rule_index.get("by_category", {}).items()
            },
            "by_language": {
                lang: len(ids) for lang, ids in self.rule_index.get("by_applies_to", {}).items()
            }
        }
    
    def export_rules(self, output_path: Path) -> bool:
        """Export rules to JSON file"""
        try:
            rules_data = {
                rule_id: rule.to_dict() for rule_id, rule in self.rules.items()
            }
            
            output_path.write_text(
                json.dumps(rules_data, indent=2, default=str),
                encoding='utf-8'
            )
            logger.info(f"Exported {len(self.rules)} rules to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export rules: {e}")
            return False


if __name__ == "__main__":
    # Demo
    import sys
    logging.basicConfig(level=logging.DEBUG)
    
    project_root = Path.cwd()
    engine = ProjectRulesEngine(project_root)
    
    rules = engine.scan_rules()
    print(f"\nLoaded {len(rules)} rules:")
    print(json.dumps(engine.get_stats(), indent=2))
    
    # Test validation
    test_content = "def my_function():\n    pass"
    violations = engine.validate_against_rules(test_content, language="python")
    print(f"\nFound {len(violations)} violations")
