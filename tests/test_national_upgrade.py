"""来源隔离、全量统计和跨页面条件一致性回归。全部测试禁止真实模型调用。"""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

import backend.main as main
from backend.datasets import read_dataset, scope_dataset
from backend.job_matching import split_skills


class NationalUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)
        cls.frame = read_dataset(main.BASE_DIR / 'data/sample/jobs_expanded.csv')

    def setUp(self):
        self.env = patch.dict(os.environ, {'CAREERLENS_ANSWER_MODE': 'rules'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def post(self, endpoint, body):
        response = self.client.post('/api/' + endpoint, json=body)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_real_and_synthetic_partitions_are_disjoint(self):
        real = scope_dataset(self.frame, 'real')
        synthetic = scope_dataset(self.frame, 'synthetic')
        self.assertEqual((len(real), len(synthetic)), (2000, 8000))
        self.assertFalse(set(real.job_id) & set(synthetic.job_id))
        self.assertEqual(set(real.job_id) | set(synthetic.job_id), set(self.frame.job_id))

    def test_default_metadata_excludes_synthetic_records(self):
        data = self.client.get('/api/dataset').json()
        self.assertEqual(data['dataset_scope'], 'real')
        self.assertEqual(data['sample_count'], 2000)
        self.assertEqual(data['origin_counts']['synthetic'], 8000)
        self.assertEqual(len(data['dataset_version']), 12)
        self.assertIn('尚缺逐岗位原网页链接', data['notice'])

    def test_dashboard_scopes_have_expected_counts(self):
        for scope, expected in [('real', 2000), ('synthetic', 8000), ('all', 10000)]:
            with self.subTest(scope=scope):
                overview = self.client.get('/api/overview', params={'dataset_scope': scope}).json()
                dashboard = self.client.get('/api/dashboard', params={'dataset_scope': scope}).json()
                self.assertEqual(overview['job_count'], expected)
                self.assertEqual(sum(dashboard['trend']['values']), expected)
                self.assertEqual(dashboard['dataset']['dataset_scope'], scope)

    def test_average_uses_all_twenty_real_records(self):
        result = self.post('ask', {'question': '北京数据分析岗位的平均薪资是多少？'})
        stats = result['statistics']
        self.assertEqual(result['answer_mode'], 'statistics')
        self.assertEqual(stats['job_count'], 20)
        self.assertEqual(stats['salary_sample_count'], 20)
        self.assertEqual(stats['avg_salary'], 12.42)
        self.assertEqual(stats['median_salary'], 13.48)
        self.assertEqual(len(stats['evidence_ids']), 20)
        self.assertIn('全部筛选样本', result['ai_notice'])

    def test_mixed_statistics_explicitly_mark_test_scope(self):
        data = self.post('ask', {'question': '北京数据分析平均薪资是多少？', 'dataset_scope': 'all'})
        self.assertEqual(data['statistics']['job_count'], 109)
        self.assertEqual(data['statistics']['avg_salary'], 14.37)
        self.assertEqual(data['dataset']['dataset_label'], '混合测试样本')
        self.assertIn('不代表真实招聘市场', data['dataset']['notice'])

    def test_statistics_never_call_language_model(self):
        with patch.object(main, 'augment_answer', side_effect=AssertionError('统计不应调用模型')):
            data = self.post('ask', {'question': '北京数据分析平均薪资是多少？'})
        self.assertEqual(data['ai_status'], 'not_required')

    def test_explicit_goal_uses_same_pool_on_all_pages(self):
        goal = {'city': '北京', 'job_category': '数据分析', 'skills': ['Excel']}
        stats = self.post('statistics', goal)
        recommend = self.post('recommend', goal)
        assessment = self.post('skill-match', goal)
        plan = self.post('job-goal/plan', goal)
        trends = self.client.get('/api/trends', params={'city': '北京', 'job_category': '数据分析'}).json()
        for data in (recommend, assessment, plan):
            self.assertEqual(data['target_sample_count'], stats['target_sample_count'])
            self.assertEqual(data['dataset']['dataset_scope'], 'real')
        self.assertEqual(trends['summary']['job_count'], stats['statistics']['job_count'])
        self.assertEqual(sum(row['count'] for row in trends['monthly_trend']), 20)

    def test_explicit_nested_goal_selects_its_dataset_scope(self):
        data = self.post('ask', {'question': '平均薪资是多少？', 'goal': {
            'city': '北京', 'job_category': '数据分析', 'dataset_scope': 'synthetic',
        }})
        self.assertEqual(data['statistics']['job_count'], 89)
        self.assertEqual(data['dataset']['dataset_scope'], 'synthetic')

    def test_city_comparison_retains_both_cities(self):
        data = self.post('ask', {'question': '北京和上海数据分析岗位的薪资比较'})
        groups = {group['city']: group for group in data['statistics']['groups']}
        self.assertEqual(set(groups), {'北京', '上海'})
        self.assertEqual(groups['北京']['job_count'], 20)
        self.assertEqual(groups['上海']['job_count'], 11)
        self.assertEqual(data['statistics']['job_count'], 31)

    def test_generic_operations_requests_clarification(self):
        data = self.post('ask', {'question': '杭州运营岗位有哪些？'})
        self.assertTrue(data['needs_confirmation'])
        self.assertIn('job_category', data['ambiguous_fields'])
        self.assertEqual(data['matches'], [])
        self.assertIn('内容运营或电商运营', data['answer'])

    def test_competition_is_not_invented_from_job_counts(self):
        data = self.post('ask', {'question': '深圳岗位竞争激烈吗？'})
        self.assertIn('无法据此判断竞争程度', data['answer'])
        self.assertEqual(data['statistics']['intent'], 'competition')

    def test_unknown_input_returns_no_global_fake_matches(self):
        data = self.post('ask', {'question': 'asdf%^?'})
        self.assertEqual(data['matched_count'], 0)
        self.assertEqual(data['top_skills'], [])

    def test_nontechnical_profile_skills_are_recognized(self):
        data = self.post('job-goal/parse', {'question': '我会 SEO 和 Photoshop，想找杭州内容运营实习'})
        self.assertEqual(set(data['conditions']['skills']), {'SEO', 'Photoshop'})
        self.assertEqual(data['conditions']['job_category'], '内容运营')

    def test_dynamic_skill_options_follow_nontechnical_category(self):
        response = self.client.get('/api/skills', params={'job_category': '内容运营'})
        data = response.json()
        names = {item['name'] for item in data['skills']}
        self.assertIn('SEO', names)
        self.assertIn('Photoshop', names)
        self.assertNotIn('Spring Boot', names)

    def test_slashes_and_programming_punctuation_are_preserved(self):
        self.assertEqual(split_skills('A/B测试|TCP/IP,CI/CD；C++、C#;.NET|IDS/IPS'),
                         ['A/B测试', 'TCP/IP', 'CI/CD', 'C++', 'C#', '.NET', 'IDS/IPS'])

    def test_empty_statistics_do_not_make_up_zero_salary(self):
        data = self.post('statistics', {'city': '没有此城市', 'job_category': '数据分析'})
        self.assertEqual(data['statistics']['job_count'], 0)
        self.assertIsNone(data['statistics']['avg_salary'])
        self.assertIsNone(data['statistics']['median_salary'])
        self.assertIn('不能计算', data['answer'])

    def test_proportion_denominator_is_explicit_and_consistent(self):
        data = self.post('ask', {'question': '深圳 Java 岗位占比是多少？'})
        stats = data['statistics']
        self.assertEqual((stats['job_count'], stats['denominator_count']), (7, 224))
        self.assertEqual(stats['share_percent'], 3.12)
        self.assertIn('取消岗位类别与关键词', stats['denominator_note'])

    def test_empty_proportion_cannot_divide_by_zero(self):
        data = self.post('statistics', {'question': '岗位占比', 'city': '没有此城市'})
        self.assertIsNone(data['statistics']['share_percent'])

    def test_statistics_do_not_silently_expand_city(self):
        data = self.post('statistics', {'city': '没有此城市', 'expand_city': True})
        self.assertEqual(data['statistics']['job_count'], 0)
        self.assertFalse(data['conditions']['expand_city'])

    def test_test_scope_evidence_has_synthetic_label(self):
        data = self.post('ask', {'question': '深圳 Java 后端岗位需要哪些技能？', 'dataset_scope': 'synthetic'})
        self.assertTrue(data['matches'])
        for job in data['matches']:
            self.assertEqual(job['data_origin'], 'synthetic')
            self.assertEqual(job['dataset'], 'jobs_expanded.csv')
            self.assertGreater(int(job['job_id'].split('_')[1]), 2000)

    def test_unfilled_profile_does_not_show_fifty_percent_match(self):
        data = self.post('recommend', {'city': '深圳'})
        self.assertTrue(data['recommendations'])
        self.assertTrue(all(job['match_score'] is None for job in data['recommendations']))

    def test_invalid_scope_is_rejected(self):
        self.assertEqual(self.client.get('/api/dataset?dataset_scope=fake').status_code, 422)
        self.assertEqual(self.client.post('/api/recommend', json={'dataset_scope': 'fake'}).status_code, 422)

    def test_invalid_trend_filters_are_validation_errors(self):
        for params in [{'min_salary': -1}, {'min_salary': 'inf'}, {'recruitment_type': 'fake'}]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get('/api/trends', params=params).status_code, 422)

    def test_missing_origin_is_not_assumed_to_be_real(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'unverified.csv'
            self.frame.head(2).drop(columns='data_origin').to_csv(path, index=False)
            data = read_dataset(path)
            self.assertEqual(set(data.data_origin), {'unverified'})
            self.assertTrue(scope_dataset(data, 'real').empty)

    def test_duplicate_ids_and_invalid_origin_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, frame in [('duplicates', self.frame.head(1).loc[[0, 0]]),
                                ('origin', self.frame.head(1).assign(data_origin='fabricated'))]:
                with self.subTest(name=name):
                    path = Path(directory) / f'{name}.csv'
                    frame.to_csv(path, index=False)
                    with self.assertRaises(HTTPException) as caught:
                        read_dataset(path)
                    self.assertEqual(caught.exception.status_code, 503)


if __name__ == '__main__':
    unittest.main()
