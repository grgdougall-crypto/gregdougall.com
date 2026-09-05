import json
import os
import unittest
from collections import deque
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import openai
import app as portfolio


def structured_result(category="accepted", **overrides):
    value = {
        "answer": "A short, bounded response.",
        "category": category,
        "confidence": "medium",
        "rule_followed": "Answered briefly without tools or external actions.",
    }
    value.update(overrides)
    return json.dumps(value)


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        output = self.outputs.pop(0)
        return SimpleNamespace(status="completed", output_text=output)


class FakeOpenAIClient:
    def __init__(self, outputs):
        self.responses = FakeResponses(outputs)


class AICorralTests(unittest.TestCase):
    def setUp(self):
        portfolio._rate_buckets.clear()
        self.client = portfolio.app.test_client()
        self.environment = patch.dict(os.environ, {"OPENAI_API_KEY": "server-only-test-key"}, clear=False)
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def post_with_outputs(self, outputs, prompt="Explain guardrails."):
        fake = FakeOpenAIClient(outputs)
        with patch.object(portfolio, "create_ai_corral_client", return_value=fake):
            response = self.client.post("/api/ai-corral", json={"prompt": prompt})
        return response, fake

    def test_valid_prompt_returns_accepted_structured_response(self):
        response, fake = self.post_with_outputs([structured_result()])
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["category"], "accepted")
        self.assertFalse(payload["retry_used"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertTrue(all(payload["guardrails"].values()))
        call = fake.responses.calls[0]
        self.assertEqual(call["model"], "gpt-5.6-luna")
        self.assertEqual(call["tools"], [])
        self.assertFalse(call["store"])
        self.assertEqual(call["max_output_tokens"], 500)
        self.assertEqual(call["reasoning"], {"effort": "low"})
        self.assertTrue(call["text"]["format"]["strict"])
        self.assertNotIn("conversation", call)
        self.assertNotIn("previous_response_id", call)

    def test_model_name_is_configurable(self):
        with patch.dict(os.environ, {"AI_CORRAL_MODEL": "configured-model"}, clear=False):
            response, fake = self.post_with_outputs([structured_result()])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(fake.responses.calls[0]["model"], "configured-model")

    def test_redirected_result(self):
        response, _ = self.post_with_outputs([structured_result("redirected")])
        self.assertEqual(response.get_json()["result"]["category"], "redirected")

    def test_refused_result(self):
        response, _ = self.post_with_outputs([structured_result("refused", confidence="high")])
        self.assertEqual(response.get_json()["result"]["category"], "refused")

    def test_empty_prompt_is_rejected(self):
        response = self.client.post("/api/ai-corral", json={"prompt": "   "})
        self.assertEqual(response.status_code, 400)

    def test_exactly_600_characters_is_accepted(self):
        response, fake = self.post_with_outputs([structured_result()], prompt="x" * 600)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(fake.responses.calls), 1)
        self.assertEqual(fake.responses.calls[0]["input"], "x" * 600)

    def test_oversized_prompt_is_rejected_before_any_openai_call(self):
        with patch.object(portfolio, "create_ai_corral_client") as create_client:
            response = self.client.post("/api/ai-corral", json={"prompt": "x" * 601})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {"ok": False, "error": "Prompt must be 600 characters or fewer."},
        )
        create_client.assert_not_called()
        self.assertNotIn("server-only-test-key", response.get_data(as_text=True))
        self.assertNotIn("model", response.get_data(as_text=True).lower())

    def test_prompt_length_uses_trimmed_unicode_code_points(self):
        prompt = "  " + ("😀" * 600) + "  "
        response, fake = self.post_with_outputs([structured_result()], prompt=prompt)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(fake.responses.calls[0]["input"], "😀" * 600)

        with patch.object(portfolio, "create_ai_corral_client") as create_client:
            response = self.client.post("/api/ai-corral", json={"prompt": " " + ("😀" * 601) + " "})
        self.assertEqual(response.status_code, 400)
        create_client.assert_not_called()

    def test_non_string_prompt_is_rejected(self):
        response = self.client.post("/api/ai-corral", json={"prompt": 42})
        self.assertEqual(response.status_code, 400)

    def test_non_json_request_is_rejected(self):
        response = self.client.post("/api/ai-corral", data="prompt=hello")
        self.assertEqual(response.status_code, 415)

    def test_missing_api_key_is_handled_safely(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            response = self.client.post("/api/ai-corral", json={"prompt": "Hello"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("OPENAI_API_KEY", response.get_data(as_text=True))

    def test_malformed_output_gets_only_one_retry(self):
        response, fake = self.post_with_outputs(["not json", "still not json"])
        self.assertEqual(response.status_code, 502)
        self.assertEqual(len(fake.responses.calls), 2)
        self.assertTrue(fake.responses.calls[1]["instructions"].endswith("Return a corrected result."))

    def test_retry_can_succeed(self):
        response, fake = self.post_with_outputs(["not json", structured_result()])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["retry_used"])
        self.assertEqual(len(fake.responses.calls), 2)

    def test_retry_failure_returns_deterministic_safe_error(self):
        response, _ = self.post_with_outputs(["{", "["])
        self.assertEqual(
            response.get_json(),
            {"ok": False, "error": "The model response did not pass the Corral's checks. Please try a different prompt."},
        )

    def test_answer_length_is_enforced(self):
        response, fake = self.post_with_outputs([
            structured_result(answer="x" * 401),
            structured_result(answer="x" * 401),
        ])
        self.assertEqual(response.status_code, 502)
        self.assertEqual(len(fake.responses.calls), 2)

    def test_category_enum_is_enforced(self):
        response, _ = self.post_with_outputs([
            structured_result("unknown"),
            structured_result("unknown"),
        ])
        self.assertEqual(response.status_code, 502)

    def test_confidence_enum_is_enforced(self):
        response, _ = self.post_with_outputs([
            structured_result(confidence="certain"),
            structured_result(confidence="certain"),
        ])
        self.assertEqual(response.status_code, 502)

    def test_rule_length_is_enforced(self):
        response, _ = self.post_with_outputs([
            structured_result(rule_followed="x" * 161),
            structured_result(rule_followed="x" * 161),
        ])
        self.assertEqual(response.status_code, 502)

    def test_unexpected_fields_are_rejected(self):
        invalid = json.loads(structured_result())
        invalid["provider_metadata"] = "not allowed"
        response, _ = self.post_with_outputs([json.dumps(invalid), json.dumps(invalid)])
        self.assertEqual(response.status_code, 502)

    def test_secret_and_malformed_output_do_not_leak(self):
        response, _ = self.post_with_outputs([
            "server-only-test-key raw provider content",
            "server-only-test-key raw provider content",
        ])
        body = response.get_data(as_text=True)
        self.assertNotIn("server-only-test-key", body)
        self.assertNotIn("raw provider content", body)

    def test_provider_timeout_is_safe_and_not_retried(self):
        fake = FakeOpenAIClient([])
        timeout = openai.APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
        with patch.object(portfolio, "create_ai_corral_client", return_value=fake), patch.object(
            portfolio, "request_ai_corral_result", side_effect=timeout,
        ) as request_model:
            response = self.client.post("/api/ai-corral", json={"prompt": "Hello"})
        self.assertEqual(response.status_code, 504)
        self.assertEqual(request_model.call_count, 1)

    def test_provider_rate_limit_is_safe_and_not_retried(self):
        fake = FakeOpenAIClient([])
        provider_response = httpx.Response(
            429,
            request=httpx.Request("POST", "https://api.openai.com/v1/responses"),
        )
        failure = openai.RateLimitError("rate limited", response=provider_response, body=None)
        with patch.object(portfolio, "create_ai_corral_client", return_value=fake), patch.object(
            portfolio, "request_ai_corral_result", side_effect=failure,
        ) as request_model:
            response = self.client.post("/api/ai-corral", json={"prompt": "Hello"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(request_model.call_count, 1)

    def test_invalid_input_does_not_consume_throttle_quota(self):
        for _ in range(portfolio.RATE_LIMIT_ATTEMPTS + 1):
            response = self.client.post("/api/ai-corral", json={"prompt": ""})
            self.assertEqual(response.status_code, 400)
        self.assertNotIn("ai-corral:127.0.0.1", portfolio._rate_buckets)

    def test_in_memory_request_throttle_is_conservative(self):
        fake = FakeOpenAIClient([structured_result()] * portfolio.RATE_LIMIT_ATTEMPTS)
        with patch.object(portfolio, "create_ai_corral_client", return_value=fake):
            for _ in range(portfolio.RATE_LIMIT_ATTEMPTS):
                response = self.client.post("/api/ai-corral", json={"prompt": "Hello"})
                self.assertEqual(response.status_code, 200)
            response = self.client.post("/api/ai-corral", json={"prompt": "Hello"})
        self.assertEqual(response.status_code, 429)

    def test_railway_client_ip_header_keeps_visitors_separate(self):
        first_visitor = {"X-Real-IP": "203.0.113.10"}
        fake = FakeOpenAIClient([structured_result()] * (portfolio.RATE_LIMIT_ATTEMPTS + 1))
        with patch.object(portfolio, "create_ai_corral_client", return_value=fake):
            for _ in range(portfolio.RATE_LIMIT_ATTEMPTS):
                response = self.client.post("/api/ai-corral", json={"prompt": "Hello"}, headers=first_visitor)
                self.assertEqual(response.status_code, 200)
            response = self.client.post(
                "/api/ai-corral",
                json={"prompt": "Hello"},
                headers={"X-Real-IP": "203.0.113.11"},
            )
        self.assertEqual(response.status_code, 200)

    def test_throttle_prunes_stale_identity_buckets(self):
        portfolio._rate_buckets["stale-client"] = deque([1.0])
        now = portfolio.RATE_LIMIT_WINDOW_SECONDS + 2.0
        with patch.object(portfolio.time, "monotonic", return_value=now):
            self.assertFalse(portfolio._rate_limit_exceeded("current-client"))
        self.assertNotIn("stale-client", portfolio._rate_buckets)

    def test_throttle_identity_storage_is_bounded(self):
        for index in range(portfolio.RATE_LIMIT_MAX_BUCKETS):
            portfolio._rate_buckets[f"client-{index}"] = deque([1.0])
        with patch.object(portfolio.time, "monotonic", return_value=2.0):
            self.assertTrue(portfolio._rate_limit_exceeded("one-client-too-many"))
        self.assertEqual(len(portfolio._rate_buckets), portfolio.RATE_LIMIT_MAX_BUCKETS)

    def test_ai_corral_route_and_unrelated_routes_load(self):
        for path in (
            "/projects/ai-corral",
            "/",
            "/contact",
            "/projects/gnojo",
            "/projects/ai-operations-assistant",
            "/projects/irongate",
            "/projects/smartfix",
            "/projects/cyberslooth",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()

    def test_ai_corral_page_declares_trimmed_prompt_limit_for_javascript(self):
        response = self.client.get("/projects/ai-corral")
        body = response.get_data(as_text=True)
        self.assertIn('data-prompt-limit="600"', body)
        self.assertNotIn('maxlength="600"', body)
        response.close()


if __name__ == "__main__":
    unittest.main()
