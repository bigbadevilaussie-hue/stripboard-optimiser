"""Regression for the current repository's tracked static integrity contract."""
import unittest

from scripts.audit_repo_integrity import check_repository


class RepoIntegrityTests(unittest.TestCase):
    def test_repo_tree_manifest_imports_and_versions(self):
        audit = check_repository()
        self.assertEqual(audit["status"], "PASS", audit.get("errors"))
        self.assertEqual(audit["errors"], [])
        self.assertGreaterEqual(audit["stats"]["fixture_files"], 12)
        self.assertEqual(audit["stats"]["fixture_files"],
                         audit["stats"]["fixture_hashes_checked"])
        self.assertEqual(audit["stats"]["master_project_jsons_checked"], 5)
        self.assertGreaterEqual(audit["stats"]["typescript_files_checked"], 76)
        self.assertRegex(audit["versions"]["gui"], r"^2\.\d{2}$")
        self.assertNotEqual(audit["versions"]["gui"], audit["versions"]["repository"])
        self.assertEqual(audit["versions"]["repository"], "2.00")


if __name__ == "__main__":
    unittest.main()
