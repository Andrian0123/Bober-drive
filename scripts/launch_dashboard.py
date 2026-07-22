#!/usr/bin/env python3
"""
Quick launcher for Bober-Drive Dashboard
Минимальный скрипт для быстрого запуска дашборда
"""

import subprocess
import sys
import webbrowser
import time
from pathlib import Path


def main():
    """Launch dashboard"""
    
    print("""
╔═══════════════════════════════════════════════════╗
║     🚀 Bober-Drive Dashboard v3.0.1              ║
║                                                   ║
║  Launching web interface for monitoring...       ║
╚═══════════════════════════════════════════════════╝
    """)
    
    # Check if FastAPI/uvicorn are installed
    try:
        import fastapi
        import uvicorn
    except ImportError:
        print("⚠️  Missing dependencies. Installing...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "fastapi", "uvicorn"],
            check=True
        )
    
    # Find dashboard script
    dashboard_path = Path(__file__).parent / "dashboard.py"
    
    if not dashboard_path.exists():
        print(f"❌ Dashboard script not found at {dashboard_path}")
        sys.exit(1)
    
    # Default configuration
    project_root = "./docs"
    vault_path = "./.nexus/vault"
    port = 8000
    host = "127.0.0.1"
    
    # Check for custom paths
    if Path("docs").exists():
        project_root = "docs"
    elif Path("documentation").exists():
        project_root = "documentation"
    
    url = f"http://{host}:{port}"
    
    print(f"""
✅ Configuration:
   📁 Project Root: {project_root}
   💾 Vault Path: {vault_path}
   🌐 Dashboard URL: {url}

📝 Starting daemon and dashboard server...
   (Press Ctrl+C to stop)

""")
    
    # Start dashboard
    try:
        # Open browser after delay
        def open_browser():
            time.sleep(2)
            try:
                webbrowser.open(url)
                print(f"\n✨ Opened {url} in your default browser")
            except:
                print(f"\n📍 Open {url} manually in your browser")
        
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # Run dashboard
        subprocess.run(
            [
                sys.executable,
                str(dashboard_path),
                "--project", project_root,
                "--vault", vault_path,
                "--port", str(port),
                "--host", host
            ],
            check=True
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
