@echo off
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if %errorlevel%==0 (
    uv sync
    uv run streamlit run app.py
) else (
    echo uv was not found. Falling back to python/pip...
    if not exist .venv (
        python -m venv .venv
    )
    call .venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app.py
)
endlocal
