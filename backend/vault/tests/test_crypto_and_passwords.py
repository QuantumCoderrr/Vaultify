import string

from django.test import SimpleTestCase, override_settings

from vault import crypto
from vault.passwords import estimate_strength, generate_passphrase, generate_password


class CryptoTests(SimpleTestCase):
    def test_round_trip(self):
        token = crypto.encrypt("hunter2")
        self.assertNotIn("hunter2", token)
        self.assertEqual(crypto.decrypt(token), "hunter2")

    def test_empty_values(self):
        self.assertEqual(crypto.encrypt(""), "")
        self.assertEqual(crypto.decrypt(""), "")

    def test_key_rotation(self):
        old_key, new_key = crypto.generate_key(), crypto.generate_key()
        with override_settings(VAULT_ENCRYPTION_KEYS=[old_key]):
            token = crypto.encrypt("rotate me")
        with override_settings(VAULT_ENCRYPTION_KEYS=[new_key, old_key]):
            self.assertEqual(crypto.decrypt(token), "rotate me")
            rotated = crypto.rotate(token)
        with override_settings(VAULT_ENCRYPTION_KEYS=[new_key]):
            self.assertEqual(crypto.decrypt(rotated), "rotate me")
            with self.assertRaises(crypto.DecryptionError):
                crypto.decrypt(token)


class PasswordTests(SimpleTestCase):
    def test_generate_password_respects_length_and_classes(self):
        for _ in range(20):
            pw = generate_password(24)
            self.assertEqual(len(pw), 24)
            self.assertTrue(any(c in string.ascii_lowercase for c in pw))
            self.assertTrue(any(c in string.ascii_uppercase for c in pw))
            self.assertTrue(any(c in string.digits for c in pw))

    def test_generate_password_digits_only(self):
        pw = generate_password(12, lowercase=False, uppercase=False, symbols=False)
        self.assertTrue(pw.isdigit())

    def test_exclude_ambiguous(self):
        for _ in range(20):
            self.assertFalse(set("Il1O0o") & set(generate_password(64, exclude_ambiguous=True)))

    def test_passphrase(self):
        phrase = generate_passphrase(words=4, separator=".", add_number=False)
        self.assertEqual(len(phrase.split(".")), 4)

    def test_strength(self):
        self.assertLessEqual(estimate_strength("password").score, 1)
        self.assertEqual(estimate_strength(generate_password(24)).score, 4)
        self.assertEqual(estimate_strength("").score, 0)
