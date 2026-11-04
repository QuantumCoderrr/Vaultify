# Vaultify 🔐

**An encrypted personal vault built with Django.** Store passwords, payment cards, API keys, Wi-Fi credentials and private notes, all encrypted at rest. It also includes a password generator, a security health audit, a full activity log and a REST API.

![Dashboard](docs/screenshots/dashboard.png)

## ✨ Features

| | |
|---|---|
| 🔒 **Encryption at rest** | Secrets and notes are encrypted with Fernet (AES-128-CBC + HMAC-SHA256). Several keys can be configured, so you can rotate keys without downtime. |
| 🩺 **Security health** | A 0–100 score that flags weak, reused and stale passwords. Reuse is detected with keyed HMAC fingerprints, so the audit never decrypts your vault. |
| 🪄 **Password generator** | Uses Python's `secrets` module to make passwords or passphrases, with live entropy scoring. |
| 🧾 **Activity log** | Records every sign-in, failed sign-in, reveal, copy, edit, delete and export, with the IP address and time. |
| 🛡️ **Hardened by default** | Brute-force lockout, sessions that auto-lock when idle, CSRF protection, strict cookies and data scoped to its owner. Secrets never appear in page HTML: they are fetched on demand and hidden again after 20 seconds. |
| 🗂️ **Organisation** | Categories, tags, favourites, instant search and keyboard shortcuts (`/` search, `n` new item). |
| 🌗 **Polished UI** | Responsive dark and light themes, built with no frontend build step. |
| 🔌 **REST API** | Django REST Framework with JWT auth, pagination, throttling and filtering. |
| 📦 **Export** | Download a decrypted JSON backup after confirming your password. |

<table>
<tr>
<td><img src="docs/screenshots/item.png" alt="Item detail"></td>
<td><img src="docs/screenshots/generator.png" alt="Password generator"></td>
</tr>
<tr>
<td><img src="docs/screenshots/health.png" alt="Security health"></td>
<td><img src="docs/screenshots/landing.png" alt="Landing page"></td>
</tr>
</table>

## 🚀 Quick start

Requires Python 3.11 or newer.

```bash
git clone https://github.com/QuantumCoderrr/Vaultify.git
cd Vaultify/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo       # optional: demo / vaultify-demo-2024
python manage.py runserver
```

Open http://127.0.0.1:8000. You can create an account, or sign in with the demo user that `seed_demo` creates.

Create an admin user with `python manage.py createsuperuser`. The admin site is at `/admin/` and shows item metadata only, never decrypted secrets.

### Docker

```bash
docker build -t vaultify .
docker run -p 8000:8000 -e SECRET_KEY=change-me -e DEBUG=False -e ALLOWED_HOSTS=localhost -e SECURE_SSL_REDIRECT=False vaultify
```

## ⚙️ Configuration

Settings are read from environment variables or a `.env` file. See [`.env.example`](.env.example) for the full list.

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | dev key (only when `DEBUG=True`) | Django secret key. **Required in production.** |
| `DEBUG` | `True` | Turn off in production to enable HTTPS-only cookies, HSTS and the SSL redirect. |
| `DATABASE_URL` | SQLite | e.g. `postgres://user:pass@host:5432/vaultify` (install `psycopg[binary]`). |
| `VAULT_ENCRYPTION_KEY` | derived from `SECRET_KEY` | Comma-separated Fernet keys. The first one encrypts; all of them can decrypt. |
| `VAULT_SESSION_TIMEOUT` | `1800` | Seconds of inactivity before the vault auto-locks. |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCKOUT_SECONDS` | `5` / `300` | Brute-force protection. |

Generate an encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> ⚠️ Set `VAULT_ENCRYPTION_KEY` explicitly in production and back it up. If you lose it, you lose the data. If you leave it unset, changing `SECRET_KEY` makes existing secrets unreadable.

## 🔌 REST API

Base URL: `/api/v1/`. Authenticate with a JWT (`Authorization: Bearer <token>`) or a session cookie.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `auth/register/` | Create an account |
| `POST` | `auth/token/` · `auth/token/refresh/` | Get or refresh a JWT pair |
| `GET` `POST` | `items/` | List (`?q=`, `?category=`, `?favorite=true`) or create items |
| `GET` `PUT` `PATCH` `DELETE` | `items/{id}/` | Manage one item (the secret is write-only) |
| `GET` | `items/{id}/reveal/` | Decrypt the secret and notes (the reveal is logged) |
| `GET` | `items/health/` | Security health report |
| `GET` | `activity/` | Your activity log |
| `POST` | `tools/generate/` · `tools/strength/` | Generate a password, or score one |

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/token/ \
  -d username=demo -d password=vaultify-demo-2024 | python -c "import sys,json;print(json.load(sys.stdin)['access'])")
curl -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/items/
```

## 🧱 Architecture

```
backend/
├── vaultify/              # project settings & root URLs
└── vault/
    ├── models.py          # VaultItem (encrypted fields) & ActivityLog
    ├── crypto.py          # Fernet / MultiFernet helpers, key rotation
    ├── passwords.py       # generator + entropy-based strength estimator
    ├── security.py        # weak / reused / stale analysis
    ├── views.py, forms.py # server-rendered web UI
    ├── api.py, serializers.py, api_urls.py   # REST API
    ├── signals.py         # login / logout / failed-login auditing
    ├── templates/ static/ # UI (vanilla CSS + JS, no build step)
    ├── management/commands/seed_demo.py
    └── tests/             # crypto, models, API and view tests
```

**Security model.** Encryption happens on the server, so the database alone never holds plaintext secrets. Whoever controls both the server and its encryption key can decrypt them. This is the same trust model as most self-hosted apps. Vaultify is not a zero-knowledge (client-side encryption) design.

## 🧪 Tests

```bash
cd backend
python manage.py test vault
```

CI runs the test suite on Python 3.11–3.13 for every push (see `.github/workflows/ci.yml`).

## 🤝 Contributing

PRs and suggestions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

## 💬 Code of Conduct

Kindness comes first. Please read our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before you start.

## 📄 License

[MIT](LICENSE)
