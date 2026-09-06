import unittest

import app as portfolio


class LabNotesTests(unittest.TestCase):
    def setUp(self):
        self.client = portfolio.app.test_client()

    def test_lab_note_routes_render_expected_content(self):
        expected = {
            "/lab-notes/bounded-autonomous-research": (
                "Running My First Bounded Autonomous Research Job",
                "AR-20260905-7A34AD",
                "/projects/cyberslooth",
            ),
            "/lab-notes/governed-ai-repair": (
                "Governed AI Repair",
                "/static/Images/gnojo/gnojo-governed-review.jpeg",
                "/projects/gnojo",
            ),
            "/lab-notes/service-workflow-relationships": (
                "Designing Relationships Around a Service Workflow",
                "/static/Images/smartfix/09-estimate-to-invoice.jpeg",
                "/projects/smartfix",
            ),
        }
        for path, required_content in expected.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                body = response.get_data(as_text=True)
                for content in required_content:
                    self.assertIn(content, body)
                self.assertIn('href="/#lab-notes"', body)
                response.close()

    def test_homepage_previews_link_to_all_lab_notes(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        for slug in portfolio.LAB_NOTES:
            self.assertIn(f'href="/lab-notes/{slug}"', body)
        self.assertEqual(body.count("Read Lab Note"), 3)
        self.assertNotIn("note-toggle", body)
        response.close()

    def test_unknown_lab_note_returns_404(self):
        response = self.client.get("/lab-notes/not-a-note")
        self.assertEqual(response.status_code, 404)
        response.close()

    def test_lab_note_evidence_images_exist_and_are_served(self):
        for note in portfolio.LAB_NOTES.values():
            evidence = note["evidence"]
            if evidence["type"] != "image":
                continue
            with self.subTest(src=evidence["src"]):
                response = self.client.get(evidence["src"])
                self.assertEqual(response.status_code, 200)
                response.close()


if __name__ == "__main__":
    unittest.main()
