from pathlib import Path
from collections import Counter
import re

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# =========================
# 请求模型
# =========================

class AskRequest(BaseModel):
    question: str


# =========================
# FastAPI 应用
# =========================

app = FastAPI(
    title="CareerLens API",
    description="CareerLens 职见后端服务",
    version="0.4.0"
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
        return pd.read_csv(CSV_PATH)

    except UnicodeDecodeError:
        try:
            return pd.read_csv(
                CSV_PATH,
                encoding="gb18030"
            )

        except UnicodeDecodeError:
            return pd.read_csv(
                CSV_PATH,
                encoding="gbk"
            )


# =========================
# 薪资处理
# =========================

def salary_to_k(value):
    """
    将薪资统一转换为 k/月。

    例如：
    6000  -> 6
    15000 -> 15
    13.5  -> 13.5
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

    # 当前数据暂时没有 industry 字段
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

    cities = []

    if "city" in df.columns:
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
            for skill in split_skills(value):
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
# AI / RAG 问答
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
    # 1. 识别城市
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


    # =========================
    # 2. 核心技术关键词
    # =========================

    core_keywords = [
        "Spring Cloud",
        "Spring Boot",
        "JavaScript",
        "数据分析",
        "数据清洗",
        "机器学习",
        "深度学习",
        "Python",
        "Java",
        "SQL",
        "Linux",
        "K8s",
        "Spring",
        "MySQL",
        "Redis",
        "Kafka",
        "Docker",
        "Vue",
        "React",
        "Go"
    ]


    # =========================
    # 3. 岗位方向关键词
    # =========================

    role_keywords = [
        "前端",
        "后端",
        "开发",
        "算法",
        "测试",
        "运维"
    ]


    # =========================
    # 4. 提取问题核心关键词
    # =========================

    requested_core_keywords = []

    for keyword in core_keywords:
        if keyword.lower() in question_lower:
            requested_core_keywords.append(
                keyword
            )


    # JavaScript 中包含 Java，
    # 避免误认为用户同时问 Java
    if (
        "JavaScript" in requested_core_keywords
        and
        "Java" in requested_core_keywords
    ):
        requested_core_keywords.remove(
            "Java"
        )


    # =========================
    # 5. 单条岗位评分
    # =========================

    def score_job(row):
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

        job_description = str(
            row.get(
                "job_description",
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
            education,
            experience,
            job_description,
            " ".join(row_skills)
        ]).lower()


        score = 0

        matched_skills = []

        matched_core_keywords = []


        # =========================
        # 核心技术关键词匹配
        # =========================

        for keyword in requested_core_keywords:
            if (
                keyword.lower()
                in searchable_text
            ):
                score += 5

                matched_core_keywords.append(
                    keyword
                )


        # 如果用户明确指定技术，
        # 但岗位完全不含这些技术，
        # 直接排除。
        if (
            requested_core_keywords
            and
            not matched_core_keywords
        ):
            return None


        # =========================
        # skills 字段直接匹配
        # =========================

        for skill in row_skills:
            if skill.lower() in question_lower:
                score += 4

                matched_skills.append(
                    skill
                )


        # =========================
        # 岗位方向匹配
        # =========================

        for role in role_keywords:
            if (
                role in question
                and
                role in searchable_text
            ):
                score += 2


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
            "数据分析" in question
            and
            "数据分析" in searchable_text
        ):
            score += 3


        if (
            "算法" in question
            and
            "算法" in searchable_text
        ):
            score += 3


        if score <= 0:
            return None


        salary_min = row.get(
            "salary_min"
        )

        salary_max = row.get(
            "salary_max"
        )


        return {
            "score":
                int(score),

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
                float(salary_min)
                if pd.notna(salary_min)
                else None,

            "salary_max":
                float(salary_max)
                if pd.notna(salary_max)
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
                matched_skills,

            "matched_keywords":
                matched_core_keywords
        }


    # =========================
    # 6. 首次严格城市检索
    # =========================

    if target_city:
        search_df = df[
            df["city"]
            .astype(str)
            .str.strip()
            == target_city
        ]

    else:
        search_df = df


    results = []


    for _, row in search_df.iterrows():
        result = score_job(row)

        if result:
            results.append(result)


    results.sort(
        key=lambda item:
            item["score"],
        reverse=True
    )


    # =========================
    # 7. 智能降级
    # =========================

    fallback = False

    fallback_message = None


    if (
        target_city
        and len(results) == 0
    ):
        fallback = True


        other_city_df = df[
            df["city"]
            .astype(str)
            .str.strip()
            != target_city
        ]


        fallback_results = []


        for _, row in other_city_df.iterrows():
            result = score_job(row)

            if result:
                fallback_results.append(
                    result
                )


        fallback_results.sort(
            key=lambda item:
                item["score"],
            reverse=True
        )


        results = fallback_results


        if results:
            fallback_message = (
                f"当前岗位知识库中暂未找到"
                f"{target_city}符合条件的岗位，"
                f"已自动为你扩展检索其他城市"
                f"的相近岗位。"
            )

        else:
            fallback_message = (
                f"当前岗位知识库中暂未找到"
                f"{target_city}符合条件的岗位，"
                f"扩展其他城市后仍未找到"
                f"高度相关岗位。"
            )


    # =========================
    # 8. 完全没有结果
    # =========================

    if len(results) == 0:
        return {
            "question":
                question,

            "answer":
                "当前岗位知识库中暂未检索到"
                "与该问题高度相关的岗位。",

            "target_city":
                target_city,

            "fallback":
                fallback,

            "fallback_message":
                fallback_message,

            "top_skills":
                [],

            "matches":
                []
        }


    # =========================
    # 9. Top 5
    # =========================

    top_results = results[:5]


    # =========================
    # 10. 高频技能统计
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


    skill_names = "、".join(
        item["name"]
        for item
        in top_skills[:5]
    )


    # =========================
    # 11. 生成回答
    # =========================

    if fallback:
        answer = (
            f"当前知识库暂未找到"
            f"{target_city}符合条件的岗位。"
            f"我已扩展检索其他城市，"
            f"共找到 {len(results)} 条"
            f"相近岗位。"
        )

    else:
        city_text = (
            target_city
            if target_city
            else "当前数据集"
        )

        answer = (
            f"根据当前岗位知识库，"
            f"共检索到 {len(results)} 条"
            f"{city_text}相关岗位。"
        )


    if skill_names:
        answer += (
            f"这些岗位中较高频的技能包括："
            f"{skill_names}。"
        )


    # =========================
    # 12. 返回结果
    # =========================

    return {
        "question":
            question,

        "answer":
            answer,

        "target_city":
            target_city,

        "fallback":
            fallback,

        "fallback_message":
            fallback_message,

        "top_skills":
            top_skills,

        "matches":
            top_results
    }