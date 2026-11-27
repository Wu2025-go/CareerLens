import json
import unittest
from unittest.mock import patch

import httpx
import pandas as pd
from fastapi.testclient import TestClient

from backend import main, rag
from backend.job_matching import normalize_skill_key, split_skills


QUESTION = '我是在校本科生，会 Spring Boot 和 MyBatis，想找深圳 Java 后端实习。'
PROFILE = {'city': '深圳', 'job_category': '后端开发', 'recruitment_type': '实习',
           'education': '本科', 'skills': ['Spring Boot', 'MyBatis']}


def completion(content):
    return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
        'content': json.dumps(content, ensure_ascii=False),
    }}]})


class JobGoalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = main.load_jobs()

    def setUp(self):
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)
        mode = patch.object(rag, 'read_settings', return_value=rag.Settings(mode='rules'))
        mode.start()
        self.addCleanup(mode.stop)

    def post(self, path, payload):
        response = self.client.post('/api/' + path, json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_same_goal_across_questions_assessment_and_recommendations(self):
        parsed = self.post('job-goal/parse', {'question': QUESTION})
        self.assertEqual(parsed['parse_mode'], 'rules')
        self.assertEqual(parsed['conditions'], {**PROFILE, 'keyword': 'Java', 'min_salary': None, 'expand_city': False})
        recommendation = self.post('recommend', parsed['conditions'])
        assessment = self.post('skill-match', parsed['conditions'])
        answer = self.post('ask', {'question': QUESTION, 'goal': parsed['conditions']})
        direct = self.post('ask', {'question': QUESTION})
        for result in (recommendation, assessment, answer, direct):
            self.assertEqual(result['target_sample_count'], 1)
            self.assertEqual(result['missing_skills'], recommendation['missing_skills'])
        self.assertEqual([job['job_id'] for job in recommendation['recommendations']], ['JOB_0053'])
        self.assertEqual([job['job_id'] for job in answer['matches']], ['JOB_0053'])
        self.assertEqual(recommendation['ranking_basis'], 'coverage')
        self.assertEqual(recommendation['recommendations'][0]['match_score'], 25)

    def test_docker_gap_uses_filtered_pool_and_can_be_checked(self):
        result = self.post('recommend', PROFILE)
        self.assertEqual(result['target_sample_count'], 3)
        self.assertEqual(result['skill_sample_count'], 3)
        gap = next(item for item in result['missing_skills'] if item['name'] == 'Docker')
        self.assertEqual(gap['count'], 2)
        self.assertEqual({j['job_id'] for j in gap['evidence']}, {'JOB_0053', 'JOB_0811'})
        self.assertTrue(all(job['skill'] == 'Docker' and job['city'] == '深圳' for job in gap['evidence']))
        updated = self.post('recommend', {**PROFILE, 'skills': [*PROFILE['skills'], 'Docker']})
        self.assertEqual(updated['target_sample_count'], 3)
        self.assertNotIn('Docker', [item['name'] for item in updated['missing_skills']])
        job = next(item for item in updated['recommendations'] if item['job_id'] == 'JOB_0053')
        self.assertEqual((len(job['matched_skills']), len(job['skills'])), (3, 8))

    def test_expanding_city_requires_user_choice_and_preserves_filters(self):
        profile = {**PROFILE, 'city': '合肥', 'keyword': 'Java', 'min_salary': 4.6}
        strict = self.post('recommend', profile)
        self.assertEqual(strict['target_sample_count'], 0)
        self.assertEqual(strict['missing_skills'], [])
        self.assertTrue(strict['can_expand_city'])
        self.assertFalse(strict['fallback'])
        broader = self.post('recommend', {**profile, 'expand_city': True})
        self.assertTrue(broader['fallback'])
        self.assertGreater(broader['target_sample_count'], 0)
        self.assertTrue(all(job['city'] != '合肥' and job['job_category'] == '后端开发'
                            and job['recruitment_type'] == '实习' and job['salary_min'] >= 4.6
                            for job in broader['recommendations']))

    def test_zero_overlap_does_not_hide_target_sample_skill_gaps(self):
        result = self.post('recommend', {**PROFILE, 'skills': ['Photoshop']})
        self.assertEqual(result['target_sample_count'], 3)
        self.assertEqual(result['recommendations'], [])
        self.assertTrue(result['missing_skills'])
        self.assertFalse(result['can_expand_city'])
        self.assertFalse(result['fallback'])

    def test_stage_filter_does_not_infer_internship_from_experience(self):
        result = self.post('recommend', {**PROFILE, 'recruitment_type': '校招', 'skills': []})
        self.assertGreater(result['target_sample_count'], 0)
        self.assertTrue(all(job['recruitment_type'] == '校招' for job in result['recommendations']))
        self.assertNotIn('JOB_0053', [job['job_id'] for job in result['recommendations']])
        self.assertEqual(result['missing_skills'], [])

    def test_technical_or_matches_union_and_keeps_category(self):
        profile = {'city': '北京', 'job_category': '后端开发'}
        java = self.post('recommend', {**profile, 'keyword': 'Java'})
        python = self.post('recommend', {**profile, 'keyword': 'Python'})
        either = self.post('recommend', {**profile, 'keyword': 'Java 或 Python'})
        both = self.post('recommend', {**profile, 'keyword': 'Java Python'})
        self.assertEqual(either['target_sample_count'], java['target_sample_count'] + python['target_sample_count'] - both['target_sample_count'])
        self.assertGreater(either['target_sample_count'], both['target_sample_count'])
        self.assertTrue(all(j['job_category'] == '后端开发' for j in either['recommendations']))

    def test_parser_leaves_ambiguity_and_does_not_mark_unknown_skills_as_known(self):
        result = self.post('job-goal/parse', {'question': '岗位要求硕士，我会 Java、SQL，不会 Docker。想在深圳或广州找后端实习。'})
        self.assertEqual(set(result['ambiguous_fields']), {'city', 'education'})
        goal = result['conditions']
        self.assertIsNone(goal['city'])
        self.assertIsNone(goal['education'])
        self.assertIsNone(goal['keyword'])
        self.assertEqual(set(goal['skills']), {'Java', 'SQL'})
        self.assertEqual(goal['recruitment_type'], '实习')

    def test_ai_fills_a_supported_draft_field_and_ignores_guessed_hard_conditions(self):
        seen = []

        async def provider(settings, payload):
            seen.append(json.loads(payload['messages'][1]['content']))
            return completion({'city': '深圳', 'job_category': '后端开发', 'recruitment_type': '实习',
                               'education': '硕士', 'min_salary': 30, 'skills': ['Docker']})

        with patch.object(rag, 'read_settings', return_value=rag.Settings(api_key='unit-test-key')), \
             patch.object(rag, '_budget', rag.CallBudget()), patch.object(rag, '_post_completion', side_effect=provider):
            result = self.post('job-goal/parse', {'question': '想在深圳做后端的暑期见习，想学 Docker。'})
        self.assertEqual(result['parse_mode'], 'ai')
        self.assertEqual(result['conditions']['recruitment_type'], '实习')
        self.assertIsNone(result['conditions']['education'])
        self.assertIsNone(result['conditions']['min_salary'])
        self.assertEqual(result['conditions']['skills'], [])
        self.assertEqual(len(seen), 1)
        self.assertIn('后端开发', seen[0]['categories'])

    def test_malformed_model_draft_falls_back_to_rules(self):
        async def provider(settings, payload):
            return completion({'city': '不存在的城市', 'recruitment_type': '实习'})

        with patch.object(rag, 'read_settings', return_value=rag.Settings(api_key='unit-test-key')), \
             patch.object(rag, '_budget', rag.CallBudget()), patch.object(rag, '_post_completion', side_effect=provider):
            result = self.post('job-goal/parse', {'question': QUESTION})
        self.assertEqual(result['parse_mode'], 'rules')
        self.assertEqual(result['ai_status'], 'invalid_response')
        self.assertEqual(result['conditions']['city'], '深圳')

    def test_rag_uses_only_target_evidence_and_rejects_contradictory_skill_claim(self):
        sent = []

        async def provider(settings, payload):
            context = json.loads(payload['messages'][1]['content'])
            sent.append(context)
            text = '建议练习用 Docker 启动一个本地服务。' if len(sent) == 1 else '这条岗位不需要 Docker。'
            return completion({'evidence_insufficient': False, 'claims': [{'text': text, 'citations': [
                {'job_id': 'JOB_0053', 'quote': 'Docker'},
            ]}]})

        with patch.object(rag, 'read_settings', return_value=rag.Settings(api_key='unit-test-key')), \
             patch.object(rag, '_budget', rag.CallBudget()), patch.object(rag, '_post_completion', side_effect=provider):
            payload = {'question': QUESTION, 'goal': {**PROFILE, 'keyword': 'Java'}}
            accepted = self.post('ask', payload)
            rejected = self.post('ask', payload)
        self.assertEqual(accepted['answer_mode'], 'rag')
        self.assertEqual(accepted['citations'][0]['job_id'], 'JOB_0053')
        self.assertEqual([job['job_id'] for job in sent[0]['evidence']], ['JOB_0053'])
        self.assertEqual(sent[0]['sample_facts']['target_sample_count'], 1)
        self.assertEqual(rejected['answer_mode'], 'rules')
        self.assertEqual(rejected['ai_status'], 'invalid_response')
        self.assertIn('1 条岗位样本', rejected['answer'])

    def test_plan_rejects_new_skills_and_preserves_server_counts(self):
        baseline = self.post('recommend', PROFILE)
        original = baseline['missing_skills'][:3]
        seen = []

        async def provider(settings, payload):
            context = json.loads(payload['messages'][1]['content'])
            seen.append(context)
            skills = context['skills'] if len(seen) == 1 else ['未出现在岗位中的虚构技能']
            return completion({'steps': [{'skill': name, 'exercise': '用本地样例完成一个小练习。',
                                          'deliverable': '保存命令和运行结果。'} for name in skills]})

        with patch.object(rag, 'read_settings', return_value=rag.Settings(api_key='unit-test-key')), \
             patch.object(rag, '_budget', rag.CallBudget()), patch.object(rag, '_post_completion', side_effect=provider):
            ai = self.post('job-goal/plan', PROFILE)
            rules = self.post('job-goal/plan', PROFILE)
        self.assertEqual(ai['plan_mode'], 'ai')
        self.assertEqual(rules['plan_mode'], 'rules')
        self.assertEqual(rules['ai_status'], 'invalid_response')
        for result in (ai, rules):
            self.assertEqual(result['skill_sample_count'], 3)
            for actual, expected in zip(result['steps'], original, strict=True):
                self.assertEqual({key: actual[key] for key in expected}, expected)
        self.assertNotIn('skills', ai['steps'][0])
        self.assertIn('Dockerfile', rules['steps'][0]['exercise'])

    def test_no_target_data_does_not_call_model(self):
        with patch.object(rag, '_post_completion') as provider:
            p = self.post('job-goal/plan', {**PROFILE, 'city': '不存在的城市'})
            a = self.post('ask', {'question': QUESTION, 'goal': {**PROFILE, 'city': '不存在的城市'}})
        provider.assert_not_called()
        self.assertEqual(p['steps'], [])
        self.assertEqual(a['matches'], [])
        self.assertEqual(a['ai_status'], 'no_matches')

    def test_skill_aliases_count_only_once_per_job(self):
        row = self.dataset.loc[self.dataset.job_id == 'JOB_0053'].iloc[0].to_dict()
        row['skills'] = 'Spring Boot、springboot、Docker、Docker'
        with patch.object(main, 'load_jobs', return_value=pd.DataFrame([row])):
            result = self.post('recommend', {**PROFILE, 'skills': ['springboot']})
        self.assertEqual(result['strengths'], [{'name': 'Spring Boot', 'count': 1}])
        self.assertEqual(result['missing_skills'][0]['count'], 1)
        self.assertEqual(result['recommendations'][0]['match_score'], 50)
        self.assertEqual(len({normalize_skill_key(s) for s in split_skills(row['skills'])}), 2)
