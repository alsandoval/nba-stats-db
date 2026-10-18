@echo off
cd /d "%~dp0"
echo ========================================================
echo   Pushing Antigravity NBA Analytics to GitHub (main)
echo ========================================================
echo If a GitHub Sign-In window appears, click "Sign in with your browser".
echo.
git push -u origin main
echo.
echo Done! Next step: Go to https://github.com/alsandoval/nba-stats-db/settings/pages
echo and set Source to "GitHub Actions".
pause
