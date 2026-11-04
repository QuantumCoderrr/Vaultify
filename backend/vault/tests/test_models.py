from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from vault.models import VaultItem
from vault.security import analyze


def make_item(user, title, secret="", **kwargs):
    item = VaultItem(user=user, title=title, **kwargs)
    item.secret = secret
    item.save()
    return item


class VaultItemModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="x-very-long-pass")

    def test_str(self):
        self.assertEqual(str(make_item(self.user, "Secret")), "Secret")

    def test_secret_is_encrypted_at_rest(self):
        item = make_item(self.user, "Bank", secret="correct horse battery staple")
        item.notes = "PIN 1234"
        item.save()
        raw = VaultItem.objects.values("encrypted_secret", "encrypted_notes").get(pk=item.pk)
        self.assertNotIn("correct horse", raw["encrypted_secret"])
        self.assertNotIn("1234", raw["encrypted_notes"])
        fresh = VaultItem.objects.get(pk=item.pk)
        self.assertEqual(fresh.secret, "correct horse battery staple")
        self.assertEqual(fresh.notes, "PIN 1234")

    def test_strength_and_fingerprint_computed(self):
        item = make_item(self.user, "Weak", secret="abc")
        self.assertEqual(item.strength_score, 0)
        self.assertEqual(len(item.secret_fingerprint), 64)

    def test_secret_changed_at_only_moves_on_change(self):
        item = make_item(self.user, "Site", secret="Same-Secret-123!")
        item.secret_changed_at = timezone.now() - timedelta(days=10)
        item.secret = "Same-Secret-123!"
        self.assertGreaterEqual(item.age_days, 10)
        item.secret = "Different-Secret-456!"
        self.assertEqual(item.age_days, 0)

    def test_tags_and_domain(self):
        item = make_item(self.user, "X", tags="work, dev,", url="https://www.github.com/login")
        self.assertEqual(item.tag_list, ["work", "dev"])
        self.assertEqual(item.domain, "github.com")


class HealthAnalysisTests(TestCase):
    def test_detects_weak_reused_and_stale(self):
        user = get_user_model().objects.create_user("bob", password="x-very-long-pass")
        make_item(user, "A", secret="sunshine2024")
        make_item(user, "B", secret="sunshine2024")
        old = make_item(user, "C", secret="Xk9$mP2!qL7#vN4@wR8&")
        VaultItem.objects.filter(pk=old.pk).update(secret_changed_at=timezone.now() - timedelta(days=400))
        make_item(user, "Note only")  # no secret: ignored

        report = analyze(VaultItem.objects.filter(user=user))
        self.assertEqual(report["total"], 3)
        self.assertEqual({i.title for i in report["reused"]}, {"A", "B"})
        self.assertEqual({i.title for i in report["stale"]}, {"C"})
        self.assertTrue(report["weak"])
        self.assertLess(report["score"], 50)

    def test_empty_vault_scores_100(self):
        self.assertEqual(analyze([])["score"], 100)
