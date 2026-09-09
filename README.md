# Sahaayak Cooperative Services API

FastAPI backend for a cooperative-owned household and community service marketplace.

## Included capabilities

- Customer, provider, and admin JWT authentication
- Provider profiles, cooperative association, verification, skills, certifications, and welfare records
- Verified service listings with category, skill, radius, and geo-location filtering
- Scheduled and emergency bookings with distance-ready coordinates
- Booking status workflow and demo digital payment/invoice records
- Customer ratings and feedback
- Federation dashboard and a transparent demand forecast endpoint
- Preferred-language field ready for multilingual mobile clients

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open interactive API docs at `http://127.0.0.1:8000/docs`.

## Run the frontend

Keep the API running, then open a second terminal from this folder:

```powershell
.venv\Scripts\python.exe -m http.server 4173 --directory frontend
```

Open `http://127.0.0.1:4173`. The frontend starts with the office/service request form, including the customer's need, preferred date and time, approver/contact name, address, and a draggable map pin. After submission it shows nearby cooperative workers and saves selected bookings in the browser.

## Authentication

Register with `POST /auth/register`, then use `POST /auth/login` with form fields `username` (email) and `password`. Send the returned bearer token as `Authorization: Bearer <token>`.

Customer registration requires `full_name`, `phone`, and a 12-digit `aadhaar_number`. Worker registration uses `role: provider` and additionally requires `upi_id`, `bank_account_number`, `bank_ifsc`, `permanent_address`, and `residential_address`. The frontend exposes these worker fields only when the applicant selects “I want to register as a service provider”.

Users can select **Forgot password?** on the login form. The local API uses `POST /auth/forgot-password` followed by `POST /auth/reset-password` with a 15-minute reset token. For production, send the token through verified email or SMS instead of returning it directly from the API.

A provider must create a profile, then an admin must verify it before the provider can publish services. The payment endpoint is intentionally a development adapter; replace it with a gateway integration before production.

## Suggested production hardening

Use PostgreSQL, Alembic migrations, a managed secret, encryption or tokenization for Aadhaar and bank data, object storage for certificates, a real payment provider, a queue for notifications, and a proper geospatial index such as PostGIS.
