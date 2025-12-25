from fastapi import FastAPI

app = FastAPI(title="Logan 501")

@app.get("/health")
def health():
    return {"status": "ok"}
