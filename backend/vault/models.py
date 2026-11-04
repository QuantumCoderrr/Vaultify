import hashlib
import hmac

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from . import crypto
from .passwords import estimate_strength


class VaultItem(models.Model):
    class Category(models.TextChoices):
        LOGIN = "login", "Login"
        CARD = "card", "Payment card"
        NOTE = "note", "Secure note"
        API_KEY = "api_key", "API key"
        WIFI = "wifi", "Wi-Fi"
        IDENTITY = "identity", "Identity"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vault_items"
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.LOGIN)
    username = models.CharField(max_length=255, blank=True)
    url = models.URLField(max_length=500, blank=True)
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated tags")
    favorite = models.BooleanField(default=False)

    # Encrypted at rest. Never read these directly; use .secret / .notes.
    encrypted_secret = models.TextField(blank=True, default="")
    encrypted_notes = models.TextField(blank=True, default="")

    # Derived metadata so security analysis never needs to decrypt everything.
    secret_fingerprint = models.CharField(max_length=64, blank=True, db_index=True, editable=False)
    strength_score = models.PositiveSmallIntegerField(null=True, blank=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    secret_changed_at = models.DateTimeField(default=timezone.now)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-favorite", "-updated_at"]
        indexes = [models.Index(fields=["user", "category"])]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("vault:item_detail", args=[self.pk])

    # --- encrypted properties ------------------------------------------------
    @property
    def secret(self) -> str:
        return crypto.decrypt(self.encrypted_secret)

    @secret.setter
    def secret(self, value: str):
        value = value or ""
        new_fp = self.fingerprint(value) if value else ""
        if new_fp != self.secret_fingerprint:
            self.secret_changed_at = timezone.now()
        self.encrypted_secret = crypto.encrypt(value)
        self.secret_fingerprint = new_fp
        self.strength_score = estimate_strength(value).score if value else None

    @property
    def notes(self) -> str:
        return crypto.decrypt(self.encrypted_notes)

    @notes.setter
    def notes(self, value: str):
        self.encrypted_notes = crypto.encrypt(value or "")

    @staticmethod
    def fingerprint(value: str) -> str:
        """Keyed hash used to detect reused secrets without decrypting them."""
        return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()

    # --- helpers -------------------------------------------------------------
    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def domain(self) -> str:
        from urllib.parse import urlparse

        return urlparse(self.url).netloc.removeprefix("www.") if self.url else ""

    @property
    def initials(self) -> str:
        return (self.title[:2] or "?").upper()

    @property
    def age_days(self) -> int:
        return (timezone.now() - self.secret_changed_at).days

    @property
    def is_weak(self) -> bool:
        return self.strength_score is not None and self.strength_score < 2


class ActivityLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = "login", "Signed in"
        LOGIN_FAILED = "login_failed", "Failed sign-in"
        LOGOUT = "logout", "Signed out"
        CREATE = "create", "Created item"
        UPDATE = "update", "Updated item"
        DELETE = "delete", "Deleted item"
        REVEAL = "reveal", "Revealed secret"
        COPY = "copy", "Copied secret"
        EXPORT = "export", "Exported vault"
        PASSWORD_CHANGE = "password_change", "Changed account password"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vault_activity"
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    item = models.ForeignKey(VaultItem, null=True, blank=True, on_delete=models.SET_NULL)
    item_title = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.get_action_display()} {self.item_title}".strip()

    @classmethod
    def record(cls, request, action, item=None, user=None):
        user = user or request.user
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
        return cls.objects.create(
            user=user,
            action=action,
            item=item,
            item_title=item.title if item else "",
            ip_address=ip or None,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )

    @property
    def tone(self) -> str:
        return {
            "login_failed": "danger",
            "delete": "danger",
            "reveal": "warning",
            "copy": "warning",
            "export": "warning",
            "create": "success",
            "login": "success",
        }.get(self.action, "info")
