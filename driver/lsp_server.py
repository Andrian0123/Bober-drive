#!/usr/bin/env python3
"""
Nexus LSP Server v3.0.0
Language Server Protocol implementation for IDE integration.

Communicates with VS Code / IntelliJ via JSON-RPC 2.0 protocol over stdio.
Delegates search, ingest, and project scanning to NexusGRPCAdapter.

Architecture:
- LSP Server (stdio) <-> JSON-RPC Protocol <-> VS Code / IntelliJ
- LSP Server <-> gRPC (port 50051) <-> NexusGRPCAdapter <-> NexusOrchestrator
"""

import json
import sys
import logging
import threading
from typing import Dict, Any, Optional, List
from pathlib import Path
import time
from dataclasses import dataclass, asdict

# Setup logging to file (not stderr, since stderr is used for LSP communication)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / '.nexus' / 'lsp_server.log'),
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)

# Try to import gRPC adapter; if not available, work with mock
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from nexus_grpc_adapter import NexusGRPCAdapter, IntegrationConfig
    from driver.nexus_orchestrator_v3 import NexusOrchestrator, NexusConfig
    GRPC_AVAILABLE = True
except ImportError as e:
    logger.warning(f"gRPC adapter not available: {e}. Using mock adapter.")
    GRPC_AVAILABLE = False


@dataclass
class LSPCompletionItem:
    """LSP CompletionItem structure"""
    label: str
    kind: int = 1  # Text
    detail: str = ""
    documentation: str = ""
    sortText: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v}


@dataclass
class LSPHoverResult:
    """LSP Hover response"""
    contents: str
    range: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"contents": self.contents}
        if self.range:
            result["range"] = self.range
        return result


class LSPServer:
    """
    Language Server Protocol implementation.
    
    Implements:
    - initialize: LSP handshake
    - textDocument/completion: Code completion via gRPC search
    - textDocument/hover: Hover info from vault
    - textDocument/definition: Jump to definition
    - textDocument/documentSymbol: Document outline
    - textDocument/rename: Rename documents/symbols
    
    All requests are routed through NexusGRPCAdapter.
    """
    
    def __init__(self, adapter: Optional[Any] = None):
        self.adapter = adapter
        self.initialized = False
        self.root_uri = None
        self.capabilities = {
            "completionProvider": {
                "resolveProvider": False,
                "triggerCharacters": [".", "@", "/"]
            },
            "hoverProvider": True,
            "definitionProvider": True,
            "documentSymbolProvider": True,
            "renameProvider": True,
            "textDocumentSync": 1  # Full document sync
        }
        self.open_documents: Dict[str, str] = {}  # uri -> content
        self._message_id = 0
        logger.info("LSP Server initialized (adapter available: %s)", self.adapter is not None)
    
    def _next_message_id(self) -> int:
        """Generate next message ID"""
        self._message_id += 1
        return self._message_id
    
    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request (LSP protocol handshake)"""
        logger.info("Initialize request from client at %s", params.get("rootUri"))
        self.root_uri = params.get("rootUri", "")
        self.initialized = True
        
        return {
            "capabilities": self.capabilities,
            "serverInfo": {
                "name": "Nexus LSP Server",
                "version": "3.0.0"
            }
        }
    
    def handle_initialized(self, params: Dict[str, Any]) -> None:
        """Handle initialized notification (server is now active)"""
        logger.info("Client notified that server is initialized")
        if self.adapter:
            health = self.adapter.health_check()
            logger.info("gRPC adapter health: %s", health.get("status"))
    
    def handle_shutdown(self, params: Dict[str, Any]) -> int:
        """Handle shutdown request"""
        logger.info("Shutdown request received")
        if self.adapter:
            self.adapter.shutdown()
        return 0
    
    def handle_exit(self, params: Dict[str, Any]) -> None:
        """Handle exit notification"""
        logger.info("Exit notification received")
        sys.exit(0)
    
    def handle_did_open(self, params: Dict[str, Any]) -> None:
        """Handle textDocument/didOpen notification (document opened in editor)"""
        doc = params.get("textDocument", {})
        uri = doc.get("uri")
        content = doc.get("text", "")
        
        logger.debug("Document opened: %s", uri)
        self.open_documents[uri] = content
        
        # Auto-ingest document if adapter available
        if self.adapter:
            file_path = uri.replace("file:///", "").replace("/", "\\")
            try:
                result = self.adapter.ingest(file_path, content)
                logger.debug("Auto-ingested document: %s", result.get("status"))
            except Exception as e:
                logger.warning("Auto-ingest failed for %s: %s", file_path, e)
    
    def handle_did_change(self, params: Dict[str, Any]) -> None:
        """Handle textDocument/didChange notification (document modified)"""
        doc = params.get("textDocument", {})
        uri = doc.get("uri")
        changes = params.get("contentChanges", [])
        
        if changes:
            # For full document sync, last change is the complete content
            self.open_documents[uri] = changes[-1].get("text", "")
            logger.debug("Document changed: %s (%d changes)", uri, len(changes))
    
    def handle_did_close(self, params: Dict[str, Any]) -> None:
        """Handle textDocument/didClose notification (document closed)"""
        uri = params.get("textDocument", {}).get("uri")
        if uri in self.open_documents:
            del self.open_documents[uri]
            logger.debug("Document closed: %s", uri)
    
    def handle_completion(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Handle textDocument/completion request.
        
        Query the gRPC adapter for relevant documentation based on:
        - Word being typed (extracted from document)
        - Current file context (project, language)
        
        Returns LSP CompletionItem list.
        """
        doc = params.get("textDocument", {})
        position = params.get("position", {})
        uri = doc.get("uri")
        
        line_num = position.get("line", 0)
        char = position.get("character", 0)
        
        logger.debug("Completion request: %s at line %d char %d", uri, line_num, char)
        
        # Extract word being completed from document
        content = self.open_documents.get(uri, "")
        lines = content.split("\n")
        
        if line_num >= len(lines):
            return []
        
        current_line = lines[line_num]
        if char > len(current_line):
            char = len(current_line)
        
        # Find word start (look backward for word boundary)
        word_start = char
        while word_start > 0 and (current_line[word_start - 1].isalnum() or current_line[word_start - 1] in "._"):
            word_start -= 1
        
        word = current_line[word_start:char]
        logger.debug("Completing word: '%s'", word)
        
        if not word or len(word) < 2:
            return []
        
        # Query gRPC adapter for matching documentation
        completions = []
        if self.adapter:
            try:
                search_results = self.adapter.search(
                    query=word,
                    limit=10,
                    search_type="fts5"
                )
                
                results = search_results.get("results", [])
                logger.debug("Search found %d results for '%s'", len(results), word)
                
                for i, result in enumerate(results[:10]):
                    doc_title = result.get("title", result.get("path", f"result_{i}"))
                    doc_content = result.get("content", "")[:100]  # First 100 chars
                    
                    item = LSPCompletionItem(
                        label=doc_title,
                        kind=1,  # Text
                        detail=result.get("type", "document"),
                        documentation=doc_content,
                        sortText=f"{i:03d}_{doc_title}"
                    )
                    completions.append(item.to_dict())
                    logger.debug("Added completion: %s", doc_title)
            
            except Exception as e:
                logger.error("Search failed: %s", e)
        
        return completions
    
    def handle_hover(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle textDocument/hover request.
        
        Returns documentation for the symbol at the cursor position.
        If a match is found in the vault, returns its full content.
        """
        doc = params.get("textDocument", {})
        position = params.get("position", {})
        uri = doc.get("uri")
        
        line_num = position.get("line", 0)
        char = position.get("character", 0)
        
        logger.debug("Hover request: %s at line %d char %d", uri, line_num, char)
        
        # Extract word at cursor
        content = self.open_documents.get(uri, "")
        lines = content.split("\n")
        
        if line_num >= len(lines):
            return None
        
        current_line = lines[line_num]
        
        # Find word boundaries
        if char > len(current_line):
            char = len(current_line)
        
        start = char
        while start > 0 and (current_line[start - 1].isalnum() or current_line[start - 1] in "._"):
            start -= 1
        
        end = char
        while end < len(current_line) and (current_line[end].isalnum() or current_line[end] in "._"):
            end += 1
        
        word = current_line[start:end]
        logger.debug("Hovering over word: '%s'", word)
        
        if not word:
            return None
        
        # Query adapter for documentation
        if self.adapter:
            try:
                search_results = self.adapter.search(
                    query=word,
                    limit=1,
                    search_type="fts5"
                )
                
                results = search_results.get("results", [])
                if results:
                    result = results[0]
                    content = result.get("content", "No documentation available")
                    
                    hover_result = LSPHoverResult(
                        contents=content[:500],  # First 500 chars
                        range={
                            "start": {"line": line_num, "character": start},
                            "end": {"line": line_num, "character": end}
                        }
                    )
                    return hover_result.to_dict()
            
            except Exception as e:
                logger.error("Hover search failed: %s", e)
        
        return None
    
    def handle_definition(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle textDocument/definition request (jump to definition)"""
        # TODO: Implement based on graph relationships in vault
        logger.debug("Definition request (not yet implemented)")
        return []
    
    def handle_document_symbol(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle textDocument/documentSymbol request (document outline)"""
        # TODO: Extract symbols from document via rules engine
        logger.debug("Document symbol request (not yet implemented)")
        return []
    
    def handle_rename(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle textDocument/rename request"""
        logger.debug("Rename request (not yet implemented)")
        return None
    
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single JSON-RPC 2.0 message.
        
        Returns response dict, or None for notifications.
        """
        msg_id = message.get("id")
        msg_method = message.get("method", "")
        params = message.get("params", {})
        
        logger.debug("Processing %s: %s", "request" if msg_id else "notification", msg_method)
        
        try:
            # Requests (expect response)
            if msg_method == "initialize":
                result = self.handle_initialize(params)
                return {"jsonrpc": "2.0", "id": msg_id, "result": result}
            
            elif msg_method == "shutdown":
                result = self.handle_shutdown(params)
                return {"jsonrpc": "2.0", "id": msg_id, "result": result}
            
            elif msg_method == "textDocument/completion":
                result = self.handle_completion(params)
                return {"jsonrpc": "2.0", "id": msg_id, "result": result}
            
            elif msg_method == "textDocument/hover":
                result = self.handle_hover(params)
                return {"jsonrpc": "2.0", "id": msg_id, "result": result}
            
            elif msg_method == "textDocument/definition":
                result = self.handle_definition(params)
                return {"jsonrpc": "2.0", "id": msg_id, "result": result}
            
            elif msg_method == "textDocument/documentSymbol":
                result = self.handle_document_symbol(params)
                return {"jsonrpc": "2.0", "id": msg_id, "result": result}
            
            elif msg_method == "textDocument/rename":
                result = self.handle_rename(params)
                return {"jsonrpc": "2.0", "id": msg_id, "result": result}
            
            # Notifications (no response)
            elif msg_method == "initialized":
                self.handle_initialized(params)
                return None
            
            elif msg_method == "exit":
                self.handle_exit(params)
                return None
            
            elif msg_method == "textDocument/didOpen":
                self.handle_did_open(params)
                return None
            
            elif msg_method == "textDocument/didChange":
                self.handle_did_change(params)
                return None
            
            elif msg_method == "textDocument/didClose":
                self.handle_did_close(params)
                return None
            
            else:
                logger.warning("Unknown method: %s", msg_method)
                if msg_id:
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": -32601, "message": f"Method not found: {msg_method}"}
                    }
                return None
        
        except Exception as e:
            logger.error("Error processing %s: %s", msg_method, e, exc_info=True)
            if msg_id:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": str(e)}
                }
            return None


class LSPServerStdio:
    """
    JSON-RPC 2.0 transport over stdio.
    
    Reads messages from stdin, processes them, and writes responses to stdout.
    Follows LSP spec: each message is prefixed with Content-Length header.
    """
    
    def __init__(self, lsp_server: LSPServer):
        self.server = lsp_server
        self.running = True
    
    def send_message(self, message: Dict[str, Any]) -> None:
        """Send a message to the client"""
        if not message:
            return
        
        content = json.dumps(message, ensure_ascii=False)
        content_bytes = content.encode("utf-8")
        
        response = f"Content-Length: {len(content_bytes)}\r\n\r\n{content}"
        sys.stdout.write(response)
        sys.stdout.flush()
        
        logger.debug("Sent: %s", message.get("method") or f"response {message.get('id')}")
    
    def read_message(self) -> Optional[Dict[str, Any]]:
        """Read a single message from stdin"""
        try:
            headers = {}
            
            # Read headers
            while True:
                line = sys.stdin.readline()
                if not line:
                    logger.info("EOF on stdin, shutting down")
                    self.running = False
                    return None
                
                line = line.strip()
                if not line:
                    break
                
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()
            
            # Read body
            content_length = int(headers.get("Content-Length", 0))
            if content_length == 0:
                return None
            
            content = sys.stdin.read(content_length)
            if not content:
                logger.info("No content received, shutting down")
                self.running = False
                return None
            
            message = json.loads(content)
            logger.debug("Received: %s", message.get("method") or f"request {message.get('id')}")
            return message
        
        except Exception as e:
            logger.error("Error reading message: %s", e)
            self.running = False
            return None
    
    def run(self) -> None:
        """Main event loop: read requests and send responses"""
        logger.info("LSP Server started on stdio")
        
        try:
            while self.running:
                message = self.read_message()
                if not message:
                    if not self.running:
                        break
                    continue
                
                response = self.server.process_message(message)
                if response:
                    self.send_message(response)
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error("Fatal error: %s", e, exc_info=True)
        finally:
            logger.info("LSP Server shutting down")


def create_adapter():
    """Create and initialize gRPC adapter"""
    if not GRPC_AVAILABLE:
        logger.warning("gRPC adapter not available, running without vault integration")
        return None
    
    try:
        # Get project root from environment or use current directory
        project_root = Path.cwd()
        vault_path = Path.home() / ".nexus" / "integration" / "vault.db"
        
        config = NexusConfig(
            project_root=project_root,
            vault_path=vault_path,
            enable_auto_update=False,
            enable_events=True
        )
        
        orchestrator = NexusOrchestrator(config)
        adapter = NexusGRPCAdapter(orchestrator, port=50051)
        
        logger.info("gRPC adapter created successfully")
        return adapter
    
    except Exception as e:
        logger.error("Failed to create adapter: %s", e)
        return None


def main():
    """Entry point: initialize LSP server and start stdio loop"""
    logger.info("=== Nexus LSP Server v3.0.0 ===")
    
    # Create adapter
    adapter = create_adapter()
    
    # Create LSP server
    lsp_server = LSPServer(adapter)
    
    # Start stdio event loop
    stdio = LSPServerStdio(lsp_server)
    stdio.run()


if __name__ == "__main__":
    main()
