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
