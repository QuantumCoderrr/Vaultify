from django.test import TestCase
from .models import VaultItem
from django.contrib.auth.models import User

class VaultItemModelTest(TestCase):
    def test_create_item(self):
        user = User.objects.create_user(username='testuser', password='12345')
        item = VaultItem.objects.create(user=user, title='Secret', encrypted_data='abc123')
        self.assertEqual(str(item), 'Secret')

