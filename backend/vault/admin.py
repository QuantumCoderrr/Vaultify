from django.contrib import admin

from .models import ActivityLog, VaultItem


@admin.register(VaultItem)
class VaultItemAdmin(admin.ModelAdmin):
    """Admins can manage metadata but never see decrypted secrets."""

    list_display = ("title", "user", "category", "favorite", "strength_score", "updated_at")
    list_filter = ("category", "favorite")
    search_fields = ("title", "username", "url", "user__username")
    exclude = ("encrypted_secret", "encrypted_notes")
    readonly_fields = ("secret_fingerprint", "strength_score", "created_at", "updated_at",
                       "secret_changed_at", "last_accessed_at")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "item_title", "ip_address")
    list_filter = ("action",)
    search_fields = ("user__username", "item_title", "ip_address")
    readonly_fields = [f.name for f in ActivityLog._meta.fields]

    def has_add_permission(self, request):
        return False
