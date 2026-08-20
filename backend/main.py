from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import router as api_router

app = FastAPI(title="Sangam AI API", description="Backend for Sangam Tamil Literature AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router.router, prefix="/api")

@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "Welcome to Sangam AI API"}
