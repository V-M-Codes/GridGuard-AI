# -*- coding: utf-8 -*-
"""
GridGuard AI Microgrid Autonomous Control Center
Standalone Server Launcher

Usage:
  python gridguard_server.py
"""

import os
import sys

# Add the project root to sys.path so this works both as a module and script.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Backened.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n" + "=" * 65)
    print("  GridGuard AI - Intelligent Microgrid Control Center")
    print(f"  REST API & SSE Server: http://127.0.0.1:{port}")
    print(f"  Web Dashboard:         http://127.0.0.1:{port}/")
    print(f"  API Status:            http://127.0.0.1:{port}/api/status")
    print(f"=" * 65 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False)