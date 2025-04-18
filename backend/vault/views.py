from rest_framework import generics, permissions
from .models import VaultItem
from .serializers import VaultItemSerializer
from .permissions import IsOwner

class VaultItemListCreate(generics.ListCreateAPIView):
    queryset = VaultItem.objects.all()
    serializer_class = VaultItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class VaultItemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = VaultItem.objects.all()
    serializer_class = VaultItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

