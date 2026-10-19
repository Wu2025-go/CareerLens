
import json
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# CareerLens 后端地址
BASE_URL = "http://127.0.0.1:8000"


def request_api(method, path, data=None):
    """向 CareerLens 后端发送测试请求"""

    url = BASE_URL + path

    body = (
        json.dumps(data, ensure_ascii=False).encode("utf-8")
        if data is not None
        else None
    )

    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method=method,
    )

    try:
        with urlopen(request, timeout=45) as response:
            status = response.status
            result = json.loads(
                response.read().decode("utf-8")
            )

        return status, result

    except HTTPError as error:
        detail = error.read().decode(
            "utf-8", errors="replace"
        )
        raise AssertionError(
            f"{path} 请求失败：HTTP {error.code}\n{detail[:500]}"
        ) from error

    except URLError as error:
        raise AssertionError(
            "无法连接后端，请先启动 8000 端口的 FastAPI 服务。"
        ) from error


class TestCareerLensAPI(unittest.TestCase):
    """CareerLens 后端接口自动化测试"""

    def test_01_root(self):
        """测试后端是否正常运行"""

        status, result = request_api("GET", "/")

        self.assertEqual(status, 200)
        self.assertIsInstance(result, dict)

    def test_02_overview(self):
        """测试首页岗位统计接口"""

        status, result = request_api(
            "GET", "/api/overview"
        )

        self.assertEqual(status, 200)

        self.assertIn("job_count", result)
        self.assertIn("avg_salary", result)
        self.assertIn("hot_industry", result)

        self.assertGreater(result["job_count"], 0)
        self.assertGreaterEqual(result["avg_salary"], 0)

        self.assertTrue(result["hot_industry"])

    def test_03_dashboard(self):
        """测试数据看板接口"""

        status, result = request_api(
            "GET", "/api/dashboard"
        )

        self.assertEqual(status, 200)
        self.assertIsInstance(result, dict)
        self.assertTrue(result)

    def test_04_ai_ask(self):
        """测试 AI 就业问答接口"""

        payload = {
            "question": "深圳 Java 后端开发岗位需要哪些技能？"
        }

        status, result = request_api(
            "POST",
            "/api/ask",
            payload,
        )

        self.assertEqual(status, 200)
        self.assertIsInstance(result, dict)
        self.assertTrue(result)

    def test_05_skill_match(self):
        """测试技能测评接口"""

        payload = {
            "skills": [
                "Java",
                "SQL",
                "Linux",
                "Git",
            ],
            "city": "深圳",
        }

        status, result = request_api(
            "POST",
            "/api/skill-match",
            payload,
        )

        self.assertEqual(status, 200)

        self.assertIn("overall_score", result)
        self.assertIn("level", result)

        score = result["overall_score"]

        self.assertIsInstance(score, (int, float))
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_06_recommend(self):
        """测试智能岗位推荐接口"""

        payload = {
            "city": "深圳",
            "keyword": "Java",
            "skills": [
                "Java",
                "SQL",
                "Linux",
            ],
            "min_salary": 10,
            "education": "本科",
        }

        status, result = request_api(
            "POST",
            "/api/recommend",
            payload,
        )

        self.assertEqual(status, 200)

        self.assertIn("total", result)
        self.assertIn("recommendations", result)

        self.assertIsInstance(
            result["recommendations"], list
        )

        self.assertGreaterEqual(result["total"], 0)


if __name__ == "__main__":
    unittest.main()
