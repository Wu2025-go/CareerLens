from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CareerLens API",
    description="CareerLens 职见后端服务",
    version="0.1.0"
)

# 允许 Vue 前端访问后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "CareerLens API is running"
    }


@app.get("/api/overview")
def get_overview():
    return {
        "job_count": 1000,
        "avg_salary": 13.6,
        "hot_industry": "软件开发"
    }