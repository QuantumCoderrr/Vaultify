from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from vault.models import VaultItem
from vault.passwords import generate_passphrase, generate_password

DEMO_ITEMS = [
    dict(title="GitHub", category="login", username="dev@example.com", url="https://github.com",
         tags="work, dev", favorite=True, secret=None),
    dict(title="Google Workspace", category="login", username="me@example.com",
         url="https://accounts.google.com", tags="work", favorite=True, secret=None),
    dict(title="Netflix", category="login", username="family@example.com", url="https://netflix.com",
         tags="personal, streaming", secret="sunshine2024"),
    dict(title="Spotify", category="login", username="family@example.com", url="https://spotify.com",
         tags="personal, streaming", secret="sunshine2024"),
    dict(title="Old forum account", category="login", username="coolcat99", url="https://example.org",
         tags="personal", secret="Tr0ub4dor&3", age_days=420),
    dict(title="Visa Platinum", category="card", username="J. Doe", tags="finance", favorite=True,
         secret="4242 4242 4242 4242 · 12/29 · CVV 123",
         notes="Customer support: +1 800 555 0100\nPIN stored separately."),
    dict(title="Production API key", category="api_key", username="payments-service",
         url="https://dashboard.stripe.com", tags="work, dev",
         secret="sk_demo_51HxQ9vKZ2pL7wN3mR8tY4uB6cD0eF1gH"),
    dict(title="Home Wi-Fi", category="wifi", username="Orbit-5G", tags="home", secret=None, passphrase=True),
    dict(title="Recovery codes", category="note", tags="security",
         notes="GitHub 2FA recovery codes:\n  a1b2-c3d4\n  e5f6-g7h8\n  i9j0-k1l2"),
    dict(title="Passport", category="identity", username="Jane Doe", tags="travel",
         secret="X1234567", notes="Expires 2031-06-01"),
]


class Command(BaseCommand):
    help = "Create a demo user with a realistic, pre-populated vault."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")
        parser.add_argument("--password", default="vaultify-demo-2024")
        parser.add_argument("--reset", action="store_true", help="Delete the demo user's existing items first.")

    def handle(self, *args, username, password, reset, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.com"})
        user.set_password(password)
        user.save()

        if reset or created:
            user.vault_items.all().delete()
        elif user.vault_items.exists():
            self.stdout.write(self.style.WARNING("Demo user already has items; use --reset to recreate them."))
            return

        for spec in DEMO_ITEMS:
            spec = dict(spec)
            age = spec.pop("age_days", None)
            secret = spec.pop("secret", None)
            notes = spec.pop("notes", "")
            if spec.pop("passphrase", False):
                secret = generate_passphrase(4)
            elif secret is None and spec["category"] != "note":
                secret = generate_password(22)
            item = VaultItem(user=user, **spec)
            item.secret = secret or ""
            item.notes = notes
            if age:
                item.secret_changed_at = timezone.now() - timedelta(days=age)
            item.save()

        self.stdout.write(self.style.SUCCESS(
            f"Demo vault ready → username: {username}  password: {password}"
        ))
