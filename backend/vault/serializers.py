from rest_framework import serializers
from .models import VaultItem

class VaultItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaultItem
        fields = '__all__'

