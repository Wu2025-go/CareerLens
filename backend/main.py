from pathlib import Path
from collections import Counter
import re
import math
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.rag import augment_answer
from backend.auth import install_auth


# =========================================================
# 请求模型
# =========================================================

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class SkillMatchRequest(BaseModel):
    skills: list[str]
    city: str | None = None


class JobRecommendRequest(BaseModel):
    city: str | None = None
    keyword: str | None = None
    skills: list[str] | None = None
    # 单位为 K/月；0 表示不设置最低薪资。
    min_salary: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    # 求职者本人学历，用于与岗位最低学历要求比较。
    education: str | None = None


# =========================================================
# FastAPI 应用
# =========================================================

app = FastAPI(
    title="CareerLens API",
    description="CareerLens 职见后端服务",
    version="0.6.1"
)

install_auth(app)


# =========================================================
# CORS
# =========================================================

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
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
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
    """沿用当前 CSV 约定：>=1000 按元/月处理，否则按 K/月处理。"""
    number = safe_float(value)
    if number is None or number < 0:
        return None
    return number / 1000 if number >= 1000 else number


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

        key = normalize_skill_key(skill)

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

        key = normalize_skill_key(skill)

        if key not in seen:
            seen.add(key)
            result.append(skill)

    return result


# =========================================================
# 匹配工具：保留展示名称，仅将比较时使用的键规范化
# =========================================================

_SKILL_ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "golang": "go",
    "vue.js": "vue",
    "vuejs": "vue",
    "vue2": "vue",
    "vue3": "vue",
    "vue 2": "vue",
    "vue 3": "vue",
    "react.js": "react",
    "reactjs": "react",
    "nodejs": "node.js",
    "node js": "node.js",
    "springboot": "spring boot",
    "spring-boot": "spring boot",
    "springcloud": "spring cloud",
    "spring-cloud": "spring cloud",
    "k8s": "kubernetes",
    "csharp": "c#",
    "c sharp": "c#",
    "cplusplus": "c++",
    "powerbi": "power bi",
}


def normalize_skill_key(value):
    key = re.sub(r"\s+", " ", clean_text(value).casefold())
    return _SKILL_ALIASES.get(key, key)


@lru_cache(maxsize=256)
def _keyword_pattern(key):
    variants = {key}
    variants.update(
        alias for alias, canonical in _SKILL_ALIASES.items()
        if canonical == key
    )
    alternatives = []
    for variant in sorted(variants, key=lambda item: (-len(item), item)):
        escaped = re.escape(variant).replace(r"\ ", r"\s*")
        alternatives.append(escaped)
    # 使用 ASCII 边界，让 Java开发 能匹配，同时排除 JavaScript、Django。
    # 末尾同时限制 + 和 #，防止把 C++、C# 当成 C。
    return re.compile(
        r"(?<![A-Za-z0-9_])(?:" + "|".join(alternatives)
        + r")(?![A-Za-z0-9_+#])",
        re.IGNORECASE,
    )


def contains_keyword(text, keyword):
    key = normalize_skill_key(keyword)
    if not key:
        return False
    text = clean_text(text)
    if re.search(r"[A-Za-z0-9]", key):
        return bool(_keyword_pattern(key).search(text))
    return key in text.casefold()


def matches_job_keyword(text, keyword):
    """支持 Java、Java 后端、Java后端等输入；多个词必须全部命中。"""
    if contains_keyword(text, keyword):
        return True
    terms = re.findall(
        r"[A-Za-z0-9_][A-Za-z0-9_.+#-]*|[\u3400-\u9fff]+",
        clean_text(keyword),
    )
    return bool(terms) and all(contains_keyword(text, term) for term in terms)


_UNRESTRICTED_EDUCATION = {
    "不限", "学历不限", "不限学历", "无要求", "无学历要求",
    "不要求学历", "全部", "any",
}


def is_unrestricted_education(value):
    text = clean_text(value).casefold().replace(" ", "")
    return text in _UNRESTRICTED_EDUCATION or text.startswith(
        ("学历不限（", "学历不限(", "不限（", "不限(")
    )


def get_education_rank(value):
    text = clean_text(value).casefold()
    ranks = {
        "小学": 0, "初中": 0,
        "高中": 1, "中专": 1, "中技": 1, "职高": 1, "技校": 1,
        "大专": 2, "专科": 2, "高职": 2,
        "本科": 3, "学士": 3, "bachelor": 3,
        "硕士": 4, "研究生": 4, "master": 4, "mba": 4,
        "博士": 5, "phd": 5,
    }
    found = [rank for label, rank in ranks.items() if label in text]
    # “博士研究生”是博士，“硕士研究生”是硕士。
    if "博士" in text or "phd" in text:
        if not any(label in text for label in ("本科", "学士", "大专", "专科", "硕士")):
            return 5
    return min(found) if found else None


def education_is_eligible(candidate_education, job_education):
    if is_unrestricted_education(job_education):
        return True
    candidate_rank = get_education_rank(candidate_education)
    required_rank = get_education_rank(job_education)
    if candidate_rank is None or required_rank is None:
        # 缺失或未知要求无法确认符合条件，不记为学历匹配。
        return False
    if "以下" in clean_text(job_education):
        return candidate_rank <= required_rank
    return candidate_rank >= required_rank


def normalize_city(value):
    text = clean_text(value)
    return text[:-1] if text.endswith("市") else text


def recommendation_salary(row):
    lower = salary_to_k(row.get("salary_min"))
    upper = salary_to_k(row.get("salary_max"))
    if lower is not None and upper is not None and lower > upper:
        return None, None
    return lower, upper


# =========================================================
# 根接口
# =========================================================

@app.get("/")
def root():
    return {
        "message": "CareerLens API is running",
        "version": "0.6.1"
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

    hot_industry = df["job_category"].mode().iloc[0] if "job_category" in df.columns and not df["job_category"].mode().empty else "暂无数据"

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
# 岗位知识库问答（当前采用规则检索）
# =========================================================

def retrieve_question(request: AskRequest):
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

    # -----------------------------------------------------
    # 3. 岗位评分
    # -----------------------------------------------------

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
            "answer_mode": "rules",
            "matched_count": 0,
            "question":
                question,

            "answer":
                "当前岗位知识库中暂未检索到"
                "与该问题高度相关的岗位。请补充岗位方向或技能关键词，例如：深圳 Java 后端岗位需要哪些技能？",

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
        "answer_mode": "rules",
        "matched_count": len(results),
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


@app.post("/api/ask")
def ask_question(request: AskRequest):
    retrieved = retrieve_question(request)
    return augment_answer(request.question.strip(), retrieved)


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
        normalize_skill_key(skill)
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
            normalize_skill_key(skill)
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
            normalize_skill_key(skill)
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
                normalize_skill_key(skill)
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
    """基于显式条件的规则推荐；match_score 是匹配分，不是录用概率。"""
    df = load_jobs()

    target_city = clean_text(request.city) or None
    if target_city in {"不限", "全部", "全国", "所有城市"}:
        target_city = None
    keyword = clean_text(request.keyword) or None
    education = clean_text(request.education) or None
    if education and is_unrestricted_education(education):
        education = None
    if education and get_education_rank(education) is None:
        raise HTTPException(status_code=400, detail="无法识别该学历，请选择高中、中专、大专、本科、硕士或博士。")

    user_skills = normalize_skills(request.skills)
    user_skill_set = {normalize_skill_key(skill) for skill in user_skills}
    min_salary = request.min_salary if request.min_salary and request.min_salary > 0 else None

    # 只对填写的维度计分，再按实际满分换算到 0～100。
    # 城市通过候选集筛选，不人为叠加“城市匹配分”。
    total_weight = (
        (35 if keyword else 0)
        + (30 if user_skills else 0)
        + (15 if min_salary is not None else 0)
        + (10 if education else 0)
    )

    def build_recommendations(search_df):
        recommendations = []
        for _, row in search_df.iterrows():
            job_title = clean_text(row.get("job_title"))
            company_name = clean_text(row.get("company_name"))
            city = clean_text(row.get("city"))
            job_education = clean_text(row.get("education"))
            experience = clean_text(row.get("experience"))
            description = clean_text(row.get("job_description"))
            category = clean_text(row.get("job_category"))
            job_skills = split_skills(row.get("skills"))
            salary_min_k, salary_max_k = recommendation_salary(row)

            score = 0.0
            reasons = []
            primary_text = " ".join([job_title, category, " ".join(job_skills)])
            searchable_text = " ".join([primary_text, description])

            if keyword:
                if not matches_job_keyword(searchable_text, keyword):
                    continue
                if matches_job_keyword(job_title, keyword):
                    score += 35
                    reasons.append("岗位名称符合目标方向")
                elif matches_job_keyword(primary_text, keyword):
                    score += 28
                    reasons.append("岗位类别或技能符合目标方向")
                else:
                    score += 21
                    reasons.append("岗位描述包含目标关键词")

            matched_skills = [
                skill for skill in job_skills
                if normalize_skill_key(skill) in user_skill_set
            ]
            missing_job_skills = [
                skill for skill in job_skills
                if normalize_skill_key(skill) not in user_skill_set
            ]
            if user_skills:
                # 技能无交集或岗位未提供技能时，不以其他条件制造高匹配度。
                if not matched_skills:
                    continue
                score += len(matched_skills) / len(job_skills) * 30
                reasons.append(
                    f"已掌握 {len(matched_skills)}/{len(job_skills)} 项岗位技能"
                )

            if min_salary is not None:
                # 用户输入单位为 K/月；保守比较薪资下限，缺失时不能确认达标。
                if salary_min_k is None or salary_min_k < min_salary:
                    continue
                score += 15
                reasons.append("岗位薪资下限达到预期")

            if education:
                if not education_is_eligible(education, job_education):
                    continue
                score += 10
                reasons.append("个人学历符合岗位要求")

            if total_weight:
                match_score = max(0, min(100, round(score / total_weight * 100)))
            else:
                # 仅选择城市或未填写条件时展示岗位，不冒充技能测评结果。
                match_score = 50
                reasons.append(
                    "目标城市岗位，补充技能可进一步计算匹配度"
                    if target_city and normalize_city(city) == normalize_city(target_city)
                    else "综合岗位浏览，补充技能可进一步计算匹配度"
                )

            recommendations.append({
                "job_id": clean_text(row.get("job_id")),
                "job_title": job_title,
                "company_name": company_name,
                "city": city,
                "salary_min": salary_min_k,
                "salary_max": salary_max_k,
                "education": job_education,
                "experience": experience,
                "skills": job_skills,
                "matched_skills": matched_skills,
                "missing_skills": missing_job_skills,
                "match_score": int(match_score),
                "reasons": reasons,
            })

        recommendations.sort(key=lambda item: (
            -item["match_score"],
            -len(item["matched_skills"]),
            item["job_title"],
            item["job_id"],
        ))
        return recommendations

    fallback = False
    fallback_message = None
    if target_city and "city" in df.columns:
        city_mask = df["city"].map(normalize_city) == normalize_city(target_city)
        recommendations = build_recommendations(df[city_mask])
        if not recommendations:
            fallback = True
            # 扩展城市时仍保留岗位方向、技能、薪资与学历条件。
            recommendations = build_recommendations(df[~city_mask])
            fallback_message = (
                f"当前知识库中暂未找到{target_city}符合全部条件的岗位，"
                "已自动扩展到其他城市的相近岗位。"
                if recommendations else
                f"当前知识库中暂未找到{target_city}符合条件的岗位，"
                "扩展其他城市后仍未找到合适结果。"
            )
    else:
        recommendations = build_recommendations(df)
        if target_city:
            fallback = True
            fallback_message = "当前岗位数据未提供城市字段，已按其他条件检索，请核实岗位所在地。"

    top_jobs = recommendations[:10]
    conditions = {
        "city": target_city,
        "keyword": keyword,
        "skills": user_skills,
        "min_salary": request.min_salary,
        "education": education,
    }
    message = (
        f"根据你的求职条件，共匹配到 {len(recommendations)} 条岗位，"
        f"当前展示推荐度最高的 {len(top_jobs)} 条。"
        if top_jobs else
        "当前岗位知识库暂未找到符合条件的岗位，"
        "建议调整薪资、岗位方向或技能条件。"
    )
    return {
        "total": len(recommendations),
        "message": message,
        "conditions": conditions,
        "fallback": fallback,
        "fallback_message": fallback_message,
        "recommendations": top_jobs,
    }
# =========================================================
# 趋势分析
# =========================================================

@app.get("/api/trends")
def get_trends():
    df = load_jobs()

    # =====================================================
    # 1. 岗位发布时间趋势
    # =====================================================

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

    # =====================================================
    # 2. 热门技能 Top 10
    # =====================================================

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

    # =====================================================
    # 3. 城市岗位数量 Top 8
    # =====================================================

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

    # =====================================================
    # 4. 城市平均薪资
    # =====================================================

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

    # =====================================================
    # 5. 整体统计
    # =====================================================

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

    # =====================================================
    # 6. 返回
    # =====================================================

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
