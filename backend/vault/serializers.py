from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import ActivityLog, VaultItem
from .passwords import LABELS


class VaultItemSerializer(serializers.ModelSerializer):
    """Vault item without its plaintext secret (use the ``reveal`` action)."""

    secret = serializers.CharField(write_only=True, required=False, allow_blank=True,
                                   trim_whitespace=False, style={"input_type": "password"})
    notes = serializers.CharField(write_only=True, required=False, allow_blank=True,
                                  trim_whitespace=False)
    strength = serializers.SerializerMethodField()
    tag_list = serializers.ListField(read_only=True)

    class Meta:
        model = VaultItem
        fields = [
            "id", "title", "category", "username", "url", "tags", "tag_list", "favorite",
            "secret", "notes", "strength", "created_at", "updated_at",
            "secret_changed_at", "last_accessed_at",
        ]
        read_only_fields = ["created_at", "updated_at", "secret_changed_at", "last_accessed_at"]

    def get_strength(self, obj):
        if obj.strength_score is None:
            return None
        return {"score": obj.strength_score, "label": LABELS[obj.strength_score]}

    def _apply_encrypted(self, instance, validated_data):
        if "secret" in validated_data:
            instance.secret = validated_data.pop("secret")
        if "notes" in validated_data:
            instance.notes = validated_data.pop("notes")

    def create(self, validated_data):
        secret = validated_data.pop("secret", "")
        notes = validated_data.pop("notes", "")
        instance = VaultItem(**validated_data)
        instance.secret = secret
        instance.notes = notes
        instance.save()
        return instance

    def update(self, instance, validated_data):
        self._apply_encrypted(instance, validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class VaultItemRevealSerializer(serializers.ModelSerializer):
    secret = serializers.CharField(read_only=True)
    notes = serializers.CharField(read_only=True)

    class Meta:
        model = VaultItem
        fields = ["id", "title", "username", "url", "secret", "notes"]


class ActivityLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = ActivityLog
        fields = ["id", "action", "action_display", "item", "item_title", "ip_address", "created_at"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = get_user_model()
        fields = ["id", "username", "email", "password"]

    def validate(self, attrs):
        user = get_user_model()(username=attrs.get("username"), email=attrs.get("email", ""))
        validate_password(attrs["password"], user=user)
        return attrs

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)


class PasswordGeneratorSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["password", "passphrase"], default="password")
    length = serializers.IntegerField(min_value=4, max_value=128, default=20)
    words = serializers.IntegerField(min_value=3, max_value=12, default=5)
    lowercase = serializers.BooleanField(default=True)
    uppercase = serializers.BooleanField(default=True)
    digits = serializers.BooleanField(default=True)
    symbols = serializers.BooleanField(default=True)
    exclude_ambiguous = serializers.BooleanField(default=False)
    separator = serializers.CharField(max_length=3, default="-", allow_blank=True, trim_whitespace=False)
