# 🏥 MediBook — Doctor Appointment Booking MVP

## Folder Structure

```
doctor_app/
├── app.py              ← Flask backend (routes, DB, logic)
├── clinic.db           ← SQLite database (auto-created on first run)
├── requirements.txt
├── templates/
│   ├── index.html      ← Login page
│   └── dashboard.html  ← Dashboard (Admin / Doctor / Patient)
└── static/             ← (reserved for future static assets)
```

---

## Quick Start

### 1. Install dependencies
```bash
cd doctor_app
pip install -r requirements.txt
```

### 2. Run the app
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## Demo Credentials

| Role    | Username      | Password    |
|---------|---------------|-------------|
| Admin   | admin         | admin123    |
| Doctor  | drsmith       | doctor123   |
| Patient | john_patient  | patient123  |

---

## Features by Role

### 👤 Admin
- View all appointments across all doctors
- View registered doctors

### 👨‍⚕️ Doctor
- View own appointments
- Mark appointments as **Completed** or **Cancelled**

### 🧑‍⚕️ Patient
- Browse doctors
- Check real-time slot availability (30-min slots)
- Book appointments
- View booking history with status

---

## Booking Rules
- Cannot book past dates
- Slots are 30 minutes each
- No double-booking (DB-level unique constraint)
- Doctor must have a roster for the selected day

---

## Database Tables
- `users` — authentication with hashed passwords
- `doctors` — doctor profiles linked to users
- `patients` — patient profiles linked to users
- `clinics` — clinic registry
- `doctor_roster` — availability schedule (Mon–Fri)
- `appointments` — booked appointments with status

---

## Sample Data (auto-seeded)
- 1 clinic: **City Health Clinic**
- 1 doctor: **Dr. Sarah Smith** (General Physician)
  - Available Mon–Fri, 9AM–5PM (30-min slots = 16 slots/day)
- 1 patient: **John Doe**
