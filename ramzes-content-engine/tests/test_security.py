import unittest
from unittest.mock import patch

import app as app_module
import storage as storage_module


class AccessControlTests(unittest.TestCase):
    def setUp(self):
        self.original_owner = app_module.OWNER_ID
        app_module.OWNER_ID = "123456789"

    def tearDown(self):
        app_module.OWNER_ID = self.original_owner

    def test_unconfigured_owner_fails_closed(self):
        app_module.OWNER_ID = ""
        self.assertFalse(app_module.allowed(123456789))
        self.assertFalse(app_module.allowed(None))

    def test_only_configured_owner_is_allowed(self):
        self.assertTrue(app_module.allowed(123456789))
        self.assertFalse(app_module.allowed(987654321))
        self.assertFalse(app_module.allowed(None))


class WebhookSecurityTests(unittest.TestCase):
    def setUp(self):
        self.original_secret = app_module.WEBHOOK_SECRET
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.WEBHOOK_SECRET = self.original_secret

    def test_webhook_rejects_missing_server_secret(self):
        app_module.WEBHOOK_SECRET = ""
        response = self.client.post("/telegram", json={"update_id": 1})
        self.assertEqual(response.status_code, 503)

    def test_webhook_rejects_wrong_secret(self):
        app_module.WEBHOOK_SECRET = "expected-secret"
        response = self.client.post(
            "/telegram",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        )
        self.assertEqual(response.status_code, 403)

    def test_webhook_accepts_valid_secret_and_queues_update(self):
        app_module.WEBHOOK_SECRET = "expected-secret"
        with patch.object(app_module.pool, "submit") as submit:
            response = self.client.post(
                "/telegram",
                json={"update_id": 1},
                headers={"X-Telegram-Bot-Api-Secret-Token": "expected-secret"},
            )
        self.assertEqual(response.status_code, 200)
        submit.assert_called_once()


class StorageSecurityTests(unittest.TestCase):
    def test_storage_requires_service_role_key(self):
        with patch.multiple(
            storage_module,
            STORAGE_ENABLED=True,
            REST_URL="https://example.supabase.co/rest/v1",
            SUPABASE_SERVICE_KEY="",
        ):
            self.assertFalse(storage_module.enabled())

        with patch.multiple(
            storage_module,
            STORAGE_ENABLED=True,
            REST_URL="https://example.supabase.co/rest/v1",
            SUPABASE_SERVICE_KEY="server-only-key",
        ):
            self.assertTrue(storage_module.enabled())

    def test_storage_headers_use_only_service_role_credential(self):
        with patch.object(storage_module, "SUPABASE_SERVICE_KEY", "server-only-key"):
            headers = storage_module._headers()
        self.assertEqual(headers["apikey"], "server-only-key")
        self.assertEqual(headers["Authorization"], "Bearer server-only-key")
        self.assertNotIn("x-ramzes-engine-key", headers)


if __name__ == "__main__":
    unittest.main()
