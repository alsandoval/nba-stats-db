"""
package_for_github.py - One-Click Packaging & Verification for GitHub & GitHub Pages Deployment.
Prepares the complete static site in both frontend/out and docs/ for immediate testing.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
OUT_DIR = FRONTEND_DIR / "out"
DOCS_DIR = ROOT_DIR / "docs"

NODE_PATH = r"C:\Program Files\nodejs"
NPM_CMD = r"C:\Program Files\nodejs\npm.cmd"

def run_command(cmd, cwd=ROOT_DIR, env=None):
    print(f"[*] Running: {cmd}")
    res = subprocess.run(cmd, cwd=str(cwd), env=env, shell=True)
    if res.returncode != 0:
        print(f"[!] Command failed with exit code {res.returncode}")
        return False
    return True

def package():
    print("=" * 70)
    print("  ANTIGRAVITY NBA ANALYTICS PLATFORM - GITHUB PACKAGING SUITE")
    print("=" * 70)

    # 1. Export static datasets
    print("\n[Step 1/3] Generating pre-computed analytical datasets...")
    py_exe = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
    if not py_exe.exists():
        py_exe = Path(sys.executable)

    export_script = ROOT_DIR / "scripts" / "export_static_data.py"
    if not run_command(f'"{py_exe}" "{export_script}"'):
        print("[!] Warning: Dataset export had issues, proceeding with existing data...")

    live_script = ROOT_DIR / "scripts" / "generate_live_feed.py"
    if not run_command(f'"{py_exe}" "{live_script}"'):
        print("[!] Warning: Live feed generation had issues, proceeding with existing data...")

    # 2. Build Next.js Static Export
    print("\n[Step 2/3] Compiling optimized Next.js static export...")
    env = os.environ.copy()
    env["PATH"] = f"{NODE_PATH};" + env.get("PATH", "")
    
    npm = NPM_CMD if os.path.exists(NPM_CMD) else "npm"
    if not run_command(f'"{npm}" run build', cwd=FRONTEND_DIR, env=env):
        print("[X] Next.js build failed!")
        return False

    # Ensure .nojekyll exists
    nojekyll = OUT_DIR / ".nojekyll"
    nojekyll.write_text("# Disable Jekyll for GitHub Pages\n", encoding="utf-8")

    # 3. Mirror to /docs for alternative 1-click GitHub Pages hosting
    print("\n[Step 3/3] Mirroring static output to /docs (GitHub Pages compatible)...")
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    shutil.copytree(OUT_DIR, DOCS_DIR)
    (DOCS_DIR / ".nojekyll").write_text("# Disable Jekyll for GitHub Pages\n", encoding="utf-8")

    print("\n" + "=" * 70)
    print("  [SUCCESS] NBA ANALYTICS APP SUCCESSFULLY PACKAGED FOR GITHUB!")
    print("=" * 70)
    print("""
Your app is 100% ready for deployment on GitHub Pages!

TWO EASY WAYS TO DEPLOY ON GITHUB PAGES:

Option A: Automated GitHub Actions (Recommended)
------------------------------------------------
1. Initialize or push this repository to GitHub:
     git init
     git add .
     git commit -m "Complete Antigravity NBA Analytics Platform"
     git remote add origin https://github.com/<username>/<repo-name>.git
     git push -u origin main

2. Go to your GitHub repository -> Settings -> Pages.
   Under 'Build and deployment' -> 'Source', select 'GitHub Actions'.
   The workflow at .github/workflows/deploy.yml will build and deploy automatically!

Option B: Instant Deployment via /docs Folder
---------------------------------------------
1. Push the code to GitHub:
     git add docs/
     git commit -m "Add static site in /docs"
     git push origin main

2. Go to Settings -> Pages:
   Under 'Source', choose 'Deploy from a branch', select branch 'main' and folder '/docs'.
   Click Save, and your app will be live within 60 seconds!

LOCAL TESTING:
--------------
- Test the static export locally:
    npx serve docs
  or
    python -m http.server 3000 --directory docs

- Or launch the full-stack server (FastAPI + Next.js):
    python run_server.py
""")
    return True

if __name__ == "__main__":
    package()
