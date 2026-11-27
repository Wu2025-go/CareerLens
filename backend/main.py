from pathlib import Path
from collections import Counter
import re

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.rag import augment_answer
from backend.auth import install_auth
from backend.goal_assistant import (
    GoalQuestion, interpret_job_goal, make_practice_plan, parse_goal_rules, retrieve_for_goal,
)
from backend.job_matching import (
    JobGoal, JobRecommendRequest, SkillMatchRequest, analyze_job_goal,
    clean_text, contains_keyword, matching_options, safe_float, salary_to_k, split_skills,
)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    goal: JobGoal | None = None


app = FastAPI(
    title="CareerLens API",
    description="CareerLens 职见后端服务",
    version="0.7.0"
)

install_auth(app)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    # 兼容 Vite 因端口占用而自动使用 5174 等本地端口。
    allow_origin_regex=r"http://(?:localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE_DIR = Path(__file__).resolve().parent.parent

CSV_PATH = (
    BASE_DIR
    / "data"
    / "sample"
    / "jobs_sample.csv"
)

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


@app.get("/")
def root():
    return {
        "message": "CareerLens API is running",
        "version": "0.7.0"
    }

@app.get("/api/overview")
def get_overview():
    df = load_jobs()

    job_count = len(df)

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

    hot_industry = df["job_category"].mode().iloc[0] if "job_category" in df.columns and not df["job_category"].mode().empty else "暂无数据"

    return {
        "job_count": int(job_count),
        "avg_salary": avg_salary,
        "hot_industry": hot_industry
    }


@app.get("/api/dashboard")
def get_dashboard():
    df = load_jobs()

 

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


def retrieve_question(request: AskRequest, df=None):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="问题不能为空"
        )

    df = load_jobs() if df is None else df

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


    core_keywords = [
        "Spring Cloud",
        "Spring Boot",
        "JavaScript",
        "TypeScript",
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

    role_keywords = [
        "前端",
        "后端",
        "开发",
        "算法",
        "测试",
        "运维",
        "数据分析"
    ]

    requested_core_keywords = []

    for keyword in core_keywords:
        if contains_keyword(question, keyword):
            requested_core_keywords.append(
                keyword
            )

    # 避免 Spring Cloud / Spring Boot 同时重复计算 Spring
    if (
        (
            "Spring Cloud"
            in requested_core_keywords
            or
            "Spring Boot"
            in requested_core_keywords
        )
        and
        "Spring" in requested_core_keywords
    ):
        requested_core_keywords.remove(
            "Spring"
        )


    def score_job(row):
        job_title = clean_text(
            row.get("job_title")
        )

        job_category = clean_text(
            row.get("job_category")
        )

        company_name = clean_text(
            row.get("company_name")
        )

        city = clean_text(
            row.get("city")
        )

        education = clean_text(
            row.get("education")
        )

        experience = clean_text(
            row.get("experience")
        )

        job_description = clean_text(
            row.get("job_description")
        )

        row_skills = split_skills(
            row.get("skills")
        )

        searchable_text = " ".join([
            job_title,
            job_category,
            company_name,
            education,
            experience,
            job_description,
            " ".join(row_skills)
        ]).lower()

        score = 0
        matched_skills = []
        matched_core_keywords = []

        for keyword in requested_core_keywords:
            if contains_keyword(searchable_text, keyword):
                score += 5
                matched_core_keywords.append(
                    keyword
                )

        if (
            requested_core_keywords
            and
            len(matched_core_keywords) != len(requested_core_keywords)
        ):
            # 多个明确关键词必须由同一岗位满足，不能混合不同岗位的部分命中。
            return None

        for skill in row_skills:
            if contains_keyword(question, skill):
                score += 4
                matched_skills.append(
                    skill
                )

        for role in role_keywords:
            if (
                role in question
                and role in searchable_text
            ):
                score += 2

        if (
            "后端" in question
            and "后端" in job_title
        ):
            score += 3

        if (
            "前端" in question
            and "前端" in job_title
        ):
            score += 3

        if (
            "数据分析" in question
            and "数据分析" in searchable_text
        ):
            score += 3

        if (
            "算法" in question
            and "算法" in searchable_text
        ):
            score += 3

        if score <= 0:
            return None

        return {
            "score":
                int(score),

            "job_id":
                clean_text(
                    row.get("job_id")
                ),

            "job_title":
                job_title,

            "job_category": job_category,

            "company_name":
                company_name,

            "city":
                city,

            "salary_min":
                safe_float(
                    row.get("salary_min")
                ),

            "salary_max":
                safe_float(
                    row.get("salary_max")
                ),

            "education":
                education,

            "experience":
                experience,

            "skills":
                clean_text(
                    row.get("skills")
                ),

            "matched_skills":
                matched_skills,

            "matched_keywords":
                matched_core_keywords,

            # 原文直接来自该条 CSV 记录，不由规则模板生成或改写。
            "job_description": job_description,
            "source": clean_text(row.get("source")),
            "publish_date": clean_text(row.get("publish_date")),
            "dataset": "jobs_sample.csv"
        }


    if (
        target_city
        and "city" in df.columns
    ):
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


    if not results:
        return {
            "answer_mode": "rules",
            "matched_count": 0,
            "question":
                question,

            "answer":
                "当前岗位知识库中暂未检索到"
                "与该问题高度相关的岗位。请补充岗位方向或技能关键词，例如：深圳 Java 后端岗位需要哪些技能？",

            "target_city":
                target_city,

            "fallback": False,
            "can_expand_city": bool(target_city),
            "fallback_message": (
                f"{target_city}暂无符合条件的岗位。可整理求职条件后主动查看其他城市。"
                if target_city else None
            ),

            "top_skills":
                [],

            "matches":
                []
        }

    top_results = results[:5]

    skill_counter = Counter()

    for result in results:
        for skill in split_skills(
            result.get("skills")
        ):
            skill_counter[skill] += 1

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


    city_text = target_city or '当前数据集'
    answer = f'根据当前岗位知识库，共检索到 {len(results)} 条{city_text}相关岗位。'

    if skill_names:
        answer += (
            f"这些岗位中较高频的技能包括："
            f"{skill_names}。"
        )

    return {
        "answer_mode": "rules",
        "matched_count": len(results),
        "question":
            question,

        "answer":
            answer,

        "target_city":
            target_city,

        "fallback": False,
        "fallback_message": None,

        "top_skills":
            top_skills,

        "matches":
            top_results
    }


@app.post("/api/ask")
def ask_question(request: AskRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(400, '问题不能为空')
    df = load_jobs()
    if request.goal is not None:
        retrieved = retrieve_for_goal(df, request.goal)
    else:
        goal, ambiguous = parse_goal_rules(question, matching_options(df))
        if ambiguous:
            retrieved = {
                'answer': '问题里有需要确认的筛选条件。请点击「整理为求职条件」，核对后再分析。',
                'matched_count': 0, 'matches': [], 'top_skills': [],
            }
        elif any(goal[key] for key in ('job_category', 'recruitment_type', 'education', 'min_salary', 'skills', 'keyword')):
            retrieved = retrieve_for_goal(df, JobGoal(**goal), confirmed=False)
        else:
            # 普通知识库问答继续支持未预设的技术词。
            retrieved = retrieve_question(request, df)
    return augment_answer(question, retrieved)


@app.get("/api/job-goal/options")
def job_goal_options():
    return matching_options(load_jobs())


@app.post('/api/job-goal/parse')
def parse_job_goal(request: GoalQuestion):
    question = request.question.strip()
    if not question:
        raise HTTPException(400, '请输入求职目标')
    return interpret_job_goal(load_jobs(), question)


@app.post('/api/job-goal/plan')
def job_goal_plan(request: SkillMatchRequest):
    if not any(clean_text(skill) for skill in request.skills):
        raise HTTPException(400, '请先填写已掌握的技能')
    return make_practice_plan(load_jobs(), request)


@app.post("/api/skill-match")
def skill_match(request: SkillMatchRequest):
    if not any(clean_text(skill) for skill in request.skills):
        raise HTTPException(status_code=400, detail="请至少选择一项技能")

    analysis = analyze_job_goal(load_jobs(), request, coverage_only=True)
    jobs = analysis["recommendations"][:5]
    score = round(sum(job["match_score"] for job in jobs) / len(jobs)) if jobs else 0
    if not analysis["target_sample_count"]:
        level = "暂无目标岗位样本"
    elif not analysis["skill_sample_count"]:
        level = "样本缺少技能标签"
    elif not jobs:
        level = "未匹配到已掌握技能"
    elif score >= 80:
        level = "覆盖较高"
    elif score >= 60:
        level = "覆盖过半"
    elif score >= 40:
        level = "具备部分基础"
    else:
        level = "可优先补技能"

    return {
        **analysis,
        "user_skills": analysis["conditions"]["skills"],
        "target_city": analysis["conditions"]["city"],
        "overall_score": score,
        "level": level,
        "summary": (
            f"综合覆盖分为展示的 {len(jobs)} 条岗位的平均技能覆盖分。"
            if jobs else analysis["message"]
        ),
        "recommended_jobs": jobs,
    }


@app.post("/api/recommend")
def recommend_jobs(request: JobRecommendRequest):
    return analyze_job_goal(load_jobs(), request)


@app.get("/api/trends")
def get_trends():
    df = load_jobs()


    monthly_trend = []

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

            monthly_trend = [
                {
                    "month":
                        str(period),

                    "label":
                        f"{period.month}月",

                    "count":
                        int(count)
                }
                for period, count
                in month_counts.items()
            ]


    skill_counter = Counter()

    if "skills" in df.columns:
        for value in df["skills"]:
            skills = split_skills(value)

            for skill in skills:
                skill_counter[skill] += 1

    top_skills = [
        {
            "name": skill,
            "count": int(count)
        }
        for skill, count
        in skill_counter.most_common(10)
    ]


    city_jobs = []

    if "city" in df.columns:
        city_counts = (
            df["city"]
            .dropna()
            .astype(str)
            .str.strip()
            .value_counts()
            .head(8)
        )

        city_jobs = [
            {
                "city":
                    city,

                "count":
                    int(count)
            }
            for city, count
            in city_counts.items()
        ]


    city_salary_data = {}

    for _, row in df.iterrows():
        city = clean_text(
            row.get("city")
        )

        salary_min = salary_to_k(
            row.get("salary_min")
        )

        salary_max = salary_to_k(
            row.get("salary_max")
        )

        if (
            not city
            or salary_min is None
            or salary_max is None
        ):
            continue

        avg_salary = (
            salary_min + salary_max
        ) / 2

        if city not in city_salary_data:
            city_salary_data[city] = []

        city_salary_data[city].append(
            avg_salary
        )

    city_salary = []

    for city, salaries in city_salary_data.items():
        if not salaries:
            continue

        average = round(
            sum(salaries)
            / len(salaries),
            1
        )

        city_salary.append({
            "city":
                city,

            "avg_salary":
                average,

            "job_count":
                len(salaries)
        })

    city_salary.sort(
        key=lambda item:
            item["avg_salary"],
        reverse=True
    )

    city_salary = city_salary[:8]


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
                (
                    salary_min
                    + salary_max
                ) / 2
            )

    overall_avg_salary = (
        round(
            sum(salary_values)
            / len(salary_values),
            1
        )
        if salary_values
        else 0
    )


    return {
        "summary": {
            "job_count":
                int(len(df)),

            "city_count":
                int(
                    df["city"]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .nunique()
                )
                if "city" in df.columns
                else 0,

            "skill_count":
                int(
                    len(skill_counter)
                ),

            "avg_salary":
                overall_avg_salary
        },

        "monthly_trend":
            monthly_trend,

        "top_skills":
            top_skills,

        "city_jobs":
            city_jobs,

        "city_salary":
            city_salary
    }
