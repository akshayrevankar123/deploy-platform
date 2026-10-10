"""A tiny sample 'student project' for the deployment platform to scan and deploy.

Push this folder to its OWN GitHub repository (not inside deploy-platform), register that
repository in the platform, and click Scan: it should pass the quick pre-flight check.
"""
from fastapi import FastAPI

app = FastAPI(title="Sample Student App")


@app.get("/")
def home():
    return {"message": "Hello from my deployed project!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/add")
def add(a: int, b: int):
    return {"result": a + b}
