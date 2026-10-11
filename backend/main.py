from pathlib import Path
from collections import Counter
import re

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# =========================================================
# 请求模型
# =========================================================

class AskRequest(BaseModel):
    question: str


class SkillMatchRequest(BaseModel):
    skills: list[str]
    city: str | None = None


class JobRecommendRequest(BaseModel):
    city: str | None = None
    keyword: str | None = None
    skills: list[str] | None = None
    min_salary: float | None = None
    education: str | None = None


# =========================================================
# FastAPI 应用
# =========================================================

app = FastAPI(
    title="CareerLens API",
    description="CareerLens 职见后端服务",
    version="0.6.0"
)


# =========================================================
# CORS
# =========================================================

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


# =========================================================
# 数据文件路径
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CSV_PATH = (
    BASE_DIR
    / "data"
    / "sample"
    / "jobs_sample.csv"
)


# =========================================================
# 工具函数
# =========================================================

def clean_text(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    return str(value).strip()


def safe_float(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None

        return float(value)

    except (TypeError, ValueError):
        return None


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


def salary_to_k(value):
    number = safe_float(value)

    if number is None:
        return None

    if number >= 1000:
        return number / 1000

    return number


def split_skills(value):
    text = clean_text(value)

    if not text:
        return []

    parts = re.split(
        r"[|,，、;/；]+",
        text
    )

    result = []
    seen = set()

    for skill in parts:
        skill = skill.strip()

        if not skill:
            continue

        key = skill.lower()

        if key not in seen:
            seen.add(key)
            result.append(skill)

    return result


def normalize_skills(skills):
    result = []
    seen = set()

    for skill in skills or []:
        skill = clean_text(skill)

        if not skill:
            continue

        key = skill.lower()

        if key not in seen:
            seen.add(key)
            result.append(skill)

    return result


# =========================================================
# 根接口
# =========================================================

@app.get("/")
def root():
    return {
        "message": "CareerLens API is running",
        "version": "0.6.0"
    }


# =========================================================
# 首页顶部数据
# =========================================================

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

    hot_industry = "软件开发"

    return {
        "job_count": int(job_count),
        "avg_salary": avg_salary,
        "hot_industry": hot_industry
    }


# =========================================================
# Dashboard
# =========================================================

@app.get("/api/dashboard")
def get_dashboard():
    df = load_jobs()

    # -----------------------------------------------------
    # 1. 城市岗位分布
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # 2. 薪资区间分布
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # 3. 高频技能
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # 4. 岗位趋势
    # -----------------------------------------------------

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


# =========================================================
# AI / RAG 问答
# =========================================================

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

    # -----------------------------------------------------
    # 1. 识别城市
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # 2. 技术关键词
    # -----------------------------------------------------

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
        if keyword.lower() in question_lower:
            requested_core_keywords.append(
                keyword
            )

    # 避免 JavaScript 同时误匹配 Java
    if (
        "JavaScript" in requested_core_keywords
        and "Java" in requested_core_keywords
    ):
        requested_core_keywords.remove(
            "Java"
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

    # -----------------------------------------------------
    # 3. 岗位评分
    # -----------------------------------------------------

    def score_job(row):
        job_title = clean_text(
            row.get("job_title")
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
            if keyword.lower() in searchable_text:
                score += 5
                matched_core_keywords.append(
                    keyword
                )

        if (
            requested_core_keywords
            and
            not matched_core_keywords
        ):
            return None

        for skill in row_skills:
            if skill.lower() in question_lower:
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
                matched_core_keywords
        }

    # -----------------------------------------------------
    # 4. 第一次严格检索
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # 5. 智能降级
    # -----------------------------------------------------

    fallback = False
    fallback_message = None

    if (
        target_city
        and len(results) == 0
        and "city" in df.columns
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
                f"已自动为你扩展检索其他城市的相近岗位。"
            )
        else:
            fallback_message = (
                f"当前岗位知识库中暂未找到"
                f"{target_city}符合条件的岗位，"
                f"扩展其他城市后仍未找到高度相关岗位。"
            )

    # -----------------------------------------------------
    # 6. 无结果
    # -----------------------------------------------------

    if not results:
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

    # -----------------------------------------------------
    # 7. Top 5
    # -----------------------------------------------------

    top_results = results[:5]

    # -----------------------------------------------------
    # 8. 高频技能
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # 9. 回答文本
    # -----------------------------------------------------

    if fallback:
        answer = (
            f"当前知识库暂未找到"
            f"{target_city}符合条件的岗位。"
            f"我已扩展检索其他城市，"
            f"共找到 {len(results)} 条相近岗位。"
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


# =========================================================
# 技能测评
# =========================================================

@app.post("/api/skill-match")
def skill_match(request: SkillMatchRequest):
    user_skills = normalize_skills(
        request.skills
    )

    if not user_skills:
        raise HTTPException(
            status_code=400,
            detail="请至少选择一项技能"
        )

    df = load_jobs()

    target_city = (
        clean_text(request.city)
        if request.city
        else None
    )

    fallback = False
    fallback_message = None

    # -----------------------------------------------------
    # 1. 城市筛选
    # -----------------------------------------------------

    if (
        target_city
        and "city" in df.columns
    ):
        city_df = df[
            df["city"]
            .astype(str)
            .str.strip()
            == target_city
        ]

        if not city_df.empty:
            search_df = city_df
        else:
            search_df = df
            fallback = True

            fallback_message = (
                f"当前数据集中暂无"
                f"{target_city}岗位数据，"
                f"已自动使用全部城市岗位进行技能测评。"
            )
    else:
        search_df = df

    user_skill_set = {
        skill.lower()
        for skill in user_skills
    }

    # -----------------------------------------------------
    # 2. 市场技能词频
    # -----------------------------------------------------

    market_skill_counter = Counter()

    if "skills" in search_df.columns:
        for value in search_df["skills"]:
            for skill in split_skills(value):
                market_skill_counter[skill] += 1

    # -----------------------------------------------------
    # 3. 优势技能
    # -----------------------------------------------------

    strengths = []

    for skill, count in (
        market_skill_counter
        .most_common()
    ):
        if (
            skill.lower()
            in user_skill_set
        ):
            strengths.append({
                "name": skill,
                "count": int(count)
            })

    strengths = strengths[:8]

    # -----------------------------------------------------
    # 4. 技能缺口
    # -----------------------------------------------------

    missing_skills = []

    for skill, count in (
        market_skill_counter
        .most_common()
    ):
        if (
            skill.lower()
            not in user_skill_set
        ):
            missing_skills.append({
                "name": skill,
                "count": int(count)
            })

    missing_skills = missing_skills[:8]

    # -----------------------------------------------------
    # 5. 岗位匹配
    # -----------------------------------------------------

    recommended_jobs = []

    for _, row in search_df.iterrows():
        job_skills = split_skills(
            row.get("skills")
        )

        if not job_skills:
            continue

        matched_skills = []
        missing_job_skills = []

        for skill in job_skills:
            if (
                skill.lower()
                in user_skill_set
            ):
                matched_skills.append(
                    skill
                )
            else:
                missing_job_skills.append(
                    skill
                )

        if not matched_skills:
            continue

        match_score = round(
            len(matched_skills)
            / len(job_skills)
            * 100
        )

        recommended_jobs.append({
            "job_id":
                clean_text(
                    row.get("job_id")
                ),

            "job_title":
                clean_text(
                    row.get("job_title")
                ),

            "company_name":
                clean_text(
                    row.get("company_name")
                ),

            "city":
                clean_text(
                    row.get("city")
                ),

            "education":
                clean_text(
                    row.get("education")
                ),

            "experience":
                clean_text(
                    row.get("experience")
                ),

            "salary_min":
                safe_float(
                    row.get("salary_min")
                ),

            "salary_max":
                safe_float(
                    row.get("salary_max")
                ),

            "skills":
                job_skills,

            "matched_skills":
                matched_skills,

            "missing_skills":
                missing_job_skills,

            "match_score":
                int(match_score)
        })

    recommended_jobs.sort(
        key=lambda item: (
            item["match_score"],
            len(
                item["matched_skills"]
            )
        ),
        reverse=True
    )

    top_jobs = (
        recommended_jobs[:5]
    )

    # -----------------------------------------------------
    # 6. 综合匹配分
    # -----------------------------------------------------

    if top_jobs:
        overall_score = round(
            sum(
                job["match_score"]
                for job
                in top_jobs
            )
            / len(top_jobs)
        )
    else:
        overall_score = 0

    # -----------------------------------------------------
    # 7. 等级与结论
    # -----------------------------------------------------

    if overall_score >= 80:
        level = "高度匹配"

        summary = (
            "你的技能与当前岗位需求高度匹配，"
            "已经具备较强的岗位竞争力。"
        )

    elif overall_score >= 60:
        level = "较为匹配"

        summary = (
            "你的技能已经覆盖较多岗位要求，"
            "补充部分高频技能后竞争力会进一步提升。"
        )

    elif overall_score >= 40:
        level = "基础匹配"

        summary = (
            "你已经具备一定的岗位基础，"
            "建议优先补充市场需求较高的核心技能。"
        )

    else:
        level = "待提升"

        summary = (
            "当前技能与岗位要求仍有一定差距，"
            "可以根据技能缺口制定针对性的学习计划。"
        )

    return {
        "user_skills":
            user_skills,

        "target_city":
            target_city,

        "fallback":
            fallback,

        "fallback_message":
            fallback_message,

        "overall_score":
            int(overall_score),

        "level":
            level,

        "summary":
            summary,

        "strengths":
            strengths,

        "missing_skills":
            missing_skills,

        "recommended_jobs":
            top_jobs
    }


# =========================================================
# 岗位推荐
# =========================================================

@app.post("/api/recommend")
def recommend_jobs(request: JobRecommendRequest):
    df = load_jobs()

    # -----------------------------------------------------
    # 1. 清洗用户条件
    # -----------------------------------------------------

    target_city = (
        clean_text(request.city)
        if request.city
        else None
    )

    keyword = (
        clean_text(request.keyword)
        if request.keyword
        else None
    )

    education = (
        clean_text(request.education)
        if request.education
        else None
    )

    user_skills = normalize_skills(
        request.skills
    )

    user_skill_set = {
        skill.lower()
        for skill in user_skills
    }

    no_conditions = (
        not target_city
        and not keyword
        and not user_skills
        and request.min_salary is None
        and not education
    )

    # -----------------------------------------------------
    # 2. 构造推荐结果
    # -----------------------------------------------------

    def build_recommendations(search_df):
        recommendations = []

        for _, row in search_df.iterrows():
            job_title = clean_text(
                row.get("job_title")
            )

            company_name = clean_text(
                row.get("company_name")
            )

            city = clean_text(
                row.get("city")
            )

            job_education = clean_text(
                row.get("education")
            )

            experience = clean_text(
                row.get("experience")
            )

            description = clean_text(
                row.get("job_description")
            )

            job_skills = split_skills(
                row.get("skills")
            )

            salary_min_k = salary_to_k(
                row.get("salary_min")
            )

            salary_max_k = salary_to_k(
                row.get("salary_max")
            )

            searchable_text = " ".join([
                job_title,
                description,
                " ".join(job_skills)
            ]).lower()

            score = 0
            reasons = []

            matched_skills = []
            missing_job_skills = []

            # ---------------------------------------------
            # 岗位方向
            # ---------------------------------------------

            if keyword:
                if (
                    keyword.lower()
                    in searchable_text
                ):
                    score += 35
                    reasons.append(
                        "岗位方向匹配"
                    )
                else:
                    continue

            # ---------------------------------------------
            # 技能匹配
            # ---------------------------------------------

            if user_skills:
                for skill in job_skills:
                    if (
                        skill.lower()
                        in user_skill_set
                    ):
                        matched_skills.append(
                            skill
                        )
                    else:
                        missing_job_skills.append(
                            skill
                        )

                if job_skills:
                    skill_score = round(
                        len(matched_skills)
                        / len(job_skills)
                        * 30
                    )

                    score += skill_score

                if matched_skills:
                    reasons.append(
                        f"已掌握 {len(matched_skills)} 项岗位技能"
                    )

            else:
                missing_job_skills = (
                    job_skills.copy()
                )

            # ---------------------------------------------
            # 最低薪资
            # ---------------------------------------------

            if request.min_salary is not None:
                if (
                    salary_max_k is not None
                    and
                    salary_max_k
                    >= request.min_salary
                ):
                    score += 15
                    reasons.append(
                        "薪资符合预期"
                    )

                elif salary_max_k is not None:
                    continue

            # ---------------------------------------------
            # 学历
            # ---------------------------------------------

            if (
                education
                and job_education
            ):
                if (
                    education
                    in job_education
                    or
                    job_education
                    in education
                ):
                    score += 10
                    reasons.append(
                        "学历要求匹配"
                    )

            # ---------------------------------------------
            # 无条件推荐
            # ---------------------------------------------

            if no_conditions:
                score = 50

                reasons.append(
                    "综合岗位推荐"
                )

            if score <= 0:
                continue

            recommendations.append({
                "job_id":
                    clean_text(
                        row.get("job_id")
                    ),

                "job_title":
                    job_title,

                "company_name":
                    company_name,

                "city":
                    city,

                "salary_min":
                    salary_min_k,

                "salary_max":
                    salary_max_k,

                "education":
                    job_education,

                "experience":
                    experience,

                "skills":
                    job_skills,

                "matched_skills":
                    matched_skills,

                "missing_skills":
                    missing_job_skills,

                "match_score":
                    min(
                        int(score),
                        100
                    ),

                "reasons":
                    reasons
            })

        recommendations.sort(
            key=lambda item: (
                item["match_score"],
                len(
                    item["matched_skills"]
                )
            ),
            reverse=True
        )

        return recommendations

    # -----------------------------------------------------
    # 3. 城市优先 + 自动扩展
    # -----------------------------------------------------

    fallback = False
    fallback_message = None

    if (
        target_city
        and "city" in df.columns
    ):
        city_df = df[
            df["city"]
            .astype(str)
            .str.strip()
            == target_city
        ]

        recommendations = (
            build_recommendations(
                city_df
            )
        )

        if not recommendations:
            fallback = True

            other_city_df = df[
                df["city"]
                .astype(str)
                .str.strip()
                != target_city
            ]

            recommendations = (
                build_recommendations(
                    other_city_df
                )
            )

            if recommendations:
                fallback_message = (
                    f"当前知识库中暂未找到"
                    f"{target_city}符合全部条件的岗位，"
                    f"已自动扩展到其他城市的相近岗位。"
                )
            else:
                fallback_message = (
                    f"当前知识库中暂未找到"
                    f"{target_city}符合条件的岗位，"
                    f"扩展其他城市后仍未找到合适结果。"
                )

    else:
        recommendations = (
            build_recommendations(df)
        )

    # -----------------------------------------------------
    # 4. Top 10
    # -----------------------------------------------------

    top_jobs = (
        recommendations[:10]
    )

    # -----------------------------------------------------
    # 5. 无结果
    # -----------------------------------------------------

    if not top_jobs:
        return {
            "total": 0,

            "message":
                "当前岗位知识库暂未找到符合条件的岗位，"
                "建议放宽城市、薪资或岗位方向条件。",

            "conditions": {
                "city":
                    target_city,

                "keyword":
                    keyword,

                "skills":
                    user_skills,

                "min_salary":
                    request.min_salary,

                "education":
                    education
            },

            "fallback":
                fallback,

            "fallback_message":
                fallback_message,

            "recommendations":
                []
        }

    # -----------------------------------------------------
    # 6. 返回
    # -----------------------------------------------------

    return {
        "total":
            len(recommendations),

        "message": (
            f"根据你的求职条件，"
            f"共匹配到 {len(recommendations)} 条岗位，"
            f"当前展示推荐度最高的 "
            f"{len(top_jobs)} 条。"
        ),

        "conditions": {
            "city":
                target_city,

            "keyword":
                keyword,

            "skills":
                user_skills,

            "min_salary":
                request.min_salary,

            "education":
                education
        },

        "fallback":
            fallback,

        "fallback_message":
            fallback_message,

        "recommendations":
            top_jobs
    }