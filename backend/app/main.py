from fastapi import FastAPI

app = FastAPI(title="CrossVerse API")

@app.get("/")
def root():
    return {
        "name": "CrossVerse",
        "description": "Cross-religious scripture exploration engine",
        "status": "running"
    }
