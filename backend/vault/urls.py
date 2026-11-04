from django.urls import path

from . import views

app_name = "vault"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("items/new/", views.item_create, name="item_create"),
    path("items/<int:pk>/", views.item_detail, name="item_detail"),
    path("items/<int:pk>/edit/", views.item_update, name="item_update"),
    path("items/<int:pk>/delete/", views.item_delete, name="item_delete"),
    path("items/<int:pk>/reveal/", views.item_reveal, name="item_reveal"),
    path("items/<int:pk>/favorite/", views.item_toggle_favorite, name="item_favorite"),
    path("generator/", views.generator, name="generator"),
    path("health/", views.health, name="health"),
    path("activity/", views.activity, name="activity"),
    path("account/", views.account, name="account"),
    path("account/export/", views.export_vault, name="export"),
    path("tools/generate/", views.generate_api, name="generate_api"),
    path("tools/strength/", views.strength_api, name="strength_api"),
]
