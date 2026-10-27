"""RAG回归检查：全部使用模拟HTTP，不读取或发送真实模型密钥。"""

import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import httpx

from backend import rag
from scripts.configure_ai import save_configuration


TEST_KEY = "sk-test-only-not-a-secret"


def retrieval():
    return {
        "answer": "规则结果：检索到7条岗位。", "answer_mode": "rules", "matched_count": 7,
        "question": "广州 Python 岗位需要哪些技能？", "target_city": "广州",
        "fallback": False, "fallback_message": None,
        "top_skills": [{"name": "Python", "count": 7}],
        "matches": [
            {"job_id": "JOB_0001", "job_title": "Python数据分析实习生", "city": "广州", "company_name": "测试企业A",
             "skills": "Python、SQL", "job_description": "使用Python完成数据清洗与分析。\n掌握SQL查询。", "source": "测试样本", "publish_date": "2026/10/26"},
            {"job_id": "JOB_0002", "job_title": "数据工程师", "city": "广州", "company_name": "测试企业B",
             "skills": "Python、Linux", "job_description": "维护数据处理流程并编写自动化脚本。", "source": "测试样本", "publish_date": "2026/10/25"},
        ],
    }


def document():
    return {"evidence_insufficient": False, "claims": [
        {"text": "样本岗位需要使用Python完成数据清洗与分析。", "citations": [
            {"job_id": "JOB_0001", "quote": "使用Python完成数据清洗与分析。"},
        ]},
    ]}


def completion(doc=None):
    return {
        "model": "deepseek-flash", "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(document() if doc is None else doc, ensure_ascii=False)}}],
    }


class RagTests(unittest.TestCase):
    def setUp(self):
        self.settings = rag.Settings(api_key=TEST_KEY)
        self.data = retrieval()
        budget = patch.object(rag, "_budget", rag.CallBudget())
        budget.start()
        self.addCleanup(budget.stop)

    def respond(self, body=None, status=200, handler=None, settings=None, data=None):
        calls = []
        def transport(request):
            calls.append(request)
            if handler:
                return handler(request)
            return httpx.Response(status, json=completion() if body is None else body)
        client = httpx.AsyncClient(transport=httpx.MockTransport(transport))
        with patch.object(rag.httpx, "AsyncClient", return_value=client):
            result = rag.augment_answer("广州 Python 岗位需要哪些技能？", self.data if data is None else data, settings or self.settings)
        return result, calls

    def assert_rules(self, result, status):
        self.assertEqual(result["answer_mode"], "rules")
        self.assertEqual(result["ai_status"], status)
        self.assertFalse(result["reference_integrity_checked"])
        self.assertEqual(result["citations"], [])
        self.assertNotIn(TEST_KEY, json.dumps(result, ensure_ascii=False))

    def test_generated_only_after_valid_model_response(self):
        result, calls = self.respond()
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["answer_mode"], "rag")
        self.assertEqual(result["ai_status"], "generated")
        self.assertTrue(result["reference_integrity_checked"])
        self.assertIn("[JOB_0001]", result["answer"])
        self.assertEqual(result["llm_usage"]["total_tokens"], 150)
        self.assertEqual(result["citations"][0]["field"], "job_description")
        self.assertEqual(result["matched_count"], 7)
        self.assertNotIn(TEST_KEY, json.dumps(result))

    def test_wire_request_contains_evidence_but_not_key_in_prompt(self):
        _, calls = self.respond()
        request = calls[0]
        self.assertEqual(str(request.url), "https://api.deepseek.com/chat/completions")
        self.assertEqual(request.headers["Authorization"], "Bearer " + TEST_KEY)
        payload = json.loads(request.content)
        self.assertEqual(payload["model"], "deepseek-flash")
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertFalse(payload["stream"])
        self.assertIn("json", payload["messages"][0]["content"].lower())
        context = json.loads(payload["messages"][1]["content"])
        self.assertEqual(context["evidence"][0]["job_description"], self.data["matches"][0]["job_description"])
        self.assertNotIn(TEST_KEY, json.dumps(payload))

    def test_missing_key_does_not_call_model(self):
        result, calls = self.respond(settings=replace(self.settings, api_key=""))
        self.assert_rules(result, "not_configured")
        self.assertEqual(calls, [])
        self.assertFalse(result["model_request_attempted"])

    def test_rules_mode_does_not_call_model_even_with_key(self):
        result, calls = self.respond(settings=replace(self.settings, mode="rules"))
        self.assert_rules(result, "disabled")
        self.assertEqual(calls, [])

    def test_no_matches_does_not_call_model(self):
        data = {**self.data, "matched_count": 0, "matches": [], "top_skills": []}
        result, calls = self.respond(data=data)
        self.assert_rules(result, "no_matches")
        self.assertEqual(calls, [])

    def test_missing_evidence_does_not_call_model(self):
        data = deepcopy(self.data)
        for row in data["matches"]:
            row["skills"] = ""
            row["job_description"] = ""
        result, calls = self.respond(data=data)
        self.assert_rules(result, "no_evidence")
        self.assertEqual(calls, [])

    def test_unknown_citation_is_rejected(self):
        doc = document(); doc["claims"][0]["citations"][0]["job_id"] = "JOB_9999"
        result, _ = self.respond(completion(doc))
        self.assert_rules(result, "invalid_response")
        self.assertEqual(result["answer"], self.data["answer"])

    def test_paraphrased_quote_is_rejected(self):
        doc = document(); doc["claims"][0]["citations"][0]["quote"] = "负责人工智能大模型训练与部署"
        result, _ = self.respond(completion(doc))
        self.assert_rules(result, "invalid_response")

    def test_quote_from_another_record_is_rejected(self):
        doc = document(); doc["claims"][0]["citations"][0]["quote"] = self.data["matches"][1]["job_description"]
        result, _ = self.respond(completion(doc))
        self.assert_rules(result, "invalid_response")

    def test_skill_field_can_supply_exact_quote(self):
        doc = document(); doc["claims"][0]["citations"][0]["quote"] = "Python、SQL"
        result, _ = self.respond(completion(doc))
        self.assertEqual(result["answer_mode"], "rag")
        self.assertEqual(result["citations"][0]["field"], "skills")

    def test_conclusions_require_citations(self):
        doc = document(); doc["claims"][0]["citations"] = []
        result, _ = self.respond(completion(doc))
        self.assert_rules(result, "invalid_response")

    def test_fake_inline_id_and_external_link_are_rejected(self):
        for text in ["参见JOB_9999的要求", "参见job_9999的要求", "请访问https://example.com确认"]:
            with self.subTest(text=text):
                doc = document(); doc["claims"][0]["text"] = text
                result, _ = self.respond(completion(doc))
                self.assert_rules(result, "invalid_response")

    def test_malformed_provider_payloads_fall_back(self):
        variants = [
            {}, {"choices": []}, {"choices": ["broken"]}, {"choices": None},
            completion({"evidence_insufficient": "false", "claims": []}),
            completion({"evidence_insufficient": False, "claims": "not-an-array"}),
            completion({"evidence_insufficient": False, "claims": []}),
        ]
        for body in variants:
            with self.subTest(body=body):
                result, _ = self.respond(body)
                self.assert_rules(result, "invalid_response")

    def test_empty_or_non_json_content_falls_back(self):
        for content in ["", "  ", "not json", "```json\n{}\n```", None]:
            with self.subTest(content=content):
                body = completion();body["choices"][0]["message"]["content"] = content
                result, _ = self.respond(body)
                self.assert_rules(result, "invalid_response")

    def test_truncated_generation_is_not_presented_as_rag(self):
        body=completion();body["choices"][0]["finish_reason"]="length"
        result, _ = self.respond(body)
        self.assert_rules(result, "invalid_response")

    def test_model_can_mark_evidence_insufficient(self):
        result, _ = self.respond(completion({"evidence_insufficient": True, "claims": []}))
        self.assert_rules(result, "insufficient_evidence")
        self.assertTrue(result["model_request_attempted"])

    def test_http_failures_are_safe_and_explicit(self):
        for code, status in [(401,"authentication_error"),(403,"authentication_error"),(402,"balance_error"),(429,"rate_limited"),(500,"provider_error"),(302,"provider_error")]:
            with self.subTest(code=code):
                result, calls = self.respond({"error": TEST_KEY}, code)
                self.assert_rules(result, status)
                self.assertEqual(len(calls), 1)

    def test_network_exception_text_does_not_leak(self):
        def fail(request):
            raise httpx.ConnectError("private " + TEST_KEY, request=request)
        result, _ = self.respond(handler=fail)
        self.assert_rules(result, "provider_error")

    def test_timeout_is_explicit(self):
        def fail(request):
            raise httpx.ReadTimeout("private " + TEST_KEY, request=request)
        result, _ = self.respond(handler=fail)
        self.assert_rules(result, "timeout")

    def test_total_deadline_cancels_pending_request(self):
        cancelled=[]
        async def slow(request):
            try:
                await asyncio.sleep(2)
            finally:
                cancelled.append(True)
            return httpx.Response(200, json=completion())
        client=httpx.AsyncClient(transport=httpx.MockTransport(slow))
        started=time.monotonic()
        with patch.object(rag.httpx,"AsyncClient",return_value=client):
            result=rag.augment_answer("Python",self.data,replace(self.settings,timeout=.03))
        self.assert_rules(result,"timeout")
        self.assertEqual(cancelled,[True])
        self.assertLess(time.monotonic()-started,1)

    def test_only_sent_evidence_may_be_cited(self):
        doc=document();doc["claims"][0]["citations"]=[{"job_id":"JOB_0002","quote":"Python、Linux"}]
        result,_=self.respond(completion(doc),settings=replace(self.settings,top_k=1))
        self.assert_rules(result,"invalid_response")
        self.assertEqual(result["evidence_count"],1)
        self.assertEqual(len(result["matches"]),2)
        self.assertEqual(result["matched_count"],7)

    def test_quote_beyond_context_limit_is_rejected(self):
        data=deepcopy(self.data);data["matches"][0]["job_description"]="开"*1300+"未发送给模型的尾部原文"
        doc=document();doc["claims"][0]["citations"][0]["quote"]="未发送给模型的尾部原文"
        result,_=self.respond(completion(doc),data=data)
        self.assert_rules(result,"invalid_response")

    def test_original_retrieval_is_not_modified(self):
        before=deepcopy(self.data)
        self.respond()
        self.assertEqual(self.data,before)

    def test_bad_usage_fields_are_not_reported(self):
        body=completion();body["usage"]={"prompt_tokens":True,"completion_tokens":-1,"total_tokens":"150"}
        result,_=self.respond(body)
        self.assertEqual(result["llm_usage"],{})

    def test_busy_model_falls_back_without_request(self):
        self.assertIsNone(rag._budget.acquire());self.assertIsNone(rag._budget.acquire())
        result,calls=self.respond()
        self.assert_rules(result,"busy")
        self.assertEqual(calls,[])

    def test_minute_budget_expires(self):
        with patch.object(rag.time,"monotonic",return_value=100):
            for _ in range(20):
                self.assertIsNone(rag._budget.acquire());rag._budget.release()
            result,calls=self.respond()
            self.assert_rules(result,"rate_limited");self.assertEqual(calls,[])
        with patch.object(rag.time,"monotonic",return_value=161):
            self.assertIsNone(rag._budget.acquire());rag._budget.release()

    def test_config_error_does_not_leak_settings(self):
        with patch.object(rag,"read_settings",side_effect=rag.ConfigurationError(TEST_KEY)):
            result=rag.augment_answer("Python",self.data)
        self.assert_rules(result,"config_error")


class SettingsTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.path=Path(temporary.name)/".env"

    def read(self,values=None):
        return rag.read_settings(environ={} if values is None else values,env_file=self.path)

    def test_defaults_do_not_contain_a_secret(self):
        settings=self.read()
        self.assertEqual(settings.api_key,"")
        self.assertEqual(settings.model,"deepseek-flash")

    def test_utf8_bom_and_environment_override(self):
        self.path.write_text("DEEPSEEK_API_KEY="+TEST_KEY+"\nLLM_MODEL=local-model\n",encoding="utf-8-sig")
        settings=self.read({"LLM_MODEL":"environment-model"})
        self.assertEqual(settings.api_key,TEST_KEY)
        self.assertEqual(settings.model,"environment-model")
        self.assertNotIn(TEST_KEY,repr(settings))

    def test_invalid_configuration_is_rejected(self):
        variants=[{"CAREERLENS_ANSWER_MODE":"unknown"},{"LLM_BASE_URL":"http://example.com"},{"LLM_BASE_URL":"https://user:password@example.com"},{"LLM_TIMEOUT_SECONDS":"nan"},{"LLM_TIMEOUT_SECONDS":"1000"},{"RAG_TOP_K":"6"},{"RAG_TOP_K":"2.5"},{"LLM_MODEL":"model\nkey"}]
        for values in variants:
            with self.subTest(values=values),self.assertRaises(rag.ConfigurationError):self.read(values)

    def test_configuration_tool_preserves_other_settings(self):
        self.path.write_text("DATABASE_URL=local\nDEEPSEEK_API_KEY=old\nDEEPSEEK_API_KEY=duplicate\n",encoding="utf-8")
        save_configuration(self.path,TEST_KEY)
        content=self.path.read_text()
        self.assertIn("DATABASE_URL=local",content)
        self.assertEqual(content.count("DEEPSEEK_API_KEY="),1)
        self.assertEqual(self.read().api_key,TEST_KEY)
        self.assertEqual(self.read().mode,"auto")

    def test_invalid_key_cannot_overwrite_existing_configuration(self):
        self.path.write_text("DATABASE_URL=keep\n",encoding="utf-8")
        with self.assertRaises(ValueError):save_configuration(self.path,"wrong\nkey")
        self.assertEqual(self.path.read_text(),"DATABASE_URL=keep\n")


class RagRouteTests(unittest.TestCase):
    def test_beijing_python_analytics_only_sends_matching_records_to_model(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        sent = []

        def model(request):
            context = json.loads(json.loads(request.content)['messages'][1]['content'])
            sent.append(context['evidence'])
            first = context['evidence'][0]
            return httpx.Response(200, json=completion({
                'evidence_insufficient': False,
                'claims': [{'text': '本次样本的数据分析岗位涉及 Python 和业务指标处理。',
                            'citations': [{'job_id': first['job_id'], 'quote': 'Python'}]}],
            }))

        model_client = httpx.AsyncClient(transport=httpx.MockTransport(model))
        with patch.object(rag, 'read_settings', return_value=rag.Settings(api_key=TEST_KEY)), \
             patch.object(rag, '_budget', rag.CallBudget()), \
             patch.object(rag.httpx, 'AsyncClient', return_value=model_client):
            with TestClient(app) as client:
                response = client.post('/api/ask', json={
                    'question': '北京 Python 数据分析岗位需要哪些技能？',
                })
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['answer_mode'], 'rag')
        self.assertEqual(result['matched_count'], 3)
        self.assertFalse(result['fallback'])
        self.assertEqual(len(sent), 1)
        self.assertEqual({m['job_id'] for m in sent[0]}, {'JOB_0582', 'JOB_1351', 'JOB_1962'})
        for record in sent[0]:
            self.assertEqual(record['city'], '北京')
            self.assertEqual(record['job_category'], '数据分析')
            self.assertIn('Python', record['skills'])
        self.assertTrue(result['reference_integrity_checked'])

    def test_api_route_runs_retrieval_then_model_and_returns_its_evidence(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        requests=[]
        def model(request):
            payload=json.loads(request.content)
            context=json.loads(payload["messages"][1]["content"])
            requests.append(context)
            first=context["evidence"][0]
            quote=first["job_description"].splitlines()[0]
            return httpx.Response(200,json=completion({"evidence_insufficient":False,"claims":[{"text":"该样本岗位涉及后端相关业务模块的开发与维护。","citations":[{"job_id":first["job_id"],"quote":quote}]}]}))
        transport=httpx.MockTransport(model)
        model_client=httpx.AsyncClient(transport=transport)
        with patch.object(rag,"read_settings",return_value=rag.Settings(api_key=TEST_KEY)),patch.object(rag,"_budget",rag.CallBudget()),patch.object(rag.httpx,"AsyncClient",return_value=model_client):
            with TestClient(app) as client:
                response=client.post("/api/ask",json={"question":"深圳 Java 后端开发岗位需要哪些技能？"})
        self.assertEqual(response.status_code,200)
        result=response.json()
        self.assertEqual(result["answer_mode"],"rag")
        self.assertEqual(result["matched_count"],7)
        self.assertEqual(len(result["matches"]),5)
        self.assertEqual(len(requests),1)
        cited=result["citations"][0]
        row=next(row for row in result["matches"] if row["job_id"]==cited["job_id"])
        self.assertIn(cited["quote"],row["job_description"])
        self.assertNotIn(TEST_KEY,response.text)


if __name__=="__main__":unittest.main()
