import unittest

from app import CANONICAL_PATHS, app


class CachePolicyTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def assert_cache_control(self, path, expected):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        self.assertEqual(response.headers.get("Cache-Control"), expected, path)
        return response

    def test_html_pages_require_revalidation(self):
        for path in CANONICAL_PATHS:
            with self.subTest(path=path):
                response = self.assert_cache_control(path, "no-cache")
                response.close()

    def test_css_and_javascript_are_cached_for_one_hour(self):
        for path in ("/static/css/styles.css", "/static/js/main.js"):
            with self.subTest(path=path):
                response = self.assert_cache_control(path, "public, max-age=3600")
                self.assertIsNotNone(response.headers.get("ETag"))
                self.assertIsNotNone(response.headers.get("Last-Modified"))
                response.close()

    def test_images_are_cached_for_one_day(self):
        paths = (
            "/static/Images/gnojo/gnojo-curator-dashboard-400.webp",
            "/static/Images/cyberslooth/homepage-research-interface.png",
            "/static/Images/gnojo/gnojo-curator-dashboard.jpeg",
            "/static/Images/profile/headshot-github.jpg",
        )
        for path in paths:
            with self.subTest(path=path):
                response = self.assert_cache_control(path, "public, max-age=86400")
                self.assertIsNotNone(response.headers.get("ETag"))
                self.assertIsNotNone(response.headers.get("Last-Modified"))
                response.close()

    def test_resume_pdf_is_cached_for_one_hour_and_supports_ranges(self):
        path = "/static/resume/Greg_Dougall_Resume.pdf"
        response = self.assert_cache_control(path, "public, max-age=3600")
        self.assertEqual(response.content_type, "application/pdf")
        self.assertEqual(response.headers.get("Accept-Ranges"), "bytes")
        response.close()

        range_response = self.client.get(path, headers={"Range": "bytes=0-99"})
        self.assertEqual(range_response.status_code, 206)
        self.assertEqual(range_response.headers.get("Cache-Control"), "public, max-age=3600")
        self.assertTrue(range_response.headers.get("Content-Range", "").startswith("bytes 0-99/"))
        self.assertEqual(len(range_response.data), 100)
        range_response.close()

    def test_robots_and_sitemap_require_revalidation(self):
        for path in ("/robots.txt", "/sitemap.xml"):
            with self.subTest(path=path):
                response = self.assert_cache_control(path, "no-cache")
                response.close()

    def test_static_conditional_requests_retain_validators(self):
        path = "/static/css/styles.css"
        initial = self.client.get(path)
        etag = initial.headers["ETag"]
        initial.close()

        conditional = self.client.get(path, headers={"If-None-Match": etag})
        self.assertEqual(conditional.status_code, 304)
        self.assertEqual(conditional.headers.get("Cache-Control"), "public, max-age=3600")
        self.assertEqual(conditional.headers.get("ETag"), etag)
        conditional.close()

    def test_api_and_error_responses_do_not_receive_public_caching(self):
        corral = self.client.post("/api/ai-corral", data="prompt=hello")
        self.assertEqual(corral.status_code, 415)
        self.assertEqual(corral.headers.get("Cache-Control"), "no-store")
        corral.close()

        contact = self.client.post("/api/contact", data="name=Greg")
        self.assertEqual(contact.status_code, 415)
        self.assertNotIn("public", contact.headers.get("Cache-Control", ""))
        contact.close()

        missing = self.client.get("/missing-page")
        self.assertEqual(missing.status_code, 404)
        self.assertNotIn("public", missing.headers.get("Cache-Control", ""))
        missing.close()


if __name__ == "__main__":
    unittest.main()
