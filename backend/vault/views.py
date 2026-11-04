"""Server-rendered web interface."""

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    DeleteAccountForm,
    LoginForm,
    SignUpForm,
    StyledPasswordChangeForm,
    VaultItemForm,
)
from .models import ActivityLog, VaultItem
from .passwords import estimate_strength, generate_passphrase, generate_password
from .security import analyze


# --- Public pages -------------------------------------------------------------

def landing(request):
    if request.user.is_authenticated:
        return redirect("vault:dashboard")
    return render(request, "vault/landing.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("vault:dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to Vaultify, {user.username}! Your vault is ready.")
        return redirect("vault:dashboard")
    return render(request, "registration/signup.html", {"form": form})


class LoginView(auth_views.LoginView):
    """Login with simple cache-based brute-force lockout."""

    form_class = LoginForm
    redirect_authenticated_user = True

    def _key(self):
        username = (self.request.POST.get("username") or "").lower()
        ip = self.request.META.get("REMOTE_ADDR", "")
        return f"login-attempts:{username}:{ip}"

    def post(self, request, *args, **kwargs):
        self.locked_out = cache.get(self._key(), 0) >= settings.LOGIN_MAX_ATTEMPTS
        if self.locked_out:
            # Don't even attempt authentication while locked out (no password oracle).
            minutes = max(1, settings.LOGIN_LOCKOUT_SECONDS // 60)
            form = self.form_class(request=request, initial={"username": request.POST.get("username", "")})
            return self.render_to_response(self.get_context_data(
                form=form,
                lockout_message=f"Too many failed attempts. Try again in {minutes} minute(s).",
            ), status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        if self.request.method == "POST":
            key = self._key()
            cache.set(key, cache.get(key, 0) + 1, settings.LOGIN_LOCKOUT_SECONDS)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._key())
        return super().form_valid(form)


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "Vault locked. See you soon.")
    return redirect("landing")


# --- Vault --------------------------------------------------------------------

def _user_items(request):
    return VaultItem.objects.filter(user=request.user)


@login_required
def dashboard(request):
    items = _user_items(request)
    all_items = list(items)
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    tag = request.GET.get("tag", "").strip().lower()
    favorites = request.GET.get("favorites") == "1"

    filtered = items
    if q:
        filtered = filtered.filter(Q(title__icontains=q) | Q(username__icontains=q)
                                   | Q(url__icontains=q) | Q(tags__icontains=q))
    if category in VaultItem.Category.values:
        filtered = filtered.filter(category=category)
    if favorites:
        filtered = filtered.filter(favorite=True)
    if tag:
        filtered = [i for i in filtered if tag in i.tag_list]

    counts = dict(items.values_list("category").annotate(n=Count("id")))
    categories = [
        {"value": value, "label": label, "count": counts.get(value, 0)}
        for value, label in VaultItem.Category.choices
    ]
    tags = sorted({t for i in all_items for t in i.tag_list})
    report = analyze(all_items)

    return render(request, "vault/dashboard.html", {
        "items": filtered,
        "q": q,
        "active_category": category,
        "active_tag": tag,
        "favorites": favorites,
        "categories": categories,
        "tags": tags,
        "total": len(all_items),
        "favorite_count": sum(1 for i in all_items if i.favorite),
        "report": report,
        "recent_activity": ActivityLog.objects.filter(user=request.user)[:5],
    })


@login_required
def item_detail(request, pk):
    item = get_object_or_404(_user_items(request), pk=pk)
    return render(request, "vault/item_detail.html", {
        "item": item,
        "history": ActivityLog.objects.filter(user=request.user, item=item)[:10],
        "reused": item.secret_fingerprint and _user_items(request).filter(
            secret_fingerprint=item.secret_fingerprint).exclude(pk=item.pk).exists(),
    })


@login_required
def item_create(request):
    initial = {"category": request.GET.get("category", VaultItem.Category.LOGIN)}
    form = VaultItemForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.user = request.user
        item.save()
        ActivityLog.record(request, ActivityLog.Action.CREATE, item)
        messages.success(request, f"“{item.title}” was added to your vault.")
        return redirect(item)
    return render(request, "vault/item_form.html", {"form": form, "is_new": True})


@login_required
def item_update(request, pk):
    item = get_object_or_404(_user_items(request), pk=pk)
    form = VaultItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        ActivityLog.record(request, ActivityLog.Action.UPDATE, item)
        messages.success(request, f"“{item.title}” was updated.")
        return redirect(item)
    return render(request, "vault/item_form.html", {"form": form, "item": item, "is_new": False})


@login_required
@require_POST
def item_delete(request, pk):
    item = get_object_or_404(_user_items(request), pk=pk)
    ActivityLog.record(request, ActivityLog.Action.DELETE, item)
    title = item.title
    item.delete()
    messages.success(request, f"“{title}” was deleted.")
    return redirect("vault:dashboard")


@login_required
@require_POST
def item_reveal(request, pk):
    """Return decrypted fields as JSON. ``?action=copy`` logs a copy event."""
    item = get_object_or_404(_user_items(request), pk=pk)
    item.last_accessed_at = timezone.now()
    item.save(update_fields=["last_accessed_at"])
    action = ActivityLog.Action.COPY if request.GET.get("action") == "copy" else ActivityLog.Action.REVEAL
    ActivityLog.record(request, action, item)
    return JsonResponse({"secret": item.secret, "notes": item.notes})


@login_required
@require_POST
def item_toggle_favorite(request, pk):
    item = get_object_or_404(_user_items(request), pk=pk)
    item.favorite = not item.favorite
    item.save(update_fields=["favorite"])
    if request.headers.get("x-requested-with") == "fetch":
        return JsonResponse({"favorite": item.favorite})
    return redirect(request.POST.get("next") or "vault:dashboard")


# --- Tools --------------------------------------------------------------------

@login_required
def generator(request):
    return render(request, "vault/generator.html", {"initial": generate_password(20)})


@require_POST
def generate_api(request):
    """Lightweight JSON endpoint used by the UI (CSRF-protected)."""
    try:
        opts = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        opts = {}
    if opts.get("mode") == "passphrase":
        value = generate_passphrase(
            words=int(opts.get("words", 5)),
            separator=str(opts.get("separator", "-"))[:3],
            capitalize=bool(opts.get("capitalize", True)),
            add_number=bool(opts.get("add_number", True)),
        )
    else:
        value = generate_password(
            length=int(opts.get("length", 20)),
            lowercase=bool(opts.get("lowercase", True)),
            uppercase=bool(opts.get("uppercase", True)),
            digits=bool(opts.get("digits", True)),
            symbols=bool(opts.get("symbols", True)),
            exclude_ambiguous=bool(opts.get("exclude_ambiguous", False)),
        )
    return JsonResponse({"password": value, "strength": estimate_strength(value).as_dict()})


@require_POST
def strength_api(request):
    try:
        password = json.loads(request.body or "{}").get("password", "")
    except (json.JSONDecodeError, AttributeError):
        password = ""
    return JsonResponse(estimate_strength(str(password)).as_dict())


@login_required
def health(request):
    return render(request, "vault/health.html", {"report": analyze(_user_items(request))})


@login_required
def activity(request):
    logs = ActivityLog.objects.filter(user=request.user).select_related("item")
    action = request.GET.get("action", "")
    if action in ActivityLog.Action.values:
        logs = logs.filter(action=action)
    page = Paginator(logs, 20).get_page(request.GET.get("page"))
    return render(request, "vault/activity.html", {
        "page": page, "actions": ActivityLog.Action.choices, "active_action": action,
    })


# --- Account ------------------------------------------------------------------

@login_required
def account(request):
    password_form = StyledPasswordChangeForm(request.user)
    delete_form = DeleteAccountForm(request.user)

    if request.method == "POST":
        intent = request.POST.get("intent")
        if intent == "password":
            password_form = StyledPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                ActivityLog.record(request, ActivityLog.Action.PASSWORD_CHANGE)
                messages.success(request, "Your master password was changed.")
                return redirect("vault:account")
        elif intent == "delete":
            delete_form = DeleteAccountForm(request.user, request.POST)
            if delete_form.is_valid():
                user = request.user
                logout(request)
                user.delete()
                messages.info(request, "Your account and all vault data were permanently deleted.")
                return redirect("landing")

    return render(request, "vault/account.html", {
        "password_form": password_form,
        "delete_form": delete_form,
        "item_count": _user_items(request).count(),
    })


@login_required
@require_POST
def export_vault(request):
    if not request.user.check_password(request.POST.get("password", "")):
        messages.error(request, "Incorrect password — export cancelled.")
        return redirect("vault:account")
    data = {
        "exported_at": timezone.now().isoformat(),
        "user": request.user.username,
        "items": [
            {
                "title": i.title, "category": i.category, "username": i.username, "url": i.url,
                "secret": i.secret, "notes": i.notes, "tags": i.tag_list, "favorite": i.favorite,
                "created_at": i.created_at.isoformat(), "updated_at": i.updated_at.isoformat(),
            }
            for i in _user_items(request)
        ],
    }
    ActivityLog.record(request, ActivityLog.Action.EXPORT)
    response = HttpResponse(json.dumps(data, indent=2), content_type="application/json")
    stamp = timezone.now().strftime("%Y%m%d")
    response["Content-Disposition"] = f'attachment; filename="vaultify-export-{stamp}.json"'
    return response
