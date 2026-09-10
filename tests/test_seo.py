import json
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urlsplit

from app import app


CANONICAL_ROUTES = {
    "/": "https://gregdougall.com/",
    "/contact": "https://gregdougall.com/contact",
    "/resume": "https://gregdougall.com/resume",
    "/projects/gnojo": "https://gregdougall.com/projects/gnojo",
    "/projects/ai-operations-assistant": "https://gregdougall.com/projects/ai-operations-assistant",
    "/projects/irongate": "https://gregdougall.com/projects/irongate",
    "/projects/smartfix": "https://gregdougall.com/projects/smartfix",
    "/projects/cyberslooth": "https://gregdougall.com/projects/cyberslooth",
    "/projects/ai-corral": "https://gregdougall.com/projects/ai-corral",
    "/lab-notes/bounded-autonomous-research": "https://gregdougall.com/lab-notes/bounded-autonomous-research",
    "/lab-notes/governed-ai-repair": "https://gregdougall.com/lab-notes/governed-ai-repair",
    "/lab-notes/service-workflow-relationships": "https://gregdougall.com/lab-notes/service-workflow-relationships",
}

ALIASES = {
    "/index.html": "/",
    "/contact.html": "/contact",
    "/resume.html": "/resume",
    "/projects/gnojo.html": "/projects/gnojo",
    "/projects/ai-operations-assistant.html": "/projects/ai-operations-assistant",
    "/projects/irongate.html": "/projects/irongate",
    "/projects/smartfix.html": "/projects/smartfix",
    "/projects/cyberslooth.html": "/projects/cyberslooth",
    "/projects/ai-corral.html": "/projects/ai-corral",
    "/projects/nw-home-fix": "/projects/smartfix",
}

PAGE_TITLES = {
    "/": "Greg Dougall | AI, Cybersecurity & Systems Projects",
    "/contact": "Contact — Greg Dougall",
    "/resume": "Greg Dougall Resume | IT, Cybersecurity & AI",
    "/projects/gnojo": "Gnojo | AI-Assisted Knowledge Integrity",
    "/projects/ai-operations-assistant": "AI Operations Assistant | Flask Risk Reporting",
    "/projects/irongate": "Project IronGate | Cybersecurity Training",
    "/projects/smartfix": "SmartFix | Service Workflow Software",
    "/projects/cyberslooth": "CyberSlooth | Bounded Autonomous AI Research",
    "/projects/ai-corral": "AI Corral | Constrained AI Guardrails",
    "/lab-notes/bounded-autonomous-research": "Bounded Autonomous Research | Greg Dougall Lab Notes",
    "/lab-notes/governed-ai-repair": "Governed AI Repair | Greg Dougall Lab Notes",
    "/lab-notes/service-workflow-relationships": "Service Workflow Database Design | Greg Dougall Lab Notes",
}


class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.descriptions = []
        self.h1_count = 0
        self.title_parts = []
        self.json_ld = []
        self._in_title = False
        self._in_json_ld = False
        self._script_parts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "link" and attributes.get("rel") == "canonical":
            self.canonicals.append(attributes.get("href"))
        elif tag == "meta" and attributes.get("name") == "description":
            self.descriptions.append(attributes.get("content"))
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "script" and attributes.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._script_parts = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._script_parts))
            self._in_json_ld = False

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        if self._in_json_ld:
            self._script_parts.append(data)

    @property
    def title(self):
        return "".join(self.title_parts).strip()


class SeoTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def parse_page(self, route):
        response = self.client.get(route)
        self.assertEqual(response.status_code, 200, route)
        html = response.get_data(as_text=True)
        response.close()
        parser = HeadParser()
        parser.feed(html)
        return parser

    def test_canonical_pages_have_expected_head_metadata(self):
        for route, canonical in CANONICAL_ROUTES.items():
            with self.subTest(route=route):
                parser = self.parse_page(route)
                self.assertEqual(parser.canonicals, [canonical])
                self.assertEqual(parser.title, PAGE_TITLES[route])
                self.assertEqual(len(parser.descriptions), 1)
                self.assertTrue(parser.descriptions[0])
                self.assertEqual(parser.h1_count, 1)

    def test_aliases_are_permanent_one_hop_redirects(self):
        for alias, target in ALIASES.items():
            with self.subTest(alias=alias):
                response = self.client.get(alias)
                self.assertEqual(response.status_code, 308)
                self.assertEqual(urlsplit(response.headers["Location"]).path, target)
                response.close()
                target_response = self.client.get(target)
                self.assertEqual(target_response.status_code, 200)
                target_response.close()

    def test_robots_txt(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith("text/plain"))
        self.assertEqual(
            response.get_data(as_text=True),
            "User-agent: *\nAllow: /\n\nSitemap: https://gregdougall.com/sitemap.xml\n",
        )

    def test_sitemap_contains_only_canonical_routes(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith("application/xml"))
        root = ET.fromstring(response.data)
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [node.text for node in root.findall("sm:url/sm:loc", namespace)]
        self.assertEqual(locations, list(CANONICAL_ROUTES.values()))
        self.assertEqual(len(locations), 12)

    def test_homepage_json_ld_is_valid_and_limited_to_person_and_website(self):
        parser = self.parse_page("/")
        self.assertEqual(len(parser.json_ld), 1)
        data = json.loads(parser.json_ld[0])
        graph = data["@graph"]
        self.assertEqual({item["@type"] for item in graph}, {"Person", "WebSite"})
        person = next(item for item in graph if item["@type"] == "Person")
        website = next(item for item in graph if item["@type"] == "WebSite")
        self.assertEqual(person["name"], "Greg Dougall")
        self.assertEqual(person["url"], "https://gregdougall.com/")
        self.assertEqual(person["homeLocation"]["name"], "Tacoma, Washington, USA")
        self.assertEqual(person["sameAs"], ["https://github.com/grgdougall-crypto"])
        self.assertEqual(website["name"], "Greg Dougall")
        self.assertEqual(website["url"], "https://gregdougall.com/")
        self.assertNotIn("potentialAction", website)


if __name__ == "__main__":
    unittest.main()
