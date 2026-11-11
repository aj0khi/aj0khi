import unittest

from scripts.galaxy import build_svg, color_for, repository_languages


class GalaxyTests(unittest.TestCase):
    def setUp(self):
        self.repos = [
            {
                "name": "aircade",
                "html_url": "https://github.com/aj0khi/aircade-mru-hacks",
                "language": "JavaScript",
                "languages": {"JavaScript": 900, "Swift": 100},
                "stargazers_count": 2,
            },
            {
                "name": "teach-to-game",
                "html_url": "https://github.com/aj0khi/teach-to-game",
                "language": "Python",
                "languages": {"Python": 1000},
                "stargazers_count": 0,
            },
        ]

    def test_builds_linked_animated_galaxy(self):
        svg = build_svg(self.repos, updated="2026-11-11", seed="test")
        self.assertIn("MY GITHUB UNIVERSE", svg)
        self.assertIn('href="https://github.com/aj0khi/aircade-mru-hacks"', svg)
        self.assertIn('href="https://github.com/aj0khi/teach-to-game"', svg)
        self.assertIn("<animateMotion", svg)
        self.assertIn("JavaScript", svg)
        self.assertIn("Python", svg)
        self.assertIn("updated 2026-11-11", svg)

    def test_language_arms_are_ranked_by_repository_language_share(self):
        arms = repository_languages(self.repos)
        self.assertEqual(arms[0][0], "Python")
        self.assertAlmostEqual(sum(share for _, _, share in arms), 1.0)

    def test_unknown_language_has_stable_color(self):
        self.assertEqual(color_for("ExampleLang"), color_for("ExampleLang"))
        self.assertNotEqual(color_for("ExampleLang"), color_for("AnotherLang"))

    def test_empty_repository_list_has_fallback_arm(self):
        self.assertEqual(repository_languages([]), [("Projects", "#85a7ff", 1.0)])
        self.assertIn("0 public repos", build_svg([], updated="today", seed="test"))


if __name__ == "__main__":
    unittest.main()
