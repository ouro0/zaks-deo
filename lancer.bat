@echo off
title Zak's Deo Download

:: ─────────────────────────────────────────────
:: Chemin de ton projet
set DOSSIER=C:\Users\ZAK\projet_téléchrgement
:: ─────────────────────────────────────────────

echo.
echo  ╔══════════════════════════════════════╗
echo  ║     Zak's Deo Download - Demarrage  ║
echo  ╚══════════════════════════════════════╝
echo.

cd /d "%DOSSIER%"

:: Mettre à jour yt-dlp automatiquement
echo [1/3] Mise a jour yt-dlp...
pip install -U yt-dlp --quiet

:: Lancer le serveur FastAPI en arriere-plan
echo [2/3] Lancement du serveur...
start "Serveur FastAPI" /min cmd /c "cd /d %DOSSIER% && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

:: Attendre 4 secondes que le serveur demarre
timeout /t 4 /nobreak >nul

:: Lancer ngrok
echo [3/3] Lancement de ngrok...
start "ngrok" /min cmd /c "ngrok http 8000"

echo.
echo  ✓ Serveur local : http://localhost:8000
echo  ✓ Pour voir ton lien public ngrok :
echo    Ouvre http://127.0.0.1:4040 dans ton navigateur
echo.
pause
