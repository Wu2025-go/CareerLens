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
@app.get("/api/dashboard")
def get_dashboard():
    return {
        "cities": [
    {"name": "广州", "value": 88},
    {"name": "深圳", "value": 82},
    {"name": "北京", "value": 76},
    {"name": "上海", "value": 70}
],

        "salary_distribution": [
            {"range": "5k以下", "value": 28},
            {"range": "5-10k", "value": 55},
            {"range": "10-15k", "value": 72},
            {"range": "15-25k", "value": 46},
            {"range": "25k+", "value": 20}
        ],

        "trend": {
            "months": ["4月", "5月", "6月", "7月", "8月", "9月"],
            "values": [420, 510, 480, 620, 670, 760]
        },

        "skills": [
            "Java",
            "Python",
            "SQL",
            "Spring",
            "数据清洗",
            "Linux",
            "机器学习",
            "Git"
        ]
    }