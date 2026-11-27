"""只读检查岗位数据；不会去重、改写来源或删除记录。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from backend.datasets import read_dataset
from backend.job_matching import normalize_skill_key, salary_to_k, split_skills


def validate(path):
    frame = read_dataset(path)
    salaries = frame[['salary_min', 'salary_max']].map(salary_to_k)
    invalid_salary = (salaries.isna().any(axis=1) | (salaries.salary_min > salaries.salary_max))
    dates = pd.to_datetime(frame.publish_date, errors='coerce')
    skills = {normalize_skill_key(name) for value in frame.skills for name in split_skills(value)}
    return {
        'file': Path(path).name, 'sha256': sha256(Path(path).read_bytes()).hexdigest(),
        'row_count': len(frame), 'origin_counts': frame.data_origin.value_counts().to_dict(),
        'city_count': int(frame.city.nunique()), 'category_count': int(frame.job_category.nunique()),
        'canonical_skill_count': len(skills),
        'publish_date_start': str(dates.min().date()) if dates.notna().any() else None,
        'publish_date_end': str(dates.max().date()) if dates.notna().any() else None,
        'invalid_salary_count': int(invalid_salary.sum()),
        'invalid_publish_date_count': int(dates.isna().sum()),
        'blank_cells': {key: int(frame[key].astype(str).str.strip().eq('').sum()) for key in frame},
        'duplicate_title_company_city_extra_rows': int(frame.duplicated(['job_title', 'company_name', 'city']).sum()),
        'duplicate_description_extra_rows': int(frame.job_description.duplicated().sum()),
        'records_with_original_url': int(frame.get('source_url', pd.Series(dtype=str)).astype(str).str.match(r'https?://').sum()),
        'notes': [
            '来源分类由团队说明提供，未完成逐岗位原网页核验。',
            '同公司同名同城只是疑似重复；不同批次招聘可能合法，本工具不自动删除。',
            '仿真记录不能计入真实招聘规模或用于证明薪资市场结论。',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=ROOT / 'data/sample/jobs_expanded.csv')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = validate(args.csv)
    content = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + '\n', encoding='utf-8')
    print(content)
    return 1 if report['invalid_salary_count'] or report['invalid_publish_date_count'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
