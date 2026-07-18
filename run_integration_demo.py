#!/usr/bin/env python3
"""
Nexus Driver v3.0.0 Integration Demo
Демонстрация gRPC интеграции с Python adapter и Node.js клиентом
"""

import sys
import time
import logging
from pathlib import Path
from concurrent import futures

# Add driver to path
sys.path.insert(0, str(Path(__file__).parent / "driver"))

from nexus_orchestrator_v3 import NexusOrchestrator, NexusConfig
from nexus_grpc_adapter import NexusGRPCAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run integration demo"""
    
    # Setup paths
    project_root = Path.home() / ".nexus" / "demo_project"
    vault_path = Path.home() / ".nexus" / "integration" / "vault.db"
    
    project_root.mkdir(parents=True, exist_ok=True)
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Project root: {project_root}")
    logger.info(f"Vault path: {vault_path}")
    
    # Create test documents
    logger.info("Creating test documents...")
    (project_root / "README.md").write_text("""# Demo Project

This is a demo project for testing Nexus Driver v3.0.0 integration.

## Features
- Full-text search via gRPC
- Document indexing
- Project scanning
- Real-time event emission
""")
    
    (project_root / "config.txt").write_text("""Configuration settings for the project.

API Configuration:
- gRPC server: localhost:50051
- Max message size: 100MB
- Auto-update: disabled
""")
    
    # Create Nexus configuration
    config = NexusConfig(
        project_root=project_root,
        vault_path=vault_path,
        enable_auto_update=False,
        enable_events=True,
        enable_caching=True,
        max_workers=4
    )
    
    # Initialize Orchestrator
    logger.info("Initializing NexusOrchestrator...")
    orchestrator = NexusOrchestrator(config)
    
    # Ingest documents
    logger.info("Ingesting documents...")
    for doc in project_root.glob("*.md"):
        result = orchestrator.ingest_document(doc)
        logger.info(f"Ingested {doc.name}: {result}")
    
    for doc in project_root.glob("*.txt"):
        result = orchestrator.ingest_document(doc)
        logger.info(f"Ingested {doc.name}: {result}")
    
    # Test search
    logger.info("\nTesting search functionality...")
    search_results = orchestrator.search("gRPC")
    logger.info(f"Search for 'gRPC': {len(search_results.get('results', []))} results found")
    for i, result in enumerate(search_results.get('results', [])[:3], 1):
        logger.info(f"  {i}. {result}")
    
    # Test project scan
    logger.info("\nScanning project...")
    scan_results = orchestrator.scan_project()
    logger.info(f"Scan results: {scan_results}")
    
    # Get stats
    logger.info("\nGetting system stats...")
    stats = orchestrator.get_stats()
    logger.info(f"Vault entries: {stats.get('vault', {}).get('entries', 0)}")
    logger.info(f"Total indexed: {stats.get('vault', {}).get('edges', 0)}")
    
    # Create and start gRPC adapter
    logger.info("\nStarting gRPC adapter server...")
    try:
        adapter = NexusGRPCAdapter(orchestrator, port=50051)
        adapter.start()
        logger.info("gRPC server started on localhost:50051")
        logger.info("Server will run for 30 seconds for demo purposes...")
        
        # Keep server running
        for i in range(30):
            time.sleep(1)
            if i % 10 == 0 and i > 0:
                logger.info(f"Server running... ({30-i} seconds remaining)")
        
        logger.info("Stopping gRPC server...")
        adapter.stop()
        
    except Exception as e:
        logger.error(f"Error starting gRPC adapter: {e}", exc_info=True)
    finally:
        orchestrator.shutdown()
        logger.info("Orchestrator shutdown complete")
    
    logger.info("\nDemo completed successfully!")


if __name__ == "__main__":
    main()
