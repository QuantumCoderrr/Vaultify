from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm

from .models import VaultItem


class StyledFormMixin:
    """Adds the design-system CSS class to every widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "checkbox")
            else:
                widget.attrs.setdefault("class", "input")


class SignUpForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=False, help_text="Optional.")

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(placeholder="satoshi", autofocus=True)
        self.fields["email"].widget.attrs.update(placeholder="you@example.com")
        self.fields["password1"].widget.attrs.update(placeholder="At least 10 characters",
                                                     **{"data-strength": "true"})
        self.fields["password2"].widget.attrs.update(placeholder="Repeat password")


class LoginForm(StyledFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(placeholder="Username")
        self.fields["password"].widget.attrs.update(placeholder="Master password")


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget.attrs["data-strength"] = "true"


class VaultItemForm(StyledFormMixin, forms.ModelForm):
    secret = forms.CharField(
        required=False,
        strip=False,
        label="Password / secret",
        widget=forms.PasswordInput(render_value=True, attrs={
            "autocomplete": "new-password", "data-strength": "true", "spellcheck": "false",
        }),
    )
    notes = forms.CharField(
        required=False,
        strip=False,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Recovery codes, PINs, anything private…"}),
    )

    class Meta:
        model = VaultItem
        fields = ["title", "category", "username", "url", "tags", "favorite"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. GitHub", "autofocus": True}),
            "username": forms.TextInput(attrs={"placeholder": "Email or username", "autocomplete": "off"}),
            "url": forms.URLInput(attrs={"placeholder": "https://"}),
            "tags": forms.TextInput(attrs={"placeholder": "work, dev, finance"}),
        }
        labels = {"url": "Website", "username": "Username / email", "favorite": "Pin to favourites"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["secret"].initial = self.instance.secret
            self.fields["notes"].initial = self.instance.notes

    def clean_tags(self):
        tags = [t.strip().lower() for t in self.cleaned_data["tags"].split(",") if t.strip()]
        return ", ".join(dict.fromkeys(tags))

    def save(self, commit=True):
        item = super().save(commit=False)
        item.secret = self.cleaned_data.get("secret", "")
        item.notes = self.cleaned_data.get("notes", "")
        if commit:
            item.save()
        return item


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "input", "placeholder": "Confirm your password"})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password.")
        return password
