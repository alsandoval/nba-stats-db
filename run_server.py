"""
run_server.py - Production & Development Launcher for Antigravity NBA Analytics Platform.
Orchestrates the FastAPI OLAP backend and Next.js App Router frontend.
"""

import os
import sys
import argparse
import subprocess
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="Antigravity NBA Analytics Server Launcher")
    parser.add_argument("--api-port", type=int, default=8000, help="FastAPI port (default: 8000)")
    parser.add_argument("--front-port", type=int, default=3000, help="Next.js frontend port (default: 3000)")
    parser.add_argument("--api-only", action="store_true", help="Launch only FastAPI backend")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    args = parser.parse_args()

    frontend_proc = None
    node_exe = r"C:\Program Files\nodejs\node.exe"
    npm_cmd = r"C:\Program Files\nodejs\npm.cmd"

    # Start Next.js frontend if not api-only and npm is available
    if not args.api_only and os.path.exists(npm_cmd):
        print(f"[*] Starting Next.js App Router Frontend on http://{args.host}:{args.front_port}...")
        frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
        env = os.environ.copy()
        env["PATH"] = r"C:\Program Files\nodejs;" + env.get("PATH", "")
        env["PORT"] = str(args.front_port)
        try:
            frontend_proc = subprocess.Popen(
                [npm_cmd, "start", "--", "-p", str(args.front_port)],
                cwd=frontend_dir,
                env=env,
                shell=True,
            )
            print(f"[+] Frontend running at: http://{args.host}:{args.front_port}")
        except Exception as e:
            print(f"[!] Note: Could not auto-start Next.js frontend: {e}")

    print(f"[*] Starting FastAPI OLAP Backend on http://{args.host}:{args.api_port}...")
    print(f"[*] Interactive API Docs: http://{args.host}:{args.api_port}/docs")
    print(f"[*] Sub-15ms WOWY bitmask endpoint: http://{args.host}:{args.api_port}/api/wowy/evaluate")
    print(f"[*] Sparse Matrix RAPM leaderboard: http://{args.host}:{args.api_port}/api/rapm/leaderboard")
    print(f"[*] Apache Arrow streaming IPC: http://{args.host}:{args.api_port}/api/arrow/possessions")

    try:
        uvicorn.run("nba_stats_db.api.main:app", host=args.host, port=args.api_port, reload=False)
    finally:
        if frontend_proc:
            print("[*] Shutting down frontend subprocess...")
            frontend_proc.terminate()

if __name__ == "__main__":
    main()
