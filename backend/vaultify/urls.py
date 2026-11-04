from django.contrib import admin
from django.urls import include, path

from vault import views as vault_views

admin.site.site_header = "Vaultify administration"
admin.site.site_title = "Vaultify admin"

urlpatterns = [
    path("", vault_views.landing, name="landing"),
    path("login/", vault_views.LoginView.as_view(), name="login"),
    path("logout/", vault_views.logout_view, name="logout"),
    path("signup/", vault_views.signup, name="signup"),
    path("vault/", include("vault.urls")),
    path("api/v1/", include("vault.api_urls")),
    path("api-auth/", include("rest_framework.urls")),
    path("admin/", admin.site.urls),
]
