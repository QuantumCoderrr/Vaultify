import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from vault.models import ActivityLog, VaultItem

PASSWORD = "a-very-long-master-pass"


class WebViewTests(TestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.user = User.objects.create_user("alice", password=PASSWORD)
        self.other = User.objects.create_user("mallory", password=PASSWORD)

    def login(self):
        self.client.login(username="alice", password=PASSWORD)

    def test_public_pages(self):
        for name in ("landing", "login", "signup"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_vault_requires_login(self):
        res = self.client.get(reverse("vault:dashboard"))
        self.assertRedirects(res, f"{reverse('login')}?next={reverse('vault:dashboard')}")

    def test_signup_logs_in(self):
        res = self.client.post(reverse("signup"), {
            "username": "newbie", "email": "", "password1": "Sup3r-Secure-Pass!", "password2": "Sup3r-Secure-Pass!",
        })
        self.assertRedirects(res, reverse("vault:dashboard"))

    def test_login_records_activity_and_lockout(self):
        res = self.client.post(reverse("login"), {"username": "alice", "password": PASSWORD})
        self.assertRedirects(res, reverse("vault:dashboard"), fetch_redirect_response=False)
        self.assertTrue(ActivityLog.objects.filter(user=self.user, action="login").exists())
        self.client.post(reverse("logout"))

        with override_settings(LOGIN_MAX_ATTEMPTS=3):
            for _ in range(3):
                self.assertEqual(self.client.post(reverse("login"), {"username": "alice", "password": "nope"}).status_code, 200)
            # Even the right password is refused while locked out.
            res = self.client.post(reverse("login"), {"username": "alice", "password": PASSWORD})
            self.assertEqual(res.status_code, 429)
            self.assertContains(res, "Too many failed attempts", status_code=429)
        self.assertEqual(ActivityLog.objects.filter(user=self.user, action="login_failed").count(), 3)

    def test_full_item_lifecycle(self):
        self.login()
        res = self.client.post(reverse("vault:item_create"), {
            "title": "GitHub", "category": "login", "username": "alice", "url": "https://github.com",
            "tags": "Work, dev, work", "secret": "Hunter2-Is-Not-Enough!", "notes": "backup codes",
        })
        item = VaultItem.objects.get(user=self.user)
        self.assertRedirects(res, item.get_absolute_url())
        self.assertEqual(item.tags, "work, dev")
        self.assertEqual(item.secret, "Hunter2-Is-Not-Enough!")

        detail = self.client.get(item.get_absolute_url())
        self.assertContains(detail, "GitHub")
        self.assertNotContains(detail, "Hunter2-Is-Not-Enough!")  # never rendered in HTML

        self.assertContains(self.client.get(reverse("vault:dashboard") + "?q=git"), "GitHub")

        reveal = self.client.post(reverse("vault:item_reveal", args=[item.pk]))
        self.assertEqual(json.loads(reveal.content)["secret"], "Hunter2-Is-Not-Enough!")

        self.client.post(reverse("vault:item_update", args=[item.pk]), {
            "title": "GitHub Enterprise", "category": "login", "secret": "Hunter2-Is-Not-Enough!",
        })
        item.refresh_from_db()
        self.assertEqual(item.title, "GitHub Enterprise")

        self.client.post(reverse("vault:item_favorite", args=[item.pk]))
        item.refresh_from_db()
        self.assertTrue(item.favorite)

        self.client.post(reverse("vault:item_delete", args=[item.pk]))
        self.assertFalse(VaultItem.objects.filter(pk=item.pk).exists())
        actions = set(ActivityLog.objects.filter(user=self.user).values_list("action", flat=True))
        self.assertTrue({"create", "reveal", "update", "delete"} <= actions)

    def test_cannot_touch_other_users_items(self):
        item = VaultItem(user=self.other, title="Mallory's")
        item.secret = "nope"
        item.save()
        self.login()
        self.assertEqual(self.client.get(reverse("vault:item_detail", args=[item.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("vault:item_reveal", args=[item.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("vault:item_delete", args=[item.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("vault:dashboard")), "Mallory")

    def test_reveal_requires_post(self):
        self.login()
        item = VaultItem.objects.create(user=self.user, title="X")
        self.assertEqual(self.client.get(reverse("vault:item_reveal", args=[item.pk])).status_code, 405)

    def test_tool_pages_render(self):
        self.login()
        for name in ("vault:generator", "vault:health", "vault:activity", "vault:account"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_generate_endpoint(self):
        res = self.client.post(reverse("vault:generate_api"), json.dumps({"length": 30}), content_type="application/json")
        self.assertEqual(len(json.loads(res.content)["password"]), 30)

    def test_export_requires_password(self):
        self.login()
        item = VaultItem(user=self.user, title="Export me")
        item.secret = "exported-secret"
        item.save()
        bad = self.client.post(reverse("vault:export"), {"password": "wrong"})
        self.assertRedirects(bad, reverse("vault:account"))
        good = self.client.post(reverse("vault:export"), {"password": PASSWORD})
        data = json.loads(good.content)
        self.assertEqual(data["items"][0]["secret"], "exported-secret")

    def test_change_password_and_delete_account(self):
        self.login()
        res = self.client.post(reverse("vault:account"), {
            "intent": "password", "old_password": PASSWORD,
            "new_password1": "Brand-New-Pass-99!", "new_password2": "Brand-New-Pass-99!",
        })
        self.assertRedirects(res, reverse("vault:account"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Brand-New-Pass-99!"))

        res = self.client.post(reverse("vault:account"), {"intent": "delete", "password": "Brand-New-Pass-99!"})
        self.assertRedirects(res, reverse("landing"))
        self.assertFalse(get_user_model().objects.filter(username="alice").exists())

    def test_seed_demo_command(self):
        from django.core.management import call_command

        call_command("seed_demo", "--password", "demo-pass-123456", verbosity=0)
        demo = get_user_model().objects.get(username="demo")
        self.assertGreaterEqual(demo.vault_items.count(), 8)
