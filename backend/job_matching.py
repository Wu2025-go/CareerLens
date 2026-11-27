"""统一岗位筛选、技能覆盖和证据统计。"""
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import math
import re
from typing import Annotated, Literal

import pandas as pd
from fastapi import HTTPException
from pydantic import BaseModel, Field


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


_COMPOUND_SKILLS = {
    name for name in {*_SKILL_ALIASES, *_SKILL_ALIASES.values(), 'restful api'} if ' ' in name
}
_KEYWORD_TERMS = re.compile(
    '|'.join(r'(?<![A-Za-z0-9_])' + re.escape(name).replace(r'\ ', r'\s+') + r'(?![A-Za-z0-9_+#])'
             for name in sorted(_COMPOUND_SKILLS, key=lambda item: (-len(item), item)))
    + r'|[A-Za-z0-9_][A-Za-z0-9_.+#-]*|[\u3400-\u9fff]+', re.IGNORECASE,
)


def matches_job_keyword(text, keyword):
    """支持 Java、Java 后端、Java后端等输入；多个词必须全部命中。"""
    if contains_keyword(text, keyword):
        return True
    terms = _KEYWORD_TERMS.findall(clean_text(keyword))
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


Education = Literal['高中', '中专', '大专', '本科', '硕士', '博士']
RecruitmentType = Literal['实习', '校招']
SkillName = Annotated[str, Field(max_length=80)]


class JobGoal(BaseModel):
    city: str | None = Field(default=None, max_length=40)
    job_category: str | None = Field(default=None, max_length=60)
    recruitment_type: RecruitmentType | None = None
    # 技术关键词支持空格表示同时匹配，以及“或”表示择一匹配。
    keyword: str | None = Field(default=None, max_length=120)
    skills: list[SkillName] | None = Field(default=None, max_length=40)
    education: str | None = Field(default=None, max_length=40)
    min_salary: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    expand_city: bool = False


class SkillMatchRequest(JobGoal):
    skills: list[SkillName] = Field(max_length=40)


class JobRecommendRequest(JobGoal):
    pass


def matching_options(df):
    def values(column):
        if column not in df:
            return []
        normalize = normalize_city if column == 'city' else clean_text
        return sorted({normalize(value) for value in df[column]} - {''})

    return {'cities': values('city'), 'categories': values('job_category')}


def recruitment_type_of(title):
    """只依据岗位标题的明确标记；经验不限不等于实习或校招。"""
    title = clean_text(title)
    if re.search(r'实习|\bintern(?:ship)?\b', title, re.I):
        return '实习'
    if re.search(r'校招|校园招聘|应届|毕业生', title):
        return '校招'
    return None


_ALTERNATIVE = re.compile(r'或者|或|(?<![A-Za-z0-9_])or(?![A-Za-z0-9_])', re.I)


def keyword_fit(keyword, title, category, skills, description):
    if not keyword:
        return 0, ''
    terms = [term.strip() for term in _ALTERNATIVE.split(keyword) if term.strip()]
    primary = ' '.join([title, category, *skills])
    full = ' '.join([primary, description])
    for content, weight, label in (
        (title, 35, '岗位名称命中技术关键词'),
        (primary, 28, '岗位类别或技能命中技术关键词'),
        (full, 21, '岗位描述提到技术关键词'),
    ):
        if any(matches_job_keyword(content, term) for term in terms):
            return weight, label
    return 0, ''


def normalize_goal(request):
    city = clean_text(request.city)
    if city in {'不限', '全部', '全国', '所有城市', '全部城市'}:
        city = ''
    education = clean_text(request.education)
    if is_unrestricted_education(education):
        education = ''
    if education and get_education_rank(education) is None:
        raise HTTPException(400, '无法识别该学历，请选择高中、中专、大专、本科、硕士或博士。')
    return {
        'city': normalize_city(city) or None,
        'job_category': clean_text(request.job_category) or None,
        'recruitment_type': request.recruitment_type,
        'keyword': clean_text(request.keyword) or None,
        'education': education or None,
        'min_salary': request.min_salary or None,
        'skills': normalize_skills(request.skills),
        'expand_city': request.expand_city,
    }


@dataclass
class JobPool:
    conditions: dict
    jobs: list[dict]
    fallback: bool = False
    fallback_message: str | None = None
    can_expand_city: bool = False


def select_job_pool(df, request):
    """先确定求职目标样本，技能交集只参与后续个性化排序。"""
    conditions = normalize_goal(request)
    city = conditions['city']

    def eligible(frame):
        jobs = []
        for row in frame.to_dict('records'):
            title = clean_text(row.get('job_title'))
            category = clean_text(row.get('job_category'))
            stage = recruitment_type_of(title)
            degree = clean_text(row.get('education'))
            lower, upper = recommendation_salary(row)
            if conditions['job_category'] and category != conditions['job_category']:
                continue
            if conditions['recruitment_type'] and stage != conditions['recruitment_type']:
                continue
            if conditions['education'] and not education_is_eligible(conditions['education'], degree):
                continue
            floor = conditions['min_salary']
            if floor is not None and (lower is None or lower < floor):
                continue
            skills = split_skills(row.get('skills'))
            description = clean_text(row.get('job_description'))
            points, reason = keyword_fit(conditions['keyword'], title, category, skills, description)
            if conditions['keyword'] and not points:
                continue
            jobs.append({
                'job_id': clean_text(row.get('job_id')),
                'job_title': title,
                'company_name': clean_text(row.get('company_name')),
                'city': clean_text(row.get('city')),
                'job_category': category,
                'recruitment_type': stage,
                'education': degree,
                'experience': clean_text(row.get('experience')),
                'salary_min': lower,
                'salary_max': upper,
                'source': clean_text(row.get('source')),
                'publish_date': clean_text(row.get('publish_date')),
                'skills': skills,
                '_keyword_points': points,
                '_keyword_reason': reason,
                '_job_description': description,
                '_raw_skills': clean_text(row.get('skills')),
            })
        return jobs

    if not city:
        return JobPool(conditions, eligible(df))
    if 'city' not in df:
        return JobPool(conditions, [], fallback_message='样本没有城市字段，无法确认目标城市。')
    local_mask = df['city'].map(normalize_city) == city
    local = eligible(df[local_mask])
    if local:
        return JobPool(conditions, local)
    if not conditions['expand_city']:
        return JobPool(
            conditions, [], can_expand_city=True,
            fallback_message=f'{city}暂无符合全部条件的岗位。可调整条件，或主动查看其他城市。',
        )
    other = eligible(df[~local_mask])
    return JobPool(
        conditions, other, fallback=True,
        fallback_message=(
            f'{city}暂无符合条件的岗位。以下为其他城市样本，其他筛选条件保持一致。'
            if other else f'{city}及其他城市均未找到符合这些条件的岗位。'
        ),
    )


def rank_jobs(pool, *, coverage_only=False, include_unmatched=False):
    conditions = pool.conditions
    user_keys = {normalize_skill_key(skill) for skill in conditions['skills']}
    by_coverage = coverage_only or bool(conditions['job_category'] or conditions['recruitment_type'])
    active_weight = (
        (35 if conditions['keyword'] else 0) + (30 if user_keys else 0)
        + (15 if conditions['min_salary'] is not None else 0) + (10 if conditions['education'] else 0)
    )
    ranked = []
    for job in pool.jobs:
        matched = [name for name in job['skills'] if normalize_skill_key(name) in user_keys]
        missing = [name for name in job['skills'] if normalize_skill_key(name) not in user_keys]
        if user_keys and not matched and not include_unmatched:
            continue
        coverage = len(matched) / len(job['skills']) if job['skills'] else 0
        reasons = [job['_keyword_reason']] if job['_keyword_reason'] else []
        if conditions['job_category']:
            reasons.append(f"岗位类别为{conditions['job_category']}")
        if conditions['recruitment_type']:
            reasons.append(f"岗位标题明确标注{conditions['recruitment_type']}")
        if user_keys:
            reasons.append(f"已掌握 {len(matched)}/{len(job['skills'])} 项岗位技能")
        if conditions['min_salary'] is not None:
            reasons.append('岗位薪资下限达到预期')
        if conditions['education']:
            reasons.append('个人学历符合样本要求')
        if not reasons:
            reasons.append('符合当前浏览范围，可补充技能查看个人匹配')

        points = job['_keyword_points'] + coverage * 30
        points += 15 if conditions['min_salary'] is not None else 0
        points += 10 if conditions['education'] else 0
        if by_coverage and user_keys:
            score = round(coverage * 100)
        else:
            score = round(points / active_weight * 100) if active_weight else 50
        item = {key: value for key, value in job.items() if not key.startswith('_')}
        item.update(matched_skills=matched, missing_skills=missing, match_score=score, reasons=reasons)
        # 用未四舍五入的覆盖率排序，显示分相同时再比较已掌握的数量。
        sort_score = coverage if by_coverage and user_keys else score
        ranked.append(((-sort_score, -len(matched), job['job_title'], job['job_id']), item))
    ranked.sort(key=lambda entry: entry[0])
    return [item for _, item in ranked], 'coverage' if by_coverage else 'combined'


def skill_evidence(pool):
    user_keys = {normalize_skill_key(skill) for skill in pool.conditions['skills']}
    sample_count = sum(bool(job['skills']) for job in pool.jobs)
    if not user_keys:
        return {'skill_sample_count': sample_count, 'strengths': [], 'missing_skills': []}

    counts = Counter()
    labels = {}
    evidence = {}
    for job in pool.jobs:
        for name in job['skills']:
            key = normalize_skill_key(name)
            counts[key] += 1
            labels.setdefault(key, name)
            if key in user_keys:
                continue
            records = evidence.setdefault(key, [])
            if len(records) < 3 and job['job_id']:
                records.append({
                    field: job[field] for field in (
                        'job_id', 'job_title', 'company_name', 'city', 'source', 'publish_date',
                    )
                } | {'skill': name})
    ordered = sorted(counts, key=lambda key: (-counts[key], key))
    return {
        'skill_sample_count': sample_count,
        'strengths': [
            {'name': labels[key], 'count': counts[key]} for key in ordered if key in user_keys
        ][:8],
        'missing_skills': [
            {'name': labels[key], 'count': counts[key], 'evidence': evidence.get(key, [])}
            for key in ordered if key not in user_keys
        ][:8],
    }


def analyze_job_goal(df, request, *, coverage_only=False):
    pool = select_job_pool(df, request)
    ranked, ranking_basis = rank_jobs(pool, coverage_only=coverage_only)
    if not pool.jobs:
        message = pool.fallback_message or '当前样本中没有符合全部条件的岗位，可调整筛选条件。'
    elif not ranked:
        message = f'找到 {len(pool.jobs)} 条目标岗位，但没有技能交集。可先查看下方待补技能。'
    else:
        message = f'找到 {len(pool.jobs)} 条目标岗位，展示 {min(len(ranked), 10)} 条。'
    return {
        'conditions': pool.conditions,
        'target_sample_count': len(pool.jobs),
        'target_cities': sorted({job['city'] for job in pool.jobs} - {''}),
        'fallback': pool.fallback,
        'fallback_message': pool.fallback_message,
        'can_expand_city': pool.can_expand_city,
        'ranking_basis': ranking_basis,
        'total': len(ranked),
        'message': message,
        'recommendations': ranked[:10],
        **skill_evidence(pool),
    }
