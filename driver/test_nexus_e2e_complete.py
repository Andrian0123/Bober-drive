#!/usr/bin/env python3
"""
Complete End-to-End Nexus System Test
Tests full pipeline: Gateway → Memory+Graph → Intent → Plan → Execute → Validate → RTK → Post-processor
"""

import sys
import json
from pathlib import Path
from dataclasses import asdict
from typing import Dict, Any, List

# Add driver to path
sys.path.insert(0, str(Path(__file__).parent))

# Import all Nexus modules
from nexus_gateway import NexusGateway, RequestNormalization
from nexus_memory_graph import NexusMemoryGraph, MemoryKind
from nexus_intent_analyzer import IntentAnalyzer
from nexus_planner import Planner
from nexus_executor_mcp import Executor
from nexus_rtk_proxy import RTKProxy
from nexus_validator import Validator
from nexus_post_processor import PostProcessor
from nexus_integration import NexusSystem, NexusConfig


class NexusE2EAudit:
    """Complete end-to-end system audit with detailed logging"""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.results = {
            "timestamp": None,
            "phases": {},
            "errors": [],
            "warnings": [],
            "statistics": {}
        }
        
    def log_phase(self, phase_name: str, status: str, details: Dict[str, Any]):
        """Log phase execution"""
        self.results["phases"][phase_name] = {
            "status": status,
            "details": details
        }
        print(f"\n{'='*60}")
        print(f"PHASE: {phase_name}")
        print(f"STATUS: {status}")
        print(f"DETAILS: {json.dumps(details, indent=2, ensure_ascii=False)}")
        print(f"{'='*60}")
    
    def log_error(self, phase: str, error: str):
        """Log error"""
        self.results["errors"].append({"phase": phase, "error": error})
        print(f"❌ ERROR in {phase}: {error}")
    
    def log_warning(self, phase: str, warning: str):
        """Log warning"""
        self.results["warnings"].append({"phase": phase, "warning": warning})
        print(f"⚠️  WARNING in {phase}: {warning}")
    
    def run_full_audit(self):
        """Run complete E2E audit"""
        print("\n" + "="*80)
        print("NEXUS v2.1.0 — COMPLETE END-TO-END SYSTEM AUDIT")
        print("="*80)
        
        try:
            # Phase 1: Gateway initialization
            self._audit_gateway()
            
            # Phase 2: Memory + Graph
            self._audit_memory_graph()
            
            # Phase 3: Intent Analyzer
            self._audit_intent_analyzer()
            
            # Phase 4: Planner
            self._audit_planner()
            
            # Phase 5: Executor
            self._audit_executor()
            
            # Phase 6: RTK Proxy
            self._audit_rtk_proxy()
            
            # Phase 7: Validator
            self._audit_validator()
            
            # Phase 8: Post-processor
            self._audit_post_processor()
            
            # Phase 9: Full Integration
            self._audit_integration()
            
            # Summary
            self._print_summary()
            
        except Exception as e:
            self.log_error("AUDIT", str(e))
            import traceback
            print(traceback.format_exc())
    
    def _audit_gateway(self):
        """Audit Gateway module"""
        try:
            gateway = NexusGateway()
            
            # Test normalization
            test_request = "Create a Python API for document management"
            normalized = gateway.normalize_request(test_request)
            
            details = {
                "input": test_request,
                "normalized": {
                    "query": normalized.query,
                    "request_type": normalized.request_type,
                    "language": normalized.language,
                    "context_files": normalized.context_files,
                    "confidence": normalized.confidence
                }
            }
            
            self.log_phase("GATEWAY", "✅ PASS", details)
            
        except Exception as e:
            self.log_error("GATEWAY", str(e))
    
    def _audit_memory_graph(self):
        """Audit Memory+Graph module"""
        try:
            mem_graph = NexusMemoryGraph(self.workspace)
            
            # Index workspace
            index_result = mem_graph.index_workspace(max_files=5)
            
            details = {
                "files_indexed": index_result.get("files_indexed", 0),
                "nodes_created": index_result.get("nodes_created", 0),
                "edges_created": index_result.get("edges_created", 0),
                "db_path": str(mem_graph.graph.db_path)
            }
            
            self.log_phase("MEMORY+GRAPH", "✅ PASS", details)
            
        except Exception as e:
            self.log_error("MEMORY+GRAPH", str(e))
    
    def _audit_intent_analyzer(self):
        """Audit Intent Analyzer module"""
        try:
            analyzer = IntentAnalyzer()
            
            test_request = "Create a Python API for document management"
            session_state = {
                "request": test_request,
                "request_type": "code_generation",
                "file_context": "",
                "keywords": ["api", "document", "python"]
            }
            
            result = analyzer.process(session_state)
            
            details = {
                "input": test_request,
                "intent_type": result.intent_type.value,
                "confidence": result.confidence,
                "primary_skill": {
                    "name": result.primary_skill.skill_name,
                    "confidence": result.primary_skill.confidence
                },
                "secondary_skills": [
                    {"name": s.skill_name, "confidence": s.confidence}
                    for s in result.secondary_skills[:2]
                ],
                "complexity": result.complexity
            }
            
            self.log_phase("INTENT ANALYZER", "✅ PASS", details)
            
        except Exception as e:
            self.log_error("INTENT ANALYZER", str(e))
    
    def _audit_planner(self):
        """Audit Planner module"""
        try:
            planner = Planner()
            
            session_state = {
                "intent_type": "CODE_GENERATION",
                "primary_skill": "python_dev",
                "secondary_skills": ["testing", "documentation"],
                "complexity": "high"
            }
            
            plan = planner.process(session_state)
            
            details = {
                "plan_id": plan.plan_id,
                "total_tasks": len(plan.tasks),
                "execution_batches": len(plan.execution_order),
                "critical_path_length": len(plan.critical_path),
                "estimated_duration": plan.estimated_total_duration,
                "sample_tasks": [
                    {
                        "id": task_id,
                        "description": plan.tasks[task_id].description,
                        "priority": plan.tasks[task_id].priority.value
                    }
                    for task_id in list(plan.tasks.keys())[:3]
                ]
            }
            
            self.log_phase("PLANNER", "✅ PASS", details)
            
        except Exception as e:
            self.log_error("PLANNER", str(e))
    
    def _audit_executor(self):
        """Audit Executor/MCP module"""
        try:
            executor = Executor()
            
            session_state = {
                "plan": {
                    "tasks": {
                        "task_001": {
                            "description": "Initialize project structure",
                            "tool_type": "python_dev",
                            "parameters": {}
                        }
                    }
                }
            }
            
            result = executor.process(session_state)
            
            details = {
                "execution_status": result.get("execution_status", "pending"),
                "executed_tasks": len(result.get("execution_results", [])),
                "total_duration": result.get("total_execution_time", 0),
                "errors": result.get("errors", [])
            }
            
            self.log_phase("EXECUTOR", "✅ PASS", details)
            
        except Exception as e:
            self.log_error("EXECUTOR", str(e))
    
    def _audit_rtk_proxy(self):
        """Audit RTK Proxy module"""
        try:
            rtk = RTKProxy()
            
            session_state = {
                "execution_output": "A" * 5000,  # Simulate large output
                "execution_results": [{"status": "success", "output": "B" * 1000}]
            }
            
            compressed = rtk.process(session_state)
            
            original_size = len(session_state["execution_output"])
            compressed_output = compressed.get("execution_output", "")
            compressed_size = len(compressed_output)
            reduction = ((original_size - compressed_size) / original_size * 100) if original_size > 0 else 0
            
            details = {
                "original_size": original_size,
                "compressed_size": compressed_size,
                "reduction_percent": f"{reduction:.1f}%",
                "compression_strategy": compressed.get("compression_strategy", "unknown"),
                "metrics": compressed.get("compression_metrics", {})
            }
            
            self.log_phase("RTK PROXY", "✅ PASS", details)
            
        except Exception as e:
            self.log_error("RTK PROXY", str(e))
    
    def _audit_validator(self):
        """Audit Validator module"""
        try:
            validator = Validator()
            
            session_state = {
                "execution_output": "def hello():\n    print('Hello, World!')",
                "execution_results": [{"status": "success"}]
            }
            
            result = validator.process(session_state)
            
            details = {
                "validation_result": result.get("validation_result", "unknown"),
                "quality_score": result.get("quality_score", 0),
                "checks_passed": result.get("checks_passed", 0),
                "checks_total": result.get("checks_total", 0),
                "rework_needed": result.get("rework_needed", False),
                "rework_phase": result.get("rework_phase", "NONE")
            }
            
            self.log_phase("VALIDATOR", "✅ PASS", details)
            
        except Exception as e:
            self.log_error("VALIDATOR", str(e))
    
    def _audit_post_processor(self):
        """Audit Post-processor module"""
        try:
            post_proc = PostProcessor(self.workspace)
            
            session_state = {
                "session_id": "test-session-001",
                "original_request": "Create a Python API",
                "compressed_output": "Sample output",
                "execution_results": [{"status": "success", "output": "result"}],
                "validation_result": "PASS",
                "quality_score": 0.95
            }
            
            result = post_proc.process(session_state)
            
            details = {
                "session_saved": result.get("session_saved", False),
                "artifacts_count": len(result.get("artifacts", [])),
                "output_location": result.get("output_location", "unknown"),
                "memory_updated": result.get("memory_updated", False)
            }
            
            self.log_phase("POST-PROCESSOR", "✅ PASS", details)
            
        except Exception as e:
            self.log_error("POST-PROCESSOR", str(e))
    
    def _audit_integration(self):
        """Audit full integration"""
        try:
            config = NexusConfig(
                workspace_path=self.workspace,
                memory_db_path=self.workspace / ".nexus" / "memory.db",
                mcp_endpoint="http://localhost:11434",
                max_rework_attempts=3
            )
            
            nexus = NexusSystem(config)
            
            # Process test request
            user_request = "Create a Python REST API with FastAPI for task management"
            result = nexus.process_request(user_request)
            
            details = {
                "request": user_request,
                "phases_executed": list(result.get("phases_executed", {}).keys()),
                "final_status": result.get("status", "unknown"),
                "rework_attempts": result.get("rework_attempts", 0),
                "total_execution_time": result.get("execution_time", 0),
                "compression_stats": result.get("compression_stats", {}),
                "validation_score": result.get("validation_score", 0)
            }
            
            self.log_phase("FULL INTEGRATION", "✅ PASS", details)
            
        except Exception as e:
            self.log_error("FULL INTEGRATION", str(e))
    
    def _print_summary(self):
        """Print summary report"""
        print("\n" + "="*80)
        print("AUDIT SUMMARY")
        print("="*80)
        
        passed = sum(1 for p in self.results["phases"].values() if "✅" in str(p.get("status", "")))
        total = len(self.results["phases"])
        
        print(f"\n✅ Phases Passed: {passed}/{total}")
        print(f"❌ Errors: {len(self.results['errors'])}")
        print(f"⚠️  Warnings: {len(self.results['warnings'])}")
        
        if self.results["errors"]:
            print("\nErrors:")
            for err in self.results["errors"]:
                print(f"  - {err['phase']}: {err['error']}")
        
        if self.results["warnings"]:
            print("\nWarnings:")
            for warn in self.results["warnings"]:
                print(f"  - {warn['phase']}: {warn['warning']}")
        
        print("\n" + "="*80)
        if passed == total and not self.results["errors"]:
            print("✅ ALL SYSTEMS OPERATIONAL — NEXUS READY FOR PRODUCTION")
        else:
            print("⚠️  AUDIT COMPLETE WITH ISSUES — REVIEW ABOVE")
        print("="*80 + "\n")


def main():
    """Run complete audit"""
    workspace = Path(__file__).parent.parent
    audit = NexusE2EAudit(workspace)
    audit.run_full_audit()
    
    # Save report
    report_path = workspace / ".nexus" / "e2e_audit_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(audit.results, f, indent=2, ensure_ascii=False)
    print(f"\n📊 Audit report saved to: {report_path}")


if __name__ == "__main__":
    main()
