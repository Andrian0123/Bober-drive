#!/usr/bin/env python3
"""
RulesEngineV3 Usage Examples - Phase 4

Three main patterns:
1. With EventBus (centralized pub/sub)
2. Local subscribers (no EventBus needed)
3. Legacy adapter (gradual migration)
"""

import tempfile
import logging
from pathlib import Path

from nexus_rules_engine_v3 import (
    RulesEngineV3,
    RulesEngineAdapter,
    create_rules_engine_v3,
    RulesEngineV3Config
)
from core.event_bus import EventBus, EventBusConfig
from nexus_project_rules import ProjectRule, RuleLevel, RuleCategory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# PATTERN 1: With Central EventBus (Recommended for Full Ecosystem)
# ============================================================================

def example_with_eventbus():
    """Pattern 1: Using RulesEngineV3 with central EventBus"""
    
    print("\n" + "="*70)
    print("PATTERN 1: RulesEngineV3 with Central EventBus")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        
        # Create test rules file
        rules_file = project_root / "CLAUDE.md"
        rules_file.write_text("""## Code Style Guidelines
MUST follow PEP 8 style guide

## Security Best Practices
SHOULD use encryption for sensitive data

## Performance Optimization
SHOULD minimize database queries
""")
        
        # Initialize central EventBus
        event_bus = EventBus(EventBusConfig())
        
        # Track all events
        all_events = []
        
        def universal_event_handler(event):
            all_events.append(event)
            print(f"  📊 Event: {event.__class__.__name__}")
        
        # Subscribe to all RulesEngine events (could be extended to other modules)
        from nexus_rules_engine_v3 import (
            RulesScanRequested, RulesLoaded, RuleViolationDetected,
            RulesValidationCompleted
        )
        
        for event_type in [RulesScanRequested, RulesLoaded, RuleViolationDetected, RulesValidationCompleted]:
            event_bus.subscribe(event_type, universal_event_handler)
        
        # Create RulesEngineV3 with EventBus
        engine = RulesEngineV3(
            project_root,
            event_bus=event_bus,
            config=RulesEngineV3Config(
                enable_events=True,
                async_event_processing=False,
                track_scan_history=True
            )
        )
        
        print("\n1. Scanning rules...")
        rules = engine.scan_rules()
        print(f"   ✓ Loaded {len(rules)} rules")
        
        print(f"\n2. EventBus captured {len(all_events)} events:")
        for event in all_events:
            print(f"   • {event.__class__.__name__}")
        
        print("\n3. Validating content against rules...")
        test_content = """def my_function():
    password = "hardcoded"  # Security issue
    for i in range(1000):
        print(i)
"""
        violations = engine.validate_against_rules(test_content)
        print(f"   ✓ Found {len(violations)} violations")
        
        print("\n4. Statistics:")
        stats = engine.get_stats()
        print(f"   • Total rules: {stats['total_rules']}")
        print(f"   • Scans: {stats['scans']['total']} (avg {stats['scans']['avg_duration_ms']:.2f}ms)")
        print(f"   • Validations: {stats['validations']['total']}")
        
        print("\n5. EventBus snapshot:")
        bus_stats = event_bus.get_stats()
        print(f"   • Total events published: {bus_stats['total_events_published']}")


# ============================================================================
# PATTERN 2: Local Subscribers (No EventBus)
# ============================================================================

def example_with_local_subscribers():
    """Pattern 2: Using local subscribers without EventBus"""
    
    print("\n" + "="*70)
    print("PATTERN 2: Local Subscribers (No EventBus)")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        
        # Create test rules
        rules_file = project_root / "CLAUDE.md"
        rules_file.write_text("""## API Naming
MUST use snake_case for function names

## Documentation
SHOULD document all public APIs
""")
        
        # Create engine WITHOUT EventBus
        engine = RulesEngineV3(
            project_root,
            event_bus=None,  # No central EventBus
            config=RulesEngineV3Config(
                enable_events=True,
                track_scan_history=True
            )
        )
        
        # Subscribe locally
        scan_events = []
        violation_events = []
        
        def on_rules_loaded(event):
            scan_events.append(event)
            print(f"  📁 Rules Loaded: {event.rule_count} rules")
        
        def on_violation_detected(event):
            violation_events.append(event)
            print(f"  ⚠️  Violation: {event.rule_title} ({event.severity})")
        
        # Local subscriptions
        engine.on_rules_loaded(on_rules_loaded)
        engine.on_violation_detected(on_violation_detected)
        
        print("\n1. Scanning rules...")
        engine.scan_rules()
        print(f"   ✓ Captured {len(scan_events)} scan events locally")
        
        print("\n2. Validating with local listener...")
        test_code = "def MyFunction():  # violates snake_case\n    pass\n"
        
        test_rule = ProjectRule(
            rule_id="snake_case",
            title="API Naming: snake_case required",
            description="All function names must use snake_case",
            level=RuleLevel.HARD_CONSTRAINT,
            category=RuleCategory.CODE_STYLE,
            source_file="test",
            applies_to=["python"],
            pattern=r"def [A-Z]"
        )
        engine.rules = {"snake_case": test_rule}
        engine._build_index()
        
        violations = engine.validate_against_rules(test_code)
        print(f"   ✓ Captured {len(violation_events)} violation events locally")
        
        print("\n3. Local history (no central event log):")
        history = engine.get_validation_history()
        print(f"   • Validation history: {len(history)} items")


# ============================================================================
# PATTERN 3: Legacy Adapter (Gradual Migration)
# ============================================================================

def example_with_legacy_adapter():
    """Pattern 3: Wrapping legacy ProjectRulesEngine for gradual migration"""
    
    print("\n" + "="*70)
    print("PATTERN 3: Legacy Adapter (Gradual Migration)")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        
        # Create rules file
        rules_file = project_root / ".cursorrules"
        rules_file.write_text("No hardcoded credentials\nUse environment variables\n")
        
        print("\n1. Original code uses ProjectRulesEngine...")
        from nexus_project_rules import ProjectRulesEngine
        
        legacy_engine = ProjectRulesEngine(project_root)
        legacy_rules = legacy_engine.scan_rules()
        print(f"   ✓ Legacy scan found {len(legacy_rules)} rules")
        
        print("\n2. Wrap with V3 to add events...")
        v3_engine = RulesEngineAdapter.wrap(legacy_engine)
        
        print(f"   ✓ Wrapped! Engine is now {v3_engine.__class__.__name__}")
        
        # Now has V3 capabilities
        print("\n3. Add local listener (new capability)...")
        validation_count = [0]
        
        def on_validation_complete(event):
            validation_count[0] += 1
            print(f"   ✓ Validation #{validation_count[0]}: {event.violation_count} violations")
        
        v3_engine.on_validation_completed(on_validation_complete)
        
        print("\n4. Use exactly like legacy code...")
        test_content = "SECRET_KEY = 'hardcoded_value'"
        violations = v3_engine.validate_against_rules(test_content)
        
        print(f"   ✓ Got {len(violations)} violations (with new event features!)")
        
        print("\n5. Migration stats:")
        stats = v3_engine.get_stats()
        print(f"   • Rules loaded: {stats['total_rules']}")
        print(f"   • Validations run: {stats['validations']['total']}")
        print(f"   • Now has event support: YES")


# ============================================================================
# PATTERN 4: Performance Mode (Events Disabled)
# ============================================================================

def example_performance_mode():
    """Pattern 4: High-throughput mode with events disabled"""
    
    print("\n" + "="*70)
    print("PATTERN 4: Performance Mode (Events Disabled)")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        
        # Create rules
        rules_file = project_root / "CLAUDE.md"
        rules_file.write_text("## Test Rules\n\nSome test rules\n")
        
        # Create engine with events disabled
        engine = RulesEngineV3(
            project_root,
            config=RulesEngineV3Config(
                enable_events=False,  # Disabled!
                track_scan_history=False  # Also skip history
            )
        )
        
        print("\n1. Events disabled for performance...")
        print(f"   • enable_events: {engine.config.enable_events}")
        print(f"   • track_scan_history: {engine.config.track_scan_history}")
        
        print("\n2. Scan (no event overhead)...")
        import time
        start = time.time()
        engine.scan_rules()
        scan_time = (time.time() - start) * 1000
        print(f"   ✓ Scan completed in {scan_time:.2f}ms")
        
        print("\n3. Validate batch (no event overhead)...")
        test_rules = [
            ProjectRule(
                rule_id=f"rule_{i}",
                title=f"Rule {i}",
                description="Test",
                level=RuleLevel.GUIDELINE,
                category=RuleCategory.OTHER,
                source_file="test",
                applies_to=["all"]
            )
            for i in range(10)
        ]
        engine.rules = {r.rule_id: r for r in test_rules}
        
        start = time.time()
        for i in range(100):
            engine.validate_against_rules(f"test content {i}")
        batch_time = (time.time() - start) * 1000
        
        print(f"   ✓ 100 validations in {batch_time:.2f}ms ({batch_time/100:.2f}ms each)")
        
        print("\n4. Re-enable for monitoring...")
        engine.enable_events(True)
        print(f"   ✓ Events now: {engine.config.enable_events}")


# ============================================================================
# PATTERN 5: Full Lifecycle (Integration with EventBus)
# ============================================================================

def example_full_lifecycle():
    """Pattern 5: Complete lifecycle showing all capabilities"""
    
    print("\n" + "="*70)
    print("PATTERN 5: Full Lifecycle Integration")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        
        # Setup
        rules_file = project_root / "CLAUDE.md"
        rules_file.write_text("""## Naming Convention
MUST use snake_case_naming

## Type Hints
SHOULD include type hints

## Error Handling
MUST handle exceptions properly
""")
        
        event_bus = EventBus()
        engine = create_rules_engine_v3(project_root, event_bus=event_bus)
        
        # Track lifecycle
        lifecycle_events = {
            "scan_requested": 0,
            "rules_loaded": 0,
            "validation_started": 0,
            "violations_found": 0,
            "validation_complete": 0
        }
        
        from nexus_rules_engine_v3 import (
            RulesScanRequested, RulesLoaded, RulesValidationCompleted,
            RuleViolationDetected
        )
        
        def track_scan_request(event):
            lifecycle_events["scan_requested"] += 1
        
        def track_rules_loaded(event):
            lifecycle_events["rules_loaded"] += 1
            print(f"  📁 {event.rule_count} rules loaded")
        
        def track_violation(event):
            lifecycle_events["violations_found"] += 1
        
        def track_complete(event):
            lifecycle_events["validation_complete"] += 1
            print(f"  ✓ Validation complete: {event.violation_count} violations in {event.elapsed_ms:.2f}ms")
        
        event_bus.subscribe(RulesScanRequested, track_scan_request)
        event_bus.subscribe(RulesLoaded, track_rules_loaded)
        event_bus.subscribe(RuleViolationDetected, track_violation)
        event_bus.subscribe(RulesValidationCompleted, track_complete)
        
        print("\n1. Initialize and scan...")
        rules = engine.scan_rules()
        
        print("\n2. Validate test code...")
        test_python = """def MyTestFunction():  # Wrong: PascalCase
    try:
        x=get_value( )  # Wrong: formatting
    except:  # Wrong: bare except
        pass
"""
        violations = engine.validate_against_rules(test_python, rules_or_language="python")
        
        print("\n3. Lifecycle summary:")
        for event_type, count in lifecycle_events.items():
            print(f"   • {event_type}: {count}")
        
        print("\n4. Engine statistics:")
        stats = engine.get_stats()
        print(f"   • Total rules: {stats['total_rules']}")
        print(f"   • Validations: {stats['validations']['total']}")
        print(f"   • Total violations found: {stats['validations']['total_violations_found']}")
        
        print("\n5. History samples:")
        scans = engine.get_scan_history(limit=1)
        if scans:
            print(f"   • Last scan: {scans[0]['rule_count']} rules in {scans[0]['elapsed_ms']:.2f}ms")
        
        validations = engine.get_validation_history(limit=1)
        if validations:
            print(f"   • Last validation: {validations[0]['violation_count']} violations in {validations[0]['elapsed_ms']:.2f}ms")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n" + "🎯 " * 20)
    print("RULESENGINE V3 — USAGE EXAMPLES")
    print("🎯 " * 20)
    
    try:
        example_with_eventbus()
    except Exception as e:
        logger.error(f"Pattern 1 error: {e}")
    
    try:
        example_with_local_subscribers()
    except Exception as e:
        logger.error(f"Pattern 2 error: {e}")
    
    try:
        example_with_legacy_adapter()
    except Exception as e:
        logger.error(f"Pattern 3 error: {e}")
    
    try:
        example_performance_mode()
    except Exception as e:
        logger.error(f"Pattern 4 error: {e}")
    
    try:
        example_full_lifecycle()
    except Exception as e:
        logger.error(f"Pattern 5 error: {e}")
    
    print("\n" + "✓ " * 20)
    print("All examples completed!")
    print("✓ " * 20 + "\n")
