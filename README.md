# LANDLORDPRO

**Motto:** Smart Property Management System for Landlords and Tenants

A full Flask web app implemented from the uploaded `LANDLORDPRO.txt` framework. The app runs immediately with SQLite and seeded demo data, while also including MySQL schema, Flask-Migrate support, Docker/deployment files, JWT APIs, real-integration scaffolds, and production configuration templates.

## Completed Modules

* Authentication: register, login, real token-based password reset flow, optional OTP 2FA
* Property management: add properties, units, status, due day, late-fee percentage
* Tenant management: approval, assignment, ID number, occupation, emergency contact, lease dates, lease document upload
* Rent management: monthly rent tracking, paid this month, outstanding balance, automatic late fee calculation
* M-Pesa: Daraja STK Push implementation with simulation fallback when credentials are missing
* Maintenance: tenant repair requests, priority, photo upload, landlord status workflow
* Invoices: PDF rent invoices and repair invoices
* WhatsApp: direct contact links
* AI assistant: OpenAI integration if `OPENAI\_API\_KEY` is set, rule-based fallback otherwise
* Reports: occupancy, revenue and repairs reports, filters, PDF export, Excel export
* Chat: REST chat plus Socket.IO real-time event support
* Notifications: email/SMS service with console fallback and in-app notifications
* Security/RBAC: landlord/tenant route protections and reusable decorators
* API/mobile readiness: JWT REST API under `/api/v1`
* Production: `.env.example`, Dockerfile, docker-compose, Gunicorn, Nginx example, Procfile
* Tests: pytest route/API smoke tests

## Run Locally

```bash
cd landlordpro
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: [http://127.0.0.1:5000](http://127.0.0.1:5000)



\## First Account Setup



After deployment, open the app and use \*\*Create Account\*\* to register the first landlord account.



Tenants can then register themselves or be added by a landlord.

## API Example

```bash
curl -X POST http://127.0.0.1:5000/api/v1/login \\
  -H 'Content-Type: application/json' \\
  -d '{"email":"tenant@landlordpro.com","password":"password123"}'
```

Use the returned token:

```bash
curl http://127.0.0.1:5000/api/v1/tenant/dashboard \\
  -H "Authorization: Bearer YOUR\_TOKEN"
```

## Production Setup

1. Copy env file:

```bash
cp .env.example .env
```

2. Set secure values for:
* `SECRET\_KEY`
* `JWT\_SECRET`
* `DATABASE\_URL`
* M-Pesa credentials
* SMTP credentials
* `OPENAI\_API\_KEY` if using live AI
3. Use Docker:

```bash
docker compose up --build
```

Or Gunicorn:

```bash
gunicorn -c gunicorn.conf.py app:app
```

## Database / Migration

SQLite is default for local development. MySQL reference schema is in:

```text
database/schema.sql
```

Flask-Migrate is configured. For production migrations:

```bash
flask --app app db init
flask --app app db migrate -m "initial schema"
flask --app app db upgrade
```

## Tests

```bash
pytest -q
```

## Project Structure

```text
landlordpro/
├── app.py
├── config.py
├── extensions.py
├── requirements.txt
├── routes/
├── models/
├── services/
├── templates/
├── static/
├── tests/
├── uploads/repairs/
├── database/schema.sql
├── Dockerfile
├── docker-compose.yml
├── gunicorn.conf.py
└── .env.example
```

