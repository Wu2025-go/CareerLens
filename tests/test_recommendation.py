"""CareerLens 推荐规则回归测试。

将本文件放入项目的 tests 文件夹，在项目根目录运行：
    python -m unittest discover -s tests -p "test_recommendation.py" -v

测试使用固定的模拟岗位，并临时替换数据读取函数；不修改项目 CSV，
也不需要启动后端服务。FastAPI、Pandas 等仍使用项目现有依赖。
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd
from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import main as backend_main


def make_job(job_id="java-sz", **changes):
    """构造独立测试数据，企业及岗位编号均为测试用途。"""
    row = {
        "job_id": job_id,
        "job_title": "Java后端开发工程师",
        "company_name": "测试企业",
        "city": "深圳",
        "salary_min": 10000,
        "salary_max": 15000,
        "education": "本科",
        "experience": "不限",
        "job_description": "负责企业业务系统开发与维护",
        "skills": "Java|SQL|Linux",
        "publish_date": "2026-10-01",
        "job_category": "后端开发",
    }
    row.update(changes)
    return row


class TestRecommendationRules(unittest.TestCase):
    def recommend(self, rows=None, **conditions):
        """只替换本次调用的数据源，测试结束后自动恢复。"""
        frame = pd.DataFrame([make_job()] if rows is None else rows)
        request = backend_main.JobRecommendRequest(**conditions)
        with patch.object(backend_main, "load_jobs", return_value=frame):
            return backend_main.recommend_jobs(request)

    @staticmethod
    def job_ids(result):
        return [job["job_id"] for job in result["recommendations"]]

    def test_01_java_does_not_match_javascript(self):
        """搜索 Java 时，不混入仅要求 JavaScript 的前端岗位。"""
        rows = [
            make_job(),
            make_job(
                "js", job_title="JavaScript前端工程师",
                skills="JavaScript|Vue", job_category="前端开发",
            ),
        ]
        self.assertEqual(self.job_ids(self.recommend(rows, keyword="Java")), ["java-sz"])

    def test_02_go_does_not_match_django(self):
        """搜索 Go 时，不因 Django、MongoDB 中含有 go 而误匹配。"""
        rows = [
            make_job("django", job_title="Django开发", skills="Python|Django|MongoDB"),
            make_job("go", job_title="Go开发工程师", skills="Go|SQL"),
        ]
        self.assertEqual(self.job_ids(self.recommend(rows, keyword="Go")), ["go"])

    def test_03_c_cpp_csharp_are_distinct(self):
        """C、C++、C# 不应仅凭前缀相同被当作同一个方向。"""
        rows = [
            make_job("c", job_title="C开发", skills="C"),
            make_job("cpp", job_title="C++开发", skills="C++"),
            make_job("csharp", job_title="C#开发", skills="C#"),
        ]
        for keyword, expected in [("C", "c"), ("C++", "cpp"), ("C#", "csharp")]:
            with self.subTest(keyword=keyword):
                self.assertEqual(self.job_ids(self.recommend(rows, keyword=keyword)), [expected])

    def test_04_multiple_keywords_must_all_match(self):
        """输入 Java 后端时，岗位需要同时符合两个方向词。"""
        rows = [
            make_job(),
            make_job("frontend", job_title="Java前端工程师", skills="Java|Vue", job_category="前端开发"),
        ]
        for keyword in ["Java 后端", "Java后端"]:
            with self.subTest(keyword=keyword):
                self.assertEqual(self.job_ids(self.recommend(rows, keyword=keyword)), ["java-sz"])

    def test_05_all_conditions_can_reach_100(self):
        """方向、全部岗位技能、薪资和学历都满足时，可以达到100分。"""
        result = self.recommend(
            city="深圳", keyword="Java", skills=["Java", "SQL", "Linux"],
            min_salary=10, education="本科",
        )
        self.assertEqual(result["recommendations"][0]["match_score"], 100)

    def test_06_more_skill_coverage_ranks_higher(self):
        """其他条件相同时，覆盖岗位全部技能的结果应排在部分覆盖之前。"""
        rows = [
            make_job("partial", skills="Java|SQL|Linux"),
            make_job("complete", skills="Java|SQL"),
        ]
        result = self.recommend(rows, keyword="Java", skills=["Java", "SQL"])
        self.assertEqual(self.job_ids(result), ["complete", "partial"])
        self.assertGreater(
            result["recommendations"][0]["match_score"],
            result["recommendations"][1]["match_score"],
        )

    def test_07_zero_skill_overlap_is_excluded(self):
        """用户技能完全不重合时，不以城市、薪资等条件制造高匹配结果。"""
        result = self.recommend(
            keyword="Java", skills=["Photoshop"], min_salary=10, education="本科",
        )
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["recommendations"], [])

    def test_08_skill_aliases_and_duplicates(self):
        """常用技能别名与大小写应统一，重复输入不应重复计分。"""
        result = self.recommend(
            [make_job(skills="SpringBoot|Spring Boot|Vue.js|Vue|SQL|sql")],
            skills=["Spring Boot", "springboot", "Vue3", "SQL", "sql"],
        )
        item = result["recommendations"][0]
        self.assertEqual(len(item["skills"]), 3)
        self.assertEqual(len(item["matched_skills"]), 3)
        self.assertEqual(item["match_score"], 100)

    def test_09_salary_checks_lower_bound(self):
        """期望10K时，8K—20K不应被认定为薪资下限达标。"""
        rows = [
            make_job("low", salary_min=8000, salary_max=20000),
            make_job("eligible", salary_min=10000, salary_max=15000),
        ]
        self.assertEqual(self.job_ids(self.recommend(rows, min_salary=10)), ["eligible"])

    def test_10_missing_salary_cannot_prove_minimum(self):
        """薪资下限缺失、无穷大或无效时，不能确认满足最低薪资条件。"""
        for lower in [None, float("nan"), float("inf"), -1000]:
            with self.subTest(lower=lower):
                result = self.recommend([make_job(salary_min=lower)], min_salary=10)
                self.assertEqual(result["total"], 0)

    def test_11_yuan_and_k_units_are_consistent(self):
        """沿用项目数据约定，10000元与10K得到一致的薪资展示。"""
        rows = [make_job("yuan"), make_job("k", salary_min=10, salary_max=15)]
        result = self.recommend(rows, min_salary=10)
        self.assertEqual(result["total"], 2)
        for item in result["recommendations"]:
            self.assertEqual(item["salary_min"], 10)
            self.assertEqual(item["salary_max"], 15)

    def test_12_reversed_salary_range_is_not_accepted(self):
        """薪资下限大于上限的数据不能用于确认薪资达标。"""
        result = self.recommend([make_job(salary_min=20000, salary_max=10000)], min_salary=10)
        self.assertEqual(result["total"], 0)

    def test_13_candidate_education_is_compared_by_level(self):
        """本科生可满足大专、本科或不限要求，不能满足硕士、博士要求。"""
        rows = [
            make_job("associate", education="大专"),
            make_job("bachelor", education="本科及以上"),
            make_job("master", education="硕士及以上"),
            make_job("phd", education="博士研究生"),
            make_job("open", education="学历不限"),
        ]
        result = self.recommend(rows, education="本科")
        self.assertEqual(set(self.job_ids(result)), {"associate", "bachelor", "open"})
        result = self.recommend(rows, education="硕士")
        self.assertNotIn("phd", self.job_ids(result))

    def test_14_city_only_still_returns_jobs(self):
        """只选择城市时，也应返回该城市可浏览的岗位。"""
        rows = [make_job(), make_job("gz", city="广州")]
        result = self.recommend(rows, city="深圳")
        self.assertEqual(self.job_ids(result), ["java-sz"])
        self.assertFalse(result["fallback"])

    def test_15_city_suffix_does_not_force_fallback(self):
        """深圳市与深圳应识别为同一个城市。"""
        result = self.recommend(city="深圳市")
        self.assertEqual(result["total"], 1)
        self.assertFalse(result["fallback"])

    def test_16_fallback_preserves_other_conditions(self):
        """扩展城市后，仍需满足方向、技能交集、最低薪资和学历条件。"""
        rows = [
            make_job("local-wrong", skills="Photoshop"),
            make_job("other-good", city="广州"),
            make_job("other-low", city="上海", salary_min=5000, salary_max=20000),
            make_job("other-degree", city="北京", education="博士"),
            make_job("other-skill", city="杭州", skills="Photoshop"),
        ]
        result = self.recommend(
            rows, city="深圳", keyword="Java", skills=["Java"],
            min_salary=10, education="本科",
        )
        self.assertTrue(result["fallback"])
        self.assertEqual(self.job_ids(result), ["other-good"])
        self.assertEqual(result["conditions"]["city"], "深圳")

    def test_17_valid_local_jobs_are_preferred(self):
        """本地已有符合条件的结果时，不自动扩展到其他城市。"""
        rows = [make_job("local", skills="Java|SQL|Linux"), make_job("other", city="广州", skills="Java")]
        result = self.recommend(rows, city="深圳", skills=["Java"])
        self.assertEqual(self.job_ids(result), ["local"])
        self.assertFalse(result["fallback"])

    def test_18_no_matches_returns_empty_list(self):
        """没有匹配结果时，返回明确的空列表和提示信息。"""
        result = self.recommend(keyword="不存在的岗位方向")
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["recommendations"], [])
        self.assertTrue(result["message"])

    def test_19_top_ten_and_full_total(self):
        """展示最多10条，但total保留全部匹配岗位数量。"""
        result = self.recommend([make_job(str(i)) for i in range(15)], keyword="Java")
        self.assertEqual(result["total"], 15)
        self.assertEqual(len(result["recommendations"]), 10)

    def test_20_empty_dataset_is_handled(self):
        """空数据集也应返回合法的空结果。"""
        result = self.recommend([])
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["recommendations"], [])

    def test_21_default_browsing_has_bounded_score(self):
        """未填写条件时仍可浏览，展示分数保持在0至100范围内。"""
        result = self.recommend()
        self.assertEqual(result["total"], 1)
        score = result["recommendations"][0]["match_score"]
        self.assertIsInstance(score, int)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_22_missing_skills_not_claimed_as_match(self):
        """岗位未给出技能时，不能确认与用户已选技能有交集。"""
        result = self.recommend([make_job(skills=None)], skills=["Java"])
        self.assertEqual(result["total"], 0)

    def test_23_invalid_min_salary_is_rejected(self):
        """请求模型拒绝负数与非有限薪资。"""
        for value in [-1, "nan", "inf"]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    backend_main.JobRecommendRequest(min_salary=value)

    def test_24_title_match_ranks_above_description_only(self):
        """技能等其他条件相同时，岗位名称命中优先于仅描述提及。"""
        rows = [
            make_job(
                "description-only", job_title="应用开发工程师", skills="SQL|Linux",
                job_description="项目涉及Java服务维护",
            ),
            make_job("title"),
        ]
        result = self.recommend(rows, keyword="Java")
        self.assertEqual(self.job_ids(result), ["title", "description-only"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
