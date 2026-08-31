import unittest
from unittest.mock import patch

from financeiro import consultor, consultor_settings as settings
from financeiro.secure_config import SecureConfigError


class ConsultorSettingsModuleTest(unittest.TestCase):
    def test_public_operations_are_reexported(self):
        for name in ("get_consultor_settings", "save_consultor_settings",
                     "sync_consultor_with_ai_settings", "get_complementary_profile",
                     "save_complementary_profile", "delete_complementary_profile"):
            self.assertIs(getattr(consultor, name), getattr(settings, name))
        self.assertIs(consultor.ConsultorError, settings.ConsultorError)

    def test_disabled_or_missing_ai_purges_only_requested_user(self):
        for configured, enabled in ((False, False), (False, True), (True, False), (True, True)):
            with self.subTest(configured=configured, enabled=enabled):
                with patch.object(settings, "ai_settings_status", return_value={
                    "configured": configured, "enabled": enabled,
                }), patch.object(settings.history_store, "delete_history") as purge:
                    settings.sync_consultor_with_ai_settings(17)
                if configured and enabled:
                    purge.assert_not_called()
                else:
                    purge.assert_called_once_with(17)

    def test_invalid_encrypted_profile_keeps_public_friendly_error(self):
        with patch.object(settings, "get_connection") as connect:
            connection = connect.return_value.__enter__.return_value
            connection.execute.return_value.fetchone.return_value = {"payload_enc": "invalid"}
            with patch.object(settings, "decrypt_json_from_storage", side_effect=SecureConfigError("internal detail")):
                with self.assertRaisesRegex(consultor.ConsultorError, "^Perfil Complementar criptografado invalido.$"):
                    settings.get_complementary_profile(17)
            self.assertEqual(connection.execute.call_args.args[1], (17,))


if __name__ == "__main__":
    unittest.main()
