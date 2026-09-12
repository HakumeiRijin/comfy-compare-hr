@echo off
REM Image Compare Viewer 起動用バッチファイル
REM このファイルをダブルクリックすると起動します。
cd /d "%~dp0"
uv run python -m image_compare