from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import api

router = DefaultRouter()
router.register("items", api.VaultItemViewSet, basename="item")

urlpatterns = [
    path("auth/register/", api.RegisterView.as_view(), name="api-register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="api-token"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="api-token-refresh"),
    path("activity/", api.ActivityLogList.as_view(), name="api-activity"),
    path("tools/generate/", api.generate, name="api-generate"),
    path("tools/strength/", api.strength, name="api-strength"),
    path("", include(router.urls)),
]
