# Sample student app

A minimal FastAPI app used to demo the deployment platform.

1. Copy this whole folder OUT of `deploy-platform` into a new folder, and push it to a new public GitHub repo.
2. In the platform, register that repo URL and click **Scan project**. Expect `passed`.
3. Run locally:
   ```
   pip install -r requirements-dev.txt
   pytest -q
   uvicorn main:app --reload
   ```
