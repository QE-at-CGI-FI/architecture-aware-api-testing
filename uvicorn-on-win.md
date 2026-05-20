Common fixes for uvicorn on Windows:

1. Run as a Python module (most reliable)
   python -m uvicorn main:app --reload

2. Use the full path if uvicorn isn't in PATH
   python -m uvicorn main:app --host 127.0.0.1 --port 8000

3. If using uv (which is in your requirements.txt)
   uv run uvicorn main:app --reload

4. Activate the virtual environment first

.venv\Scripts\activate
uvicorn main:app --reload

The python -m uvicorn approach is the most common fix — it bypasses PATH issues entirely. Since your project uses uv, uv run uvicorn main:app --reload is also a clean option that doesn't require activating the venv.
