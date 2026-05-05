"""
db.py — Run this once to create and seed the MediBook database.
Usage:  python db.py
"""
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB = 'clinic.db'


def init_db():
    if os.path.exists(DB):
        os.remove(DB)
        print(f"[db.py] Removed old {DB}")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    print("[db.py] Creating tables…")

    c.executescript("""
    -- ── USERS ──────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS users (
        user_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT    UNIQUE NOT NULL,
        password TEXT    NOT NULL,
        role     TEXT    NOT NULL CHECK(role IN ('ADMIN','DOCTOR','PATIENT'))
    );

    -- ── DOCTORS ────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS doctors (
        doctor_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL REFERENCES users(user_id),
        name        TEXT    NOT NULL,
        speciality  TEXT    NOT NULL,
        phone       TEXT,
        email       TEXT
    );

    -- ── PATIENTS ───────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS patients (
        patient_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL REFERENCES users(user_id),
        name        TEXT    NOT NULL
    );

    -- ── CLINICS ────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS clinics (
        clinic_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        clinic_name TEXT    NOT NULL,
        address     TEXT,
        phone       TEXT
    );

    -- ── DOCTOR–CLINIC MAPPING ───────────────────────────────────────────────
    -- Many-to-many: a doctor can work at multiple clinics
    CREATE TABLE IF NOT EXISTS doctor_clinic_map (
        map_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id   INTEGER NOT NULL REFERENCES doctors(doctor_id),
        clinic_id   INTEGER NOT NULL REFERENCES clinics(clinic_id),
        UNIQUE(doctor_id, clinic_id)
    );

    -- ── DOCTOR ROSTER ───────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS doctor_roster (
        roster_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id   INTEGER NOT NULL REFERENCES doctors(doctor_id),
        clinic_id   INTEGER NOT NULL REFERENCES clinics(clinic_id),
        day_of_week TEXT    NOT NULL CHECK(day_of_week IN ('Mon','Tue','Wed','Thu','Fri','Sat','Sun')),
        start_time  TEXT    NOT NULL,
        end_time    TEXT    NOT NULL,
        CHECK(start_time < end_time)
    );

    -- ── DOCTOR LEAVE ────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS doctor_leave (
        leave_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id   INTEGER NOT NULL REFERENCES doctors(doctor_id),
        start_date  TEXT    NOT NULL,
        end_date    TEXT    NOT NULL,
        reason      TEXT    NOT NULL CHECK(reason IN ('SICK','CONFERENCE','OUT_OF_STATION')),
        notes       TEXT,
        CHECK(start_date <= end_date)
    );

    -- ── APPOINTMENTS ────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS appointments (
        appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id     INTEGER NOT NULL REFERENCES patients(patient_id),
        doctor_id      INTEGER NOT NULL REFERENCES doctors(doctor_id),
        clinic_id      INTEGER NOT NULL REFERENCES clinics(clinic_id),
        appt_date      TEXT    NOT NULL,
        appt_time      TEXT    NOT NULL,
        status         TEXT    NOT NULL DEFAULT 'BOOKED'
                       CHECK(status IN ('BOOKED','COMPLETED','CANCELLED','NOSHOW')),
        UNIQUE(doctor_id, appt_date, appt_time)
    );
    """)

    print("[db.py] Seeding demo data…")

    # ── USERS
    conn.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
        ('admin', generate_password_hash('admin123'), 'ADMIN'))
    conn.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
        ('drsmith', generate_password_hash('doctor123'), 'DOCTOR'))
    conn.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
        ('john_patient', generate_password_hash('patient123'), 'PATIENT'))

    # ── DOCTOR (user_id=2)
    conn.execute("""INSERT INTO doctors (user_id,name,speciality,phone,email)
        VALUES (2,'Dr. Sarah Smith','General Physician','9876543210','sarah@medibook.com')""")

    # ── PATIENT (user_id=3)
    conn.execute("INSERT INTO patients (user_id,name) VALUES (3,'John Doe')")

    # ── CLINIC
    conn.execute("""INSERT INTO clinics (clinic_name,address,phone)
        VALUES ('City Health Clinic','123 Main Street, Downtown','044-22334455')""")

    # ── DOCTOR–CLINIC MAP  (doctor_id=1, clinic_id=1)
    conn.execute("INSERT INTO doctor_clinic_map (doctor_id,clinic_id) VALUES (1,1)")

    # ── ROSTER: Mon–Fri, 09:00–17:00
    for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']:
        conn.execute("""INSERT INTO doctor_roster (doctor_id,clinic_id,day_of_week,start_time,end_time)
            VALUES (1,1,?,?,?)""", (day, '09:00', '17:00'))

    conn.commit()
    conn.close()
    print(f"[db.py] Done — {DB} is ready.")
    print()
    print("  Demo credentials:")
    print("  ┌─────────────┬───────────────┬─────────────┐")
    print("  │ Role        │ Username      │ Password    │")
    print("  ├─────────────┼───────────────┼─────────────┤")
    print("  │ Admin       │ admin         │ admin123    │")
    print("  │ Doctor      │ drsmith       │ doctor123   │")
    print("  │ Patient     │ john_patient  │ patient123  │")
    print("  │ Doctor      │ drmyra        │ doctor123   │")
    print("  │ Patient     │ kavyap        │ patient123  │")
    print("  └─────────────┴───────────────┴─────────────┘")


if __name__ == '__main__':
    init_db()