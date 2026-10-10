from pathlib import Path
from collections import Counter
import re

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# =========================
# 请求数据模型
# =========================

class AskRequest(BaseModel):
    question: str


# =========================
# FastAPI 应用
# =========================

app = FastAPI(
    title="CareerLens API",
    description="CareerLens 职见后端服务",
    version="0.3.0"
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
    15000 -> 15
    13.5 -> 13.5
    """

    try:
        value = float(value)

        if value >= 1000:
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

    # 支持：
    # |
    # ,
    # ，
    # 、
    # ;
    # ；
    # /
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

    # -------------------------
    # 1. 岗位总量
    # -------------------------

    job_count = len(df)


    # -------------------------
    # 2. 平均薪资
    # -------------------------

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


    # -------------------------
    # 3. 热门行业
    # -------------------------

    # 当前 CSV 暂时没有 industry 字段。
    # 后面可以根据 job_title 自动归类。
    hot_industry = "软件开发"


    return {
        "job_count": int(job_count),
        "avg_salary": avg_salary,
        "hot_industry": hot_industry
    }


# =========================
# Dashboard 数据
# =========================

@app.get("/api/dashboard")
def get_dashboard():

    df = load_jobs()


    # =========================
    # 1. 城市岗位分布
    # =========================

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


    # =========================
    # 2. 薪资区间分布
    # =========================

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
            "value": int(value)
        }
        for name, value
        in salary_bins.items()
    ]


    # =========================
    # 3. 高频技能
    # =========================

    skill_counter = Counter()

    if "skills" in df.columns:

        for value in df["skills"]:

            row_skills = split_skills(value)

            for skill in row_skills:
                skill_counter[skill] += 1


    skills = [
        skill
        for skill, _
        in skill_counter.most_common(8)
    ]


    # =========================
    # 4. 岗位趋势
    # =========================

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


# =========================
# AI / RAG 检索问答
# =========================

@app.post("/api/ask")
def ask_question(request: AskRequest):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="问题不能为空"
        )

    df = load_jobs()

    question_lower = question.lower()


    # =========================
    # 1. 识别用户指定城市
    # =========================

    target_city = None

    if "city" in df.columns:

        all_cities = (
            df["city"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        for city in all_cities:

            if city and city in question:

                target_city = city

                break


    # 如果用户明确指定城市，
    # 只在对应城市中检索
    if target_city:

        search_df = df[
            df["city"]
            .astype(str)
            .str.strip()
            == target_city
        ]

    else:

        search_df = df


    # =========================
    # 2. 技术关键词
    # =========================

    keywords = [
        "Java",
        "Python",
        "SQL",
        "Linux",
        "Go",
        "K8s",
        "Spring",
        "Spring Boot",
        "MySQL",
        "Redis",
        "Docker",
        "Vue",
        "React",
        "JavaScript",
        "数据分析",
        "数据清洗",
        "机器学习",
        "深度学习",
        "前端",
        "后端",
        "开发",
        "算法",
        "测试",
        "运维"
    ]


    # =========================
    # 3. 检索岗位
    # =========================

    results = []


    for _, row in search_df.iterrows():

        job_title = str(
            row.get(
                "job_title",
                ""
            )
        ).strip()

        company_name = str(
            row.get(
                "company_name",
                ""
            )
        ).strip()

        job_description = str(
            row.get(
                "job_description",
                ""
            )
        ).strip()

        city = str(
            row.get(
                "city",
                ""
            )
        ).strip()

        education = str(
            row.get(
                "education",
                ""
            )
        ).strip()

        experience = str(
            row.get(
                "experience",
                ""
            )
        ).strip()


        row_skills = split_skills(
            row.get(
                "skills",
                ""
            )
        )


        searchable_text = " ".join([
            job_title,
            company_name,
            city,
            education,
            experience,
            job_description,
            " ".join(row_skills)
        ]).lower()


        score = 0

        matched_skills = []


        # -------------------------
        # 技能直接匹配
        # -------------------------

        for skill in row_skills:

            if (
                skill.lower()
                in question_lower
            ):

                score += 4

                matched_skills.append(
                    skill
                )


        # -------------------------
        # 技术关键词匹配
        # -------------------------

        for keyword in keywords:

            if (
                keyword.lower()
                in question_lower
                and
                keyword.lower()
                in searchable_text
            ):

                score += 2


        # -------------------------
        # 岗位方向匹配
        # -------------------------

        if (
            "后端" in question
            and
            "后端" in job_title
        ):
            score += 3


        if (
            "前端" in question
            and
            "前端" in job_title
        ):
            score += 3


        if (
            "开发" in question
            and
            "开发" in job_title
        ):
            score += 2


        if (
            "数据分析" in question
            and
            "数据分析"
            in searchable_text
        ):
            score += 3


        if (
            "算法" in question
            and
            "算法"
            in searchable_text
        ):
            score += 3


        # -------------------------
        # 保存有效结果
        # -------------------------

        if score > 0:

            results.append({
                "score": int(score),

                "job_id":
                    str(
                        row.get(
                            "job_id",
                            ""
                        )
                    ),

                "job_title":
                    job_title,

                "company_name":
                    company_name,

                "city":
                    city,

                "salary_min":
                    float(
                        row.get(
                            "salary_min",
                            0
                        )
                    )
                    if pd.notna(
                        row.get(
                            "salary_min"
                        )
                    )
                    else None,

                "salary_max":
                    float(
                        row.get(
                            "salary_max",
                            0
                        )
                    )
                    if pd.notna(
                        row.get(
                            "salary_max"
                        )
                    )
                    else None,

                "education":
                    education,

                "experience":
                    experience,

                "skills":
                    str(
                        row.get(
                            "skills",
                            ""
                        )
                    ),

                "matched_skills":
                    matched_skills
            })


    # =========================
    # 4. 按匹配分数排序
    # =========================

    results.sort(
        key=lambda item:
            item["score"],
        reverse=True
    )


    top_results = results[:5]


    # =========================
    # 5. 没找到相关岗位
    # =========================

    if not top_results:

        city_text = (
            f"{target_city}地区"
            if target_city
            else ""
        )

        return {
            "question":
                question,

            "answer":
                f"当前岗位知识库中暂未检索到"
                f"{city_text}与该问题高度相关的岗位。",

            "target_city":
                target_city,

            "top_skills":
                [],

            "matches":
                []
        }


    # =========================
    # 6. 根据检索结果统计技能
    # =========================

    skill_counter = Counter()


    for result in results:

        for skill in split_skills(
            result.get(
                "skills",
                ""
            )
        ):

            skill_counter[
                skill
            ] += 1


    top_skills = [
        {
            "name": skill,
            "count": int(count)
        }
        for skill, count
        in skill_counter.most_common(8)
    ]


    # =========================
    # 7. 自动生成基础答案
    # =========================

    city_text = (
        target_city
        if target_city
        else "当前数据集"
    )


    skill_names = "、".join(
        item["name"]
        for item
        in top_skills[:5]
    )


    if skill_names:

        answer = (
            f"根据当前岗位知识库，"
            f"共检索到 {len(results)} 条"
            f"{city_text}相关岗位。"
            f"这些岗位中较高频的技能包括："
            f"{skill_names}。"
        )

    else:

        answer = (
            f"根据当前岗位知识库，"
            f"共检索到 {len(results)} 条"
            f"{city_text}相关岗位。"
        )


    # =========================
    # 8. 返回问答结果
    # =========================

    return {
        "question":
            question,

        "answer":
            answer,

        "target_city":
            target_city,

        "top_skills":
            top_skills,

        "matches":
            top_results
    }