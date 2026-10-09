from pathlib import Path
from collections import Counter
import re

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="CareerLens API",
    description="CareerLens 职见后端服务",
    version="0.2.0"
)


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# 数据文件路径
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

CSV_PATH = (
    BASE_DIR
    / "data"
    / "sample"
    / "jobs_sample.csv"
)


# =========================
# 读取岗位数据
# =========================

def load_jobs():
    if not CSV_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"找不到数据文件：{CSV_PATH}"
        )

    try:
        df = pd.read_csv(CSV_PATH)
    except UnicodeDecodeError:
        # 某些中文 CSV 可能是 GBK 编码
        df = pd.read_csv(
            CSV_PATH,
            encoding="gbk"
        )

    return df


# =========================
# 薪资处理
# =========================

def salary_to_k(value):
    """
    将薪资统一换算成 k/月。
    例如：
    6000 -> 6
    13.5 -> 13.5
    """

    try:
        value = float(value)

        if value > 1000:
            return value / 1000

        return value

    except (TypeError, ValueError):
        return None


# =========================
# 技能拆分
# =========================

def split_skills(value):
    if pd.isna(value):
        return []

    text = str(value).strip()

    if not text:
        return []

    # 支持 |、逗号、中英文逗号、/、; 等分隔符
    parts = re.split(
        r"[|,，、;/；]+",
        text
    )

    return [
        skill.strip()
        for skill in parts
        if skill.strip()
    ]


# =========================
# 根接口
# =========================

@app.get("/")
def root():
    return {
        "message": "CareerLens API is running"
    }


# =========================
# 首页顶部数据
# =========================

@app.get("/api/overview")
def get_overview():

    df = load_jobs()

    # 岗位总量
    job_count = len(df)

    # 平均薪资
    salary_values = []

    for _, row in df.iterrows():

        salary_min = salary_to_k(
            row.get("salary_min")
        )

        salary_max = salary_to_k(
            row.get("salary_max")
        )

        if (
            salary_min is not None
            and salary_max is not None
        ):
            salary_values.append(
                (salary_min + salary_max) / 2
            )

    avg_salary = (
        round(
            sum(salary_values)
            / len(salary_values),
            1
        )
        if salary_values
        else 0
    )

    # 当前 CSV 没有 industry 字段
    # 暂时保留项目当前分类名称
    hot_industry = "软件开发"

    return {
        "job_count": job_count,
        "avg_salary": avg_salary,
        "hot_industry": hot_industry
    }


# =========================
# Dashboard 数据
# =========================

@app.get("/api/dashboard")
def get_dashboard():

    df = load_jobs()

    # -------------------------
    # 1. 城市岗位分布
    # -------------------------

    city_counts = (
        df["city"]
        .dropna()
        .astype(str)
        .str.strip()
        .value_counts()
    )

    top_cities = city_counts.head(6)

    max_city_count = (
        int(top_cities.max())
        if not top_cities.empty
        else 1
    )

    cities = []

    for city, count in top_cities.items():

        # 转换成 0~100 的相对长度
        percentage = round(
            int(count)
            / max_city_count
            * 100
        )

        cities.append({
            "name": city,
            "count": int(count),
            "value": percentage
        })


    # -------------------------
    # 2. 薪资区间分布
    # -------------------------

    salary_midpoints = []

    for _, row in df.iterrows():

        salary_min = salary_to_k(
            row.get("salary_min")
        )

        salary_max = salary_to_k(
            row.get("salary_max")
        )

        if (
            salary_min is not None
            and salary_max is not None
        ):
            salary_midpoints.append(
                (salary_min + salary_max) / 2
            )


    salary_bins = {
        "5k以下": 0,
        "5-10k": 0,
        "10-15k": 0,
        "15-25k": 0,
        "25k+": 0
    }


    for salary in salary_midpoints:

        if salary < 5:
            salary_bins["5k以下"] += 1

        elif salary < 10:
            salary_bins["5-10k"] += 1

        elif salary < 15:
            salary_bins["10-15k"] += 1

        elif salary < 25:
            salary_bins["15-25k"] += 1

        else:
            salary_bins["25k+"] += 1


    salary_distribution = [
        {
            "range": name,
            "value": value
        }
        for name, value
        in salary_bins.items()
    ]


    # -------------------------
    # 3. 高频技能
    # -------------------------

    skill_counter = Counter()

    if "skills" in df.columns:

        for value in df["skills"]:

            skills = split_skills(value)

            for skill in skills:
                skill_counter[skill] += 1


    skills = [
        item[0]
        for item
        in skill_counter.most_common(8)
    ]


    # -------------------------
    # 4. 岗位趋势
    # -------------------------

    months = []
    values = []

    if "publish_date" in df.columns:

        dates = pd.to_datetime(
            df["publish_date"],
            errors="coerce"
        )

        valid_dates = dates.dropna()

        if not valid_dates.empty:

            month_counts = (
                valid_dates
                .dt.to_period("M")
                .value_counts()
                .sort_index()
            )

            months = [
                f"{period.month}月"
                for period
                in month_counts.index
            ]

            values = [
                int(value)
                for value
                in month_counts.values
            ]


    return {
        "cities": cities,
        "salary_distribution":
            salary_distribution,
        "trend": {
            "months": months,
            "values": values
        },
        "skills": skills
    }