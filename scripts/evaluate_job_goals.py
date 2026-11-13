"""用固定样本比较两版问答检索；不调用模型。"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


ROOT = Path(__file__).resolve().parents[1]
DATA = Path('data/sample/jobs_sample.csv')


class Case(NamedTuple):
    question: str
    city: str = ''
    category: str = ''
    stage: str = ''
    # 每组必须同时满足；多个组满足任意一组即可。
    keywords: tuple[tuple[str, ...], ...] = ()
    degree: str = ''
    salary: float = 0
    needs_confirmation: bool = False


CASES = [
    Case('深圳本科在校生，想找 Java 后端实习，需要补什么技能？',
         '深圳', '后端开发', '实习', (('Java',),), '本科'),
    Case('深圳 Java 后端开发岗位需要哪些技能？', '深圳', '后端开发', keywords=(('Java',),)),
    Case('深圳后端实习需要哪些技能？', '深圳', '后端开发', '实习'),
    Case('我是本科生，想找深圳前端实习。', '深圳', '前端开发', '实习', degree='本科'),
    Case('我是本科生，广州 Python 数据分析实习有哪些？',
         '广州', '数据分析', '实习', (('Python',),), '本科'),
    Case('广州内容运营实习有哪些岗位？', '广州', '内容运营', '实习'),
    Case('北京 Python 数据分析岗位需要哪些技能？', '北京', '数据分析', keywords=(('Python',),)),
    Case('北京 Java 或 Python 后端开发岗位有哪些？',
         '北京', '后端开发', keywords=(('Java',), ('Python',))),
    Case('上海 Vue 前端开发有哪些岗位？', '上海', '前端开发', keywords=(('Vue',),)),
    Case('我是硕士在读，上海算法工程师校招有哪些？', '上海', '算法工程师', '校招', degree='硕士'),
    Case('杭州后端开发校招有哪些？', '杭州', '后端开发', '校招'),
    Case('杭州 MySQL 后端开发岗位有哪些？', '杭州', '后端开发', keywords=(('MySQL',),)),
    Case('成都测试开发实习有哪些？', '成都', '测试开发', '实习'),
    Case('南京大数据开发校招有哪些？', '南京', '数据开发', '校招'),
    Case('深圳 Docker 后端实习，最低薪资 5K，有哪些岗位？',
         '深圳', '后端开发', '实习', (('Docker',),), salary=5),
    Case('合肥 Java 后端实习有哪些？', '合肥', '后端开发', '实习', (('Java',),)),
    Case('北京或深圳的前端实习有哪些？', needs_confirmation=True),
    Case('深圳 Java Spring Boot 后端实习有哪些？',
         '深圳', '后端开发', '实习', (('Java', 'Spring Boot'),)),
]


def reference_match(row, case):
    """独立用 CSV 字段判定这批用例的条件，不调用待测解析器或排序器。"""
    if case.needs_confirmation:
        return False
    if case.city and case.city != row['city'].removesuffix('市'):
        return False
    if case.category and case.category != row['job_category']:
        return False
    title = row['job_title']
    if case.stage == '实习' and '实习' not in title and not re.search(r'\bintern(?:ship)?\b', title, re.I):
        return False
    if case.stage == '校招' and ('实习' in title or not any(x in title for x in ('校招', '校园招聘', '应届', '毕业生'))):
        return False
    if case.degree:
        # 这批固定用例只包含本科与硕士；本文件中的学历字段已核对。
        allowed = {'学历不限', '大专', '大专及以上', '本科', '本科及以上'}
        if case.degree == '硕士':
            allowed.add('硕士')
        if row['education'] not in allowed:
            return False
    if case.salary:
        lower = float(row['salary_min'] or 0)
        lower = lower / 1000 if lower >= 1000 else lower
        if lower < case.salary:
            return False
    searchable = ' '.join(row[key] for key in ('job_title', 'job_category', 'skills', 'job_description'))
    if case.keywords:
        def has(phrase):
            pattern = r'spring[\s-]*boot' if phrase == 'Spring Boot' else re.escape(phrase)
            return bool(re.search(r'(?<![A-Za-z0-9_])' + pattern + r'(?![A-Za-z0-9_+#])', searchable, re.I))
        if not any(all(has(phrase) for phrase in group) for group in case.keywords):
            return False
    return True


WORKER = """
import json, sys
from backend.main import AskRequest, ask_question
results = []
for question in json.load(sys.stdin):
    data = ask_question(AskRequest(question=question))
    results.append({
        'matched_count': data.get('matched_count', 0),
        'shown_ids': [row['job_id'] for row in data.get('matches', [])],
    })
print(json.dumps(results))
"""


def run_version(root):
    env = {**os.environ, 'CAREERLENS_ANSWER_MODE': 'rules', 'PYTHONIOENCODING': 'utf-8'}
    result = subprocess.run(
        [sys.executable, '-c', WORKER], cwd=root, env=env,
        input=json.dumps([case.question for case in CASES], ensure_ascii=False),
        encoding='utf-8', stdout=subprocess.PIPE, check=True,
    )
    return json.loads(result.stdout)


def summarize(results, expected):
    shown, bad, passes = 0, 0, 0
    for result, valid in zip(results, expected, strict=True):
        ids = result['shown_ids']
        result['out_of_scope'] = sum(job_id not in valid for job_id in ids)
        result['pass'] = (result['matched_count'] == len(valid) and not result['out_of_scope']
                          and len(set(ids)) == len(ids) == min(5, len(valid)))
        shown += len(ids)
        bad += result['out_of_scope']
        passes += result['pass']
    return {'cases_passed': passes, 'shown': shown, 'out_of_scope': bad}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, help='旧版项目根目录；建议使用提交 0cab786')
    args = parser.parse_args()
    raw = (ROOT / DATA).read_bytes()
    if args.baseline and raw != (args.baseline / DATA).read_bytes():
        parser.error('两份岗位样本文件不同，不能直接对照。')
    with (ROOT / DATA).open(encoding='utf-8-sig', newline='') as file:
        rows = list(csv.DictReader(file))
    expected = [{row['job_id'] for row in rows if reference_match(row, case)} for case in CASES]
    current = run_version(ROOT)
    baseline = run_version(args.baseline) if args.baseline else None
    report = {
        'dataset_sha256': hashlib.sha256(raw).hexdigest(),
        'sample_size': len(rows),
        'case_count': len(CASES),
        'current': summarize(current, expected),
        'baseline': summarize(baseline, expected) if baseline is not None else None,
        'cases': [
            {
                'id': f'Q{idx + 1:02}', 'question': case.question,
                'expected_count': len(expected[idx]),
                'needs_confirmation': case.needs_confirmation,
                'current': current[idx], 'baseline': baseline[idx] if baseline is not None else None,
            }
            for idx, case in enumerate(CASES)
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report['current']['cases_passed'] != len(CASES))


if __name__ == '__main__':
    sys.exit(main())
