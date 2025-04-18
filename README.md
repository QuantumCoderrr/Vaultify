# Vaultify 🔐

Vaultify is a secure, RESTful web app built using Django + DRF for storing encrypted personal data or secrets. PostgreSQL backs the data, and the encryption layer ensures high-grade protection of your information.

## Features
- 🔐 Encrypted Vault Storage
- 🧪 Unit Tested Models
- 📦 Django REST Framework API
- 🧠 Clean architecture with MVC pattern
- 🐘 PostgreSQL DB
- 🧪 Easy-to-use dev environment
- 🧰 Extensible and scalable folder structure

## 🚀 Tech Stack

Backend | Database | Auth | Misc |
--------|----------|------|------|
Django  | PostgreSQL | JWT  | REST, CORS |


## 🛠️ Setup Instructions

```bash
cd backend
python -m venv env
source env/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

📂 Environment Variables
Copy .env.example to .env and set appropriate keys.

```
SECRET_KEY=your_secret_key
DATABASE_URL=your_postgres_url
DEBUG=True
```

## 🤝 Contributing  
We welcome PRs and suggestions! Check out [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

## 💬 Code of Conduct  
Kindness comes first. Read our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before diving in.
