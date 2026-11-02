"""Offline tests for the repository protections (the live check is `repo_guard.py check`).

    python3 -m unittest discover -s tools -p "test_*.py"
"""

import unittest

import repo_guard


class WorkflowTests(unittest.TestCase):
    def test_our_workflows_are_safe(self):
        files = sorted(repo_guard.WORKFLOWS.glob("*.yml"))
        self.assertTrue(files)
        for path in files:
            self.assertEqual(repo_guard.workflow_problems(path.read_text(encoding="utf-8")), [], path.name)

    def test_unsafe_workflows_are_caught(self):
        bad = ("on: [pull_request_target]\njobs:\n  x:\n    runs-on: ubuntu-latest\n"
               "    permissions:\n      contents: write\n    steps:\n      - uses: someone/thing@v1\n")
        problems = " | ".join(repo_guard.workflow_problems(bad))
        for word in ("pull_request_target", "no top-level permissions", "someone/thing@v1", "environment: release"):
            self.assertIn(word, problems)

    def test_allow_list_has_only_third_party_actions(self):
        text = ("      - uses: actions/checkout@v4\n      - uses: github/codeql-action/init@v3\n"
                "      - uses: arduino/setup-arduino-cli@" + "a" * 40 + " # v2\n      - uses: ./local\n")
        self.assertEqual(repo_guard.third_party_patterns([text]), ["arduino/setup-arduino-cli@*"])


class RulesetTests(unittest.TestCase):
    def test_history_rule_has_no_bypass(self):
        history = repo_guard.rulesets()[0]
        self.assertEqual(history["bypass_actors"], [])
        self.assertEqual({r["type"] for r in history["rules"]}, {"deletion", "non_fast_forward"})

    def test_only_admins_bypass_review_and_tags(self):
        for rs in repo_guard.rulesets(15368)[1:]:
            self.assertEqual(rs["bypass_actors"], [{"actor_id": repo_guard.ADMIN_ROLE, "actor_type": "RepositoryRole",
                                                    "bypass_mode": "always"}], rs["name"])
            self.assertEqual(rs["enforcement"], "active")

    def test_review_rule(self):
        review = {r["type"]: r["parameters"] for r in repo_guard.rulesets(15368)[1]["rules"]}
        self.assertEqual(review["pull_request"]["required_approving_review_count"], 1)
        self.assertTrue(review["pull_request"]["require_code_owner_review"])
        self.assertEqual(review["required_status_checks"]["required_status_checks"],
                         [{"context": "build", "integration_id": 15368}])


if __name__ == "__main__":
    unittest.main()
