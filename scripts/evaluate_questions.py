"""运行固定统计问题回归；不调用外部模型，不作为模型准确率评测。"""
import argparse
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def evaluate():
    from fastapi.testclient import TestClient
    from backend.main import app
    fixture = json.loads((ROOT / 'data/evaluation/statistics_questions.json').read_text(encoding='utf-8'))
    cases = []
    with patch.dict(os.environ, {'CAREERLENS_ANSWER_MODE': 'rules'}), TestClient(app) as client:
        for case in fixture['cases']:
            response = client.post('/api/ask', json={'question': case['question']})
            data = response.json()
            stats = data.get('statistics', {})
            observed = {'city': data.get('conditions', {}).get('city'),
                        'job_category': data.get('conditions', {}).get('job_category'),
                        'job_count': stats.get('job_count'), 'avg_salary': stats.get('avg_salary')}
            ok = response.status_code == 200 and observed == case['expected'] and data.get('dataset', {}).get('dataset_scope') == 'real'
            cases.append({'id': case['id'], 'question': case['question'], 'passed': ok,
                          'expected': case['expected'], 'observed': observed})
    return {'evaluation': '固定句式统计链路回归（规则解析与全量聚合）',
            'base_dataset_sha256': fixture['source_sha256'],
            'total': len(cases), 'passed': sum(case['passed'] for case in cases),
            'limitations': '不测真实模型回答质量，不覆盖任意复杂问法，不代表开放问答准确率。', 'cases': cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = evaluate()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"统计链路回归：{report['passed']}/{report['total']} 通过；未调用真实模型。")
    for case in report['cases']:
        if not case['passed']:
            print(json.dumps(case, ensure_ascii=False))
    return 0 if report['passed'] == report['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
