"""在完整筛选样本上计算指标；模型不负责计算招聘统计。"""
from collections import Counter
from statistics import mean, median
from decimal import Decimal, ROUND_HALF_UP
import re

import pandas as pd
from pydantic import Field

from backend.datasets import attach_metadata
from backend.job_matching import JobGoal, normalize_skill_key, select_job_pool


class StatisticsRequest(JobGoal):
    question: str = Field(default='', max_length=2000)


def statistics_intent(question):
    if re.search(r'竞争|内卷|好找吗|难找吗', question):
        return 'competition'
    if re.search(r'对比|比较|相比|哪个城市|哪里.*(?:高|多)', question):
        return 'comparison'
    if re.search(r'占比|比例|百分之', question):
        return 'proportion'
    if re.search(r'趋势|按月|每月|月度|分布', question):
        return 'trend'
    if re.search(r'均薪|平均.*(?:薪|工资)|(?:薪资|月薪|工资).*平均|中位数|薪资.*多少|工资.*多少|月薪.*多少', question):
        return 'salary'
    if re.search(r'多少(?:条|个)?(?:相关)?(?:岗位|职位)|(?:岗位|职位).*(?:数量|总数|多少)|岗位数|职位数', question):
        return 'count'
    return None


def _salaries(jobs):
    return [(Decimal(str(job['salary_min'])) + Decimal(str(job['salary_max']))) / 2 for job in jobs
            if job['salary_min'] is not None and job['salary_max'] is not None]


def _summary(jobs):
    salaries = _salaries(jobs)
    rounded = lambda value: float(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    return {
        'job_count': len(jobs), 'salary_sample_count': len(salaries),
        'avg_salary': rounded(mean(salaries)) if salaries else None,
        'median_salary': rounded(median(salaries)) if salaries else None,
    }


def build_statistics(frame, request, *, intent='salary', compared_cities=None):
    # 统计不自动扩城，防止“某城市均薪”实际使用其他城市的数据。
    request = request.model_copy(update={'expand_city': False})
    if compared_cities:
        frame = frame.loc[frame.city.isin(compared_cities)].copy()
    pool = select_job_pool(frame, request)
    jobs = pool.jobs
    skill_counts, labels, months = Counter(), {}, Counter()
    dates = pd.to_datetime([job['publish_date'] for job in jobs], errors='coerce')
    for date in dates:
        if not pd.isna(date):
            months[str(date.to_period('M'))] += 1
    for job in jobs:
        for skill in job['skills']:
            key = normalize_skill_key(skill)
            skill_counts[key] += 1
            labels.setdefault(key, skill)
    groups = []
    if intent == 'comparison':
        for city in (compared_cities or sorted({j['city'] for j in jobs})):
            groups.append({'city': city, **_summary([j for j in jobs if j['city'] == city])})
    denominator = None
    if intent == 'proportion':
        denominator_request = request.model_copy(update={'job_category': None, 'keyword': None})
        denominator = len(select_job_pool(frame, denominator_request).jobs)
    stats = {
        'intent': intent, **_summary(jobs),
        'denominator_count': denominator,
        'share_percent': round(len(jobs) / denominator * 100, 2) if denominator else None,
        'denominator_note': '保留城市、学历、招聘类型和薪资条件，取消岗位类别与关键词后的样本数。',
        'salary_unit': 'K/月',
        'salary_method': '先取每条有效岗位标注薪资区间的中点，再计算均值和中位数；不是实发工资。',
        'monthly_counts': [{'month': month, 'count': count} for month, count in sorted(months.items())],
        'top_skills': [{'name': labels[key], 'count': count} for key, count in skill_counts.most_common(10)],
        'groups': groups,
        'evidence_ids': [job['job_id'] for job in jobs[:20]],
        'evidence_preview_limit': 20,
        'compared_cities': compared_cities or [],
    }
    scope = '、'.join(x for x in [request.city, request.job_category, request.recruitment_type, request.keyword] if x) or '当前筛选范围'
    if compared_cities:
        scope = '、'.join(compared_cities) + ('的' + request.job_category if request.job_category else '')
    if intent == 'competition':
        answer = f'{scope}共有 {len(jobs)} 条岗位样本。现有数据没有投递人数、招聘名额或录用率，无法据此判断竞争程度。'
    elif not jobs:
        answer = f'{scope}暂无符合条件的岗位样本，不能计算薪资均值或推断市场没有需求。'
    elif intent == 'comparison':
        answer = '；'.join(f"{group['city']} {group['job_count']} 条，薪资区间中点均值 " +
                         (f"{group['avg_salary']:.2f}K/月" if group['avg_salary'] is not None else '暂无有效数据')
                         for group in groups) + '。各城市样本量不同，结果仅描述当前样本。'
    elif intent == 'proportion':
        answer = f'{scope}有 {len(jobs)} 条，占同范围全部岗位类别样本 {denominator} 条的 {stats["share_percent"]:.2f}%。'
    elif intent == 'trend':
        answer = f'{scope}共有 {len(jobs)} 条，以下按岗位发布日期展示月度样本分布；不代表连续采集得到的市场变化。'
    elif intent == 'count':
        answer = f'{scope}共有 {len(jobs)} 条符合条件的岗位样本，数量基于全部命中记录计算。'
    elif stats['avg_salary'] is not None:
        answer = (f'{scope}共有 {len(jobs)} 条岗位，{stats["salary_sample_count"]} 条提供有效薪资。'
                  f'岗位薪资区间中点均值为 {stats["avg_salary"]:.2f}K/月，中位数为 {stats["median_salary"]:.2f}K/月。')
    else:
        answer = f'{scope}有 {len(jobs)} 条岗位，但缺少可用薪资，暂不能计算均值。'
    return attach_metadata({
        'answer': answer, 'answer_mode': 'statistics', 'ai_status': 'not_required',
        'ai_notice': '数量与薪资由程序对全部筛选样本计算，未调用大模型。',
        'matched_count': len(jobs), 'target_sample_count': len(jobs),
        'conditions': pool.conditions, 'statistics': stats,
        'top_skills': stats['top_skills'], 'matches': [], 'citations': [],
        'reference_integrity_checked': False, 'target_city': request.city,
    }, frame)
