"""REST API (``/api/v1/``)."""

from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import ActivityLog, VaultItem
from .passwords import estimate_strength, generate_passphrase, generate_password
from .permissions import IsOwner
from .security import analyze
from .serializers import (
    ActivityLogSerializer,
    PasswordGeneratorSerializer,
    RegisterSerializer,
    VaultItemRevealSerializer,
    VaultItemSerializer,
)


class VaultItemViewSet(viewsets.ModelViewSet):
    """CRUD for the authenticated user's vault items.

    Supports ``?q=`` search, ``?category=`` and ``?favorite=true`` filters.
    Plaintext secrets are only returned by ``GET /items/{id}/reveal/``.
    """

    serializer_class = VaultItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        qs = VaultItem.objects.filter(user=self.request.user)
        params = self.request.query_params
        if q := params.get("q"):
            qs = qs.filter(Q(title__icontains=q) | Q(username__icontains=q)
                           | Q(url__icontains=q) | Q(tags__icontains=q))
        if category := params.get("category"):
            qs = qs.filter(category=category)
        if params.get("favorite") in {"1", "true", "True"}:
            qs = qs.filter(favorite=True)
        return qs

    def perform_create(self, serializer):
        item = serializer.save(user=self.request.user)
        ActivityLog.record(self.request, ActivityLog.Action.CREATE, item)

    def perform_update(self, serializer):
        item = serializer.save()
        ActivityLog.record(self.request, ActivityLog.Action.UPDATE, item)

    def perform_destroy(self, instance):
        ActivityLog.record(self.request, ActivityLog.Action.DELETE, instance)
        instance.delete()

    @action(detail=True, methods=["get"])
    def reveal(self, request, pk=None):
        item = self.get_object()
        item.last_accessed_at = timezone.now()
        item.save(update_fields=["last_accessed_at"])
        ActivityLog.record(request, ActivityLog.Action.REVEAL, item)
        return Response(VaultItemRevealSerializer(item).data)

    @action(detail=False, methods=["get"])
    def health(self, request):
        report = analyze(VaultItem.objects.filter(user=request.user))
        brief = lambda items: [{"id": i.id, "title": i.title} for i in items]  # noqa: E731
        return Response({
            "score": report["score"],
            "grade": report["grade"],
            "total": report["total"],
            "weak": brief(report["weak"]),
            "reused": brief(report["reused"]),
            "stale": brief(report["stale"]),
        })


class ActivityLogList(generics.ListAPIView):
    serializer_class = ActivityLogSerializer

    def get_queryset(self):
        return ActivityLog.objects.filter(user=self.request.user)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def generate(request):
    """Generate a password or passphrase. Body fields are all optional."""
    serializer = PasswordGeneratorSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    opts = serializer.validated_data
    if opts["mode"] == "passphrase":
        value = generate_passphrase(words=opts["words"], separator=opts["separator"])
    else:
        value = generate_password(
            length=opts["length"], lowercase=opts["lowercase"], uppercase=opts["uppercase"],
            digits=opts["digits"], symbols=opts["symbols"],
            exclude_ambiguous=opts["exclude_ambiguous"],
        )
    return Response({"password": value, "strength": estimate_strength(value).as_dict()})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def strength(request):
    password = request.data.get("password", "")
    if not isinstance(password, str):
        return Response({"detail": "password must be a string"}, status=status.HTTP_400_BAD_REQUEST)
    return Response(estimate_strength(password).as_dict())
