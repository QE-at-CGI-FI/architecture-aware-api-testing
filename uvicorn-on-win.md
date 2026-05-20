Common fixes for uvicorn on Windows:

1. Run as a Python module (most reliable)

2. Use the full path if uvicorn isn't in PATH

3. If using uv (which is in your requirements.txt)

4. Activate the virtual environment first

The python -m uvicorn approach is the most common fix — it bypasses PATH issues entirely. Since your project uses uv, uv run uvicorn main:app --reload is also a clean option that doesn't require activating the venv.