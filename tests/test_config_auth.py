"""Session, role and permission rules in config.Config."""
import unittest

from tests import _support  # noqa: F401  (must be imported first)
import config

C = config.Config


class AuthTestCase(unittest.TestCase):
    """Behaviour with the password requirement switched on."""

    def setUp(self):
        C.REQUIRE_LOGIN = True
        C.USERS = {}
        C.CURRENT_USER = None
        C._sync_current_role()

    def tearDown(self):
        C.REQUIRE_LOGIN = False

    def test_no_users_runs_as_bootstrap_administrator(self):
        self.assertIsNone(C.CURRENT_USER)
        self.assertEqual(C.CURRENT_USER_ROLE, "Administrator")
        self.assertTrue(C.has_permission("manage_users"))

    def test_first_user_must_be_administrator(self):
        self.assertFalse(C.add_user("eunice", "Finance", "pw"))
        self.assertEqual(C.USERS, {})

    def test_first_user_becomes_current_session(self):
        self.assertTrue(C.add_user("admin", "Administrator", "pw"))
        self.assertEqual(C.CURRENT_USER, "admin")
        self.assertEqual(C.CURRENT_USER_ROLE, "Administrator")

    def test_unknown_role_rejected(self):
        C.add_user("admin", "Administrator", "pw")
        self.assertFalse(C.add_user("x", "Superuser", "pw"))

    def test_logged_out_with_users_has_no_permissions(self):
        C.add_user("admin", "Administrator", "pw")
        C.logout()
        self.assertIsNone(C.CURRENT_USER_ROLE)
        for feature in ("dashboard", "finance", "settings", "manage_users"):
            self.assertFalse(C.has_permission(feature), feature)

    def test_role_comes_from_logged_in_user(self):
        C.add_user("admin", "Administrator", "pw")
        C.add_user("eunice", "Finance", "pw")
        C.set_current_user("eunice")
        self.assertEqual(C.CURRENT_USER_ROLE, "Finance")
        self.assertTrue(C.has_permission("finance"))
        self.assertFalse(C.has_permission("students"))
        self.assertFalse(C.has_permission("settings"))

    def test_role_change_applies_to_current_session(self):
        C.add_user("admin", "Administrator", "pw")
        C.add_user("eunice", "Finance", "pw")
        C.set_current_user("eunice")
        C.set_user_role("eunice", "Inventory")
        self.assertEqual(C.CURRENT_USER_ROLE, "Inventory")

    def test_removing_current_user_ends_session(self):
        C.add_user("admin", "Administrator", "pw")
        C.add_user("eunice", "Finance", "pw")
        C.set_current_user("eunice")
        C.remove_user("eunice")
        self.assertIsNone(C.CURRENT_USER)
        self.assertIsNone(C.CURRENT_USER_ROLE)

    def test_last_admin_is_protected(self):
        C.add_user("admin", "Administrator", "pw")
        C.add_user("eunice", "Finance", "pw")
        self.assertTrue(C.would_remove_last_admin("admin"))
        self.assertTrue(C.would_remove_last_admin("admin", new_role="Finance"))
        self.assertFalse(C.would_remove_last_admin("eunice"))
        C.add_user("enock", "Administrator", "pw")
        self.assertFalse(C.would_remove_last_admin("admin"))

    def test_sole_admin_with_no_other_users_may_be_removed(self):
        C.add_user("admin", "Administrator", "pw")
        self.assertFalse(C.would_remove_last_admin("admin"))

    def test_session_is_not_persisted(self):
        C.add_user("admin", "Administrator", "pw")
        C.save_user_settings()
        import json
        with open(C._user_settings_path(), encoding="utf-8") as fh:
            saved = json.load(fh)
        self.assertNotIn("CURRENT_USER", saved)
        self.assertNotIn("CURRENT_USER_ROLE", saved)

    def test_password_hash_roundtrip(self):
        C.add_user("admin", "Administrator", "s3cret")
        self.assertTrue(C.verify_user_credentials("admin", "s3cret"))
        self.assertFalse(C.verify_user_credentials("admin", "wrong"))
        self.assertNotIn("s3cret", C.USERS["admin"]["password"])


class NoLoginTestCase(unittest.TestCase):
    """Default: no password; the program opens with full access even if users exist."""

    def setUp(self):
        C.REQUIRE_LOGIN = False
        C.USERS = {}
        C.CURRENT_USER = None

    def test_users_exist_but_no_login_needed(self):
        C.add_user("admin", "Administrator", "pw")
        C.add_user("eunice", "Finance", "pw")
        C.logout()
        self.assertFalse(C.login_required())
        self.assertEqual(C.CURRENT_USER_ROLE, "Administrator")
        self.assertTrue(C.has_permission("settings"))

    def test_setting_is_saved(self):
        C.REQUIRE_LOGIN = True
        C.save_user_settings()
        import json
        with open(C._user_settings_path(), encoding="utf-8") as fh:
            self.assertTrue(json.load(fh)["REQUIRE_LOGIN"])
        C.REQUIRE_LOGIN = False


class TermNameTestCase(unittest.TestCase):
    def test_normalize_legacy_labels(self):
        for raw in ("2", "term2", "Term2", "T2", "t2", "Term 2", " term 2 "):
            self.assertEqual(C.normalize_term_name(raw), "Term 2", raw)

    def test_normalize_leaves_unknown_and_empty(self):
        self.assertEqual(C.normalize_term_name("Summer"), "Summer")
        self.assertEqual(C.normalize_term_name(""), "")
        self.assertEqual(C.normalize_term_name(None), "")

    def test_aliases_include_canonical_first(self):
        aliases = C.get_term_aliases("3")
        self.assertEqual(aliases[0], "Term 3")
        self.assertIn("3", aliases)


if __name__ == "__main__":
    unittest.main()
