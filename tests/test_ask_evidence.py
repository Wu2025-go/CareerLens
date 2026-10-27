import unittest
import os
from unittest.mock import patch

import pandas as pd
from fastapi import HTTPException

from backend.main import AskRequest, ask_question


class AskEvidenceTests(unittest.TestCase):
    def setUp(self):
        mode = patch.dict(os.environ, {"CAREERLENS_ANSWER_MODE": "rules"})
        mode.start()
        self.addCleanup(mode.stop)
        self.rows = [
            {
                'job_id': f'TEST_{i}', 'job_title': 'Python 数据分析实习生',
                'company_name': '测试公司', 'city': '广州',
                'skills': 'Python、SQL', 'salary_min': 5, 'salary_max': 8,
                'job_description': f'记录 {i} 原文：使用 Python 分析数据。\n掌握 SQL。',
                'source': '测试数据', 'publish_date': '2026/10/26',
            }
            for i in range(7)
        ]
        self.fixture = patch('backend.main.load_jobs', return_value=pd.DataFrame(self.rows))
        self.fixture.start()
        self.addCleanup(self.fixture.stop)

    def test_unmatched_questions_do_not_return_global_statistics(self):
        for question in ['asdfghjkl', '哈哈哈哈哈哈', '!!!???', '我今天想吃饭', 'JavaScript 岗位']:
            with self.subTest(question=question):
                result = ask_question(AskRequest(question=question))
                self.assertEqual(result['matches'], [])
                self.assertEqual(result['top_skills'], [])
                self.assertEqual(result['matched_count'], 0)

    def test_evidence_is_copied_from_the_matched_record(self):
        result = ask_question(AskRequest(question='广州 Python 岗位需要哪些技能？'))
        self.assertEqual(result['answer_mode'], 'rules')
        self.assertEqual(result['matched_count'], 7)
        self.assertEqual(len(result['matches']), 5)
        by_id = {row['job_id']: row for row in self.rows}
        for match in result['matches']:
            original = by_id[match['job_id']]
            for key in ['job_description', 'source', 'publish_date']:
                self.assertEqual(match[key], original[key])
            self.assertEqual(match['dataset'], 'jobs_sample.csv')

    def test_missing_original_is_not_fabricated(self):
        self.rows[0]['job_description'] = None
        with patch('backend.main.load_jobs', return_value=pd.DataFrame(self.rows[:1])):
            result = ask_question(AskRequest(question='Python'))
        self.assertEqual(result['matches'][0]['job_description'], '')

    def test_whitespace_question_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            ask_question(AskRequest(question='   '))
        self.assertEqual(error.exception.status_code, 400)

    def mixed_rows(self):
        return [
            {**self.rows[0], 'job_id': 'ANALYST', 'job_title': '业务分析实习生',
             'job_category': '数据分析', 'skills': 'Python、SQL、Tableau',
             'job_description': '维护业务指标并完成数据提取。'},
            {**self.rows[1], 'job_id': 'COPYWRITER', 'job_title': '文案实习生',
             'job_category': '市场营销', 'skills': '数据分析、SEO',
             'job_description': '整理运营数据并撰写文案。'},
            {**self.rows[2], 'job_id': 'DEVELOPER', 'job_title': 'Python 后端开发实习生',
             'job_category': '后端开发', 'skills': 'Python、Redis',
             'job_description': '开发和维护业务接口。'},
        ]

    def test_multiple_requested_keywords_must_match_the_same_job(self):
        rows = self.mixed_rows()
        rows[0]['job_title'] = '数据分析实习生'
        with patch('backend.main.load_jobs', return_value=pd.DataFrame(rows)):
            result = ask_question(AskRequest(question='广州 Python 数据分析岗位需要哪些技能？'))
        self.assertEqual(result['matched_count'], 1)
        self.assertEqual([m['job_id'] for m in result['matches']], ['ANALYST'])
        self.assertNotIn('SEO', [s['name'] for s in result['top_skills']])

    def test_job_category_can_match_a_role_absent_from_title_and_description(self):
        rows = self.mixed_rows()
        with patch('backend.main.load_jobs', return_value=pd.DataFrame(rows)):
            result = ask_question(AskRequest(question='广州 Python 数据分析岗位需要哪些技能？'))
        self.assertEqual(result['matched_count'], 1)
        self.assertEqual(result['matches'][0]['job_id'], 'ANALYST')
        self.assertEqual(result['matches'][0]['job_category'], '数据分析')
        self.assertEqual(result['matches'][0]['job_description'], rows[0]['job_description'])

    def test_other_city_fallback_preserves_all_requested_keywords(self):
        rows = self.mixed_rows()
        rows[0]['city'] = '上海'
        with patch('backend.main.load_jobs', return_value=pd.DataFrame(rows)):
            result = ask_question(AskRequest(question='广州 Python 数据分析岗位需要哪些技能？'))
        self.assertTrue(result['fallback'])
        self.assertEqual(result['matched_count'], 1)
        self.assertEqual([m['job_id'] for m in result['matches']], ['ANALYST'])
        self.assertEqual(result['matches'][0]['city'], '上海')

    def test_partial_matches_do_not_become_evidence_or_global_statistics(self):
        rows = self.mixed_rows()[1:]
        with patch('backend.main.load_jobs', return_value=pd.DataFrame(rows)):
            result = ask_question(AskRequest(question='广州 Python 数据分析岗位需要哪些技能？'))
        self.assertEqual(result['matched_count'], 0)
        self.assertEqual(result['matches'], [])
        self.assertEqual(result['top_skills'], [])
        self.assertEqual(result['ai_status'], 'no_matches')
