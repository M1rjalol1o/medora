@echo off
chcp 65001 >nul
REM Medora loyihasini GitHubga yuklash (M1rjalol1o/medora)
cd /d %~dp0
where git >nul 2>nul || (echo Git topilmadi. https://git-scm.com/download/win dan ornating. & pause & exit /b 1)
if not exist .git git init -b main
git add -A
git -c user.name="M1rjalol1o" -c user.email="M1rjalol1o@users.noreply.github.com" commit -q -m "Medora: dori qidiruvi, bashorat, yetkazish, retsept va budilnik platformasi" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01ER5zPsbYVZtorRxLVk8pif"
git branch -M main
git remote remove origin 2>nul
git remote add origin https://github.com/M1rjalol1o/medora.git
echo.
echo GitHub oynasi chiqsa - M1rjalol1o akkaunti bilan kiring.
git push -u origin main
echo.
if %errorlevel%==0 (echo TAYYOR: https://github.com/M1rjalol1o/medora) else (echo Xato chiqdi - shu oynaning rasmini yuboring.)
pause
