from django.urls import path
from .views import VaultItemListCreate, VaultItemDetail

urlpatterns = [
    path('', VaultItemListCreate.as_view(), name='vault-list-create'),
    path('<int:pk>/', VaultItemDetail.as_view(), name='vault-detail'),
]

