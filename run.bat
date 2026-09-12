@echo off
REM Image Compare Viewer 起動用バッチファイル
REM このファイルをダブルクリックすると、ウィンドウを最小化した状態で起動します。
REM ターミナルから直接実行したい場合は、末尾に minimized を付けてください:
REM   run.bat minimized  ← 最小化せず、ログを見ながら実行

if /i not "%~1"=="minimized" (
    start /min "" "%~f0" minimized
    exit /b
)

cd /d "%~dp0"
uv run python -m image_compare
