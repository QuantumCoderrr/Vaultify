from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from vault.models import ActivityLog, VaultItem


class VaultAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.alice = User.objects.create_user("alice", password="alice-long-password")
        self.bob = User.objects.create_user("bob", password="bob-long-password")

    def auth(self, username, password):
        res = self.client.post(reverse("api-token"), {"username": username, "password": password})
        self.assertEqual(res.status_code, 200, res.content)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_requires_authentication(self):
        self.assertEqual(self.client.get("/api/v1/items/").status_code, 401)

    def test_register(self):
        res = self.client.post(reverse("api-register"),
                               {"username": "carol", "password": "Sup3r-Secure-Pass!"})
        self.assertEqual(res.status_code, 201)
        self.assertNotIn("password", res.data)
        res = self.client.post(reverse("api-register"), {"username": "dave", "password": "123"})
        self.assertEqual(res.status_code, 400)

    def test_create_list_reveal(self):
        self.auth("alice", "alice-long-password")
        res = self.client.post("/api/v1/items/", {
            "title": "GitHub", "username": "alice", "secret": "s3cr3t-Value!", "notes": "2FA on",
            "user": self.bob.pk,  # must be ignored
        }, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertNotIn("secret", res.data)
        item = VaultItem.objects.get(pk=res.data["id"])
        self.assertEqual(item.user, self.alice)

        listing = self.client.get("/api/v1/items/").data
        self.assertEqual(listing["count"], 1)
        self.assertNotIn("secret", listing["results"][0])

        revealed = self.client.get(f"/api/v1/items/{item.pk}/reveal/").data
        self.assertEqual(revealed["secret"], "s3cr3t-Value!")
        self.assertEqual(revealed["notes"], "2FA on")
        self.assertTrue(ActivityLog.objects.filter(user=self.alice, action="reveal").exists())

    def test_users_cannot_see_each_others_items(self):
        item = VaultItem(user=self.bob, title="Bob's bank")
        item.secret = "bob-secret"
        item.save()
        self.auth("alice", "alice-long-password")
        self.assertEqual(self.client.get("/api/v1/items/").data["count"], 0)
        self.assertEqual(self.client.get(f"/api/v1/items/{item.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/items/{item.pk}/reveal/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/v1/items/{item.pk}/").status_code, 404)
        self.assertTrue(VaultItem.objects.filter(pk=item.pk).exists())

    def test_update_and_search(self):
        self.auth("alice", "alice-long-password")
        pk = self.client.post("/api/v1/items/", {"title": "Mail", "secret": "a"}, format="json").data["id"]
        res = self.client.patch(f"/api/v1/items/{pk}/", {"secret": "N3w-Much-Stronger-Secret!"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.data["strength"]["score"], 3)
        self.assertEqual(self.client.get("/api/v1/items/?q=mai").data["count"], 1)
        self.assertEqual(self.client.get("/api/v1/items/?q=zzz").data["count"], 0)

    def test_health_and_tools(self):
        self.auth("alice", "alice-long-password")
        res = self.client.get("/api/v1/items/health/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["score"], 100)
        gen = self.client.post("/api/v1/tools/generate/", {"length": 32}, format="json").data
        self.assertEqual(len(gen["password"]), 32)
        phrase = self.client.post("/api/v1/tools/generate/", {"mode": "passphrase", "words": 4}, format="json").data
        self.assertGreaterEqual(phrase["password"].count("-"), 3)
