from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime, date, timedelta
from functools import wraps

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'doctor_app_secret_2024'
DB = 'clinic.db'

# ─────────────────────────────────────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get('role') not in roles:
                return jsonify({'error': 'Unauthorized'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role     = data.get('role', '')

    if not username or not password or not role:
        return jsonify({'error': 'All fields required'}), 400

    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ).fetchone()

    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid credentials'}), 401
    if user['role'] != role:
        return jsonify({'error': 'Role mismatch'}), 401

    session['user_id']  = user['user_id']
    session['role']     = user['role']
    session['username'] = user['username']
    return jsonify({'role': user['role'], 'username': user['username']})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — APPOINTMENTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/admin/appointments')
@require_role('ADMIN')
def admin_appointments():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT a.appointment_id, p.name AS patient, d.name AS doctor,
                   d.speciality, c.clinic_name, a.appt_date, a.appt_time, a.status
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN doctors  d ON a.doctor_id  = d.doctor_id
            JOIN clinics  c ON a.clinic_id  = c.clinic_id
            ORDER BY a.appt_date DESC, a.appt_time
        """).fetchall()
    return jsonify([dict(r) for r in rows])


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — CLINICS  (CRUD)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/admin/clinics', methods=['GET'])
@require_role('ADMIN')
def admin_clinics_list():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM clinics ORDER BY clinic_id").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/admin/clinics', methods=['POST'])
@require_role('ADMIN')
def admin_clinic_add():
    data = request.json or {}
    name = (data.get('clinic_name') or '').strip()
    if not name:
        return jsonify({'error': 'clinic_name is required'}), 400
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO clinics (clinic_name,address,phone) VALUES (?,?,?)",
            (name, data.get('address', ''), data.get('phone', ''))
        )
        conn.commit()
    return jsonify({'ok': True, 'clinic_id': cur.lastrowid}), 201


@app.route('/api/admin/clinics/<int:clinic_id>', methods=['PUT'])
@require_role('ADMIN')
def admin_clinic_edit(clinic_id):
    data = request.json or {}
    name = (data.get('clinic_name') or '').strip()
    if not name:
        return jsonify({'error': 'clinic_name is required'}), 400
    with get_db() as conn:
        conn.execute(
            "UPDATE clinics SET clinic_name=?, address=?, phone=? WHERE clinic_id=?",
            (name, data.get('address', ''), data.get('phone', ''), clinic_id)
        )
        conn.commit()
    return jsonify({'ok': True})


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — DOCTORS  (read + edit)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/admin/doctors')
@require_role('ADMIN')
def admin_doctors():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT d.doctor_id, d.name, d.speciality, d.phone, d.email, u.username
            FROM doctors d JOIN users u ON d.user_id = u.user_id
            ORDER BY d.doctor_id
        """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/admin/doctors/<int:doctor_id>', methods=['PUT'])
@require_role('ADMIN')
def admin_doctor_edit(doctor_id):
    data = request.json or {}
    name = (data.get('name') or '').strip()
    spec = (data.get('speciality') or '').strip()
    if not name or not spec:
        return jsonify({'error': 'name and speciality are required'}), 400
    with get_db() as conn:
        conn.execute(
            "UPDATE doctors SET name=?, speciality=?, phone=?, email=? WHERE doctor_id=?",
            (name, spec, data.get('phone', ''), data.get('email', ''), doctor_id)
        )
        conn.commit()
    return jsonify({'ok': True})


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — DOCTOR–CLINIC MAP  (CRUD)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/admin/doctor-clinic-map')
@require_role('ADMIN')
def admin_map_list():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT m.map_id, d.name AS doctor_name, c.clinic_name,
                   m.doctor_id, m.clinic_id
            FROM doctor_clinic_map m
            JOIN doctors d ON m.doctor_id = d.doctor_id
            JOIN clinics c ON m.clinic_id = c.clinic_id
            ORDER BY m.map_id
        """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/admin/doctor-clinic-map', methods=['POST'])
@require_role('ADMIN')
def admin_map_add():
    data = request.json or {}
    doctor_id = data.get('doctor_id')
    clinic_id = data.get('clinic_id')
    if not doctor_id or not clinic_id:
        return jsonify({'error': 'doctor_id and clinic_id are required'}), 400
    try:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO doctor_clinic_map (doctor_id,clinic_id) VALUES (?,?)",
                (doctor_id, clinic_id)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Mapping already exists'}), 409
    return jsonify({'ok': True, 'map_id': cur.lastrowid}), 201


@app.route('/api/admin/doctor-clinic-map/<int:map_id>', methods=['DELETE'])
@require_role('ADMIN')
def admin_map_delete(map_id):
    with get_db() as conn:
        conn.execute("DELETE FROM doctor_clinic_map WHERE map_id=?", (map_id,))
        conn.commit()
    return jsonify({'ok': True})


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — ROSTER  (CRUD)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/admin/roster')
@require_role('ADMIN')
def admin_roster_list():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT r.roster_id, d.name AS doctor_name, c.clinic_name,
                   r.day_of_week, r.start_time, r.end_time,
                   r.doctor_id, r.clinic_id
            FROM doctor_roster r
            JOIN doctors d ON r.doctor_id = d.doctor_id
            JOIN clinics c ON r.clinic_id = c.clinic_id
            ORDER BY r.roster_id
        """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/admin/roster', methods=['POST'])
@require_role('ADMIN')
def admin_roster_add():
    data = request.json or {}
    doctor_id   = data.get('doctor_id')
    clinic_id   = data.get('clinic_id')
    day_of_week = (data.get('day_of_week') or '').strip()
    start_time  = (data.get('start_time') or '').strip()
    end_time    = (data.get('end_time') or '').strip()

    valid_days = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
    if not all([doctor_id, clinic_id, day_of_week, start_time, end_time]):
        return jsonify({'error': 'All fields required'}), 400
    if day_of_week not in valid_days:
        return jsonify({'error': f'day_of_week must be one of {valid_days}'}), 400
    if start_time >= end_time:
        return jsonify({'error': 'start_time must be before end_time'}), 400

    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO doctor_roster (doctor_id,clinic_id,day_of_week,start_time,end_time)
            VALUES (?,?,?,?,?)
        """, (doctor_id, clinic_id, day_of_week, start_time, end_time))
        conn.commit()
    return jsonify({'ok': True, 'roster_id': cur.lastrowid}), 201


@app.route('/api/admin/roster/<int:roster_id>', methods=['PUT'])
@require_role('ADMIN')
def admin_roster_edit(roster_id):
    data = request.json or {}
    start_time = (data.get('start_time') or '').strip()
    end_time   = (data.get('end_time') or '').strip()
    if not start_time or not end_time:
        return jsonify({'error': 'start_time and end_time required'}), 400
    if start_time >= end_time:
        return jsonify({'error': 'start_time must be before end_time'}), 400
    with get_db() as conn:
        conn.execute(
            "UPDATE doctor_roster SET start_time=?, end_time=? WHERE roster_id=?",
            (start_time, end_time, roster_id)
        )
        conn.commit()
    return jsonify({'ok': True})


@app.route('/api/admin/roster/<int:roster_id>', methods=['DELETE'])
@require_role('ADMIN')
def admin_roster_delete(roster_id):
    with get_db() as conn:
        conn.execute("DELETE FROM doctor_roster WHERE roster_id=?", (roster_id,))
        conn.commit()
    return jsonify({'ok': True})


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — DOCTOR LEAVE  (CRUD)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/admin/leave')
@require_role('ADMIN')
def admin_leave_list():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT l.leave_id, d.name AS doctor_name, l.start_date, l.end_date,
                   l.reason, l.notes, l.doctor_id
            FROM doctor_leave l
            JOIN doctors d ON l.doctor_id = d.doctor_id
            ORDER BY l.start_date DESC
        """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/admin/leave', methods=['POST'])
@require_role('ADMIN')
def admin_leave_add():
    data = request.json or {}
    doctor_id  = data.get('doctor_id')
    start_date = (data.get('start_date') or '').strip()
    end_date   = (data.get('end_date') or '').strip()
    reason     = (data.get('reason') or '').strip()
    notes      = (data.get('notes') or '').strip()

    valid_reasons = ('SICK', 'CONFERENCE', 'OUT_OF_STATION')
    if not all([doctor_id, start_date, end_date, reason]):
        return jsonify({'error': 'doctor_id, start_date, end_date, reason required'}), 400
    if reason not in valid_reasons:
        return jsonify({'error': f'reason must be one of {valid_reasons}'}), 400
    if start_date > end_date:
        return jsonify({'error': 'start_date must be <= end_date'}), 400

    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO doctor_leave (doctor_id,start_date,end_date,reason,notes)
            VALUES (?,?,?,?,?)
        """, (doctor_id, start_date, end_date, reason, notes))
        conn.commit()
    return jsonify({'ok': True, 'leave_id': cur.lastrowid}), 201


@app.route('/api/admin/leave/<int:leave_id>', methods=['PUT'])
@require_role('ADMIN')
def admin_leave_edit(leave_id):
    data = request.json or {}
    start_date = (data.get('start_date') or '').strip()
    end_date   = (data.get('end_date') or '').strip()
    reason     = (data.get('reason') or '').strip()
    notes      = (data.get('notes') or '').strip()

    valid_reasons = ('SICK', 'CONFERENCE', 'OUT_OF_STATION')
    if not all([start_date, end_date, reason]):
        return jsonify({'error': 'start_date, end_date, reason required'}), 400
    if reason not in valid_reasons:
        return jsonify({'error': f'reason must be one of {valid_reasons}'}), 400
    if start_date > end_date:
        return jsonify({'error': 'start_date must be <= end_date'}), 400

    with get_db() as conn:
        conn.execute("""
            UPDATE doctor_leave SET start_date=?, end_date=?, reason=?, notes=?
            WHERE leave_id=?
        """, (start_date, end_date, reason, notes, leave_id))
        conn.commit()
    return jsonify({'ok': True})


@app.route('/api/admin/leave/<int:leave_id>', methods=['DELETE'])
@require_role('ADMIN')
def admin_leave_delete(leave_id):
    with get_db() as conn:
        conn.execute("DELETE FROM doctor_leave WHERE leave_id=?", (leave_id,))
        conn.commit()
    return jsonify({'ok': True})


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — DB INSPECTOR
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/admin/db/tables')
@require_role('ADMIN')
def db_tables():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return jsonify([r['name'] for r in rows])


@app.route('/api/admin/db/schema/<table>')
@require_role('ADMIN')
def db_schema(table):
    # Whitelist: only existing table names accepted
    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            return jsonify({'error': 'Table not found'}), 404
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return jsonify([{'name': r['name'], 'type': r['type'],
                     'notnull': bool(r['notnull']), 'pk': bool(r['pk'])} for r in rows])


@app.route('/api/admin/db/data/<table>')
@require_role('ADMIN')
def db_data(table):
    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            return jsonify({'error': 'Table not found'}), 404
        rows = conn.execute(f"SELECT * FROM {table} LIMIT 200").fetchall()
        cols = [d[0] for d in conn.execute(f"SELECT * FROM {table} LIMIT 0").description] if rows else []
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return jsonify({
        'columns': cols,
        'rows':    [dict(r) for r in rows],
        'total':   total
    })


# ─────────────────────────────────────────────────────────────────────────────
# DOCTOR ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/doctor/appointments')
@require_role('DOCTOR')
def doctor_appointments():
    with get_db() as conn:
        doc = conn.execute(
            "SELECT doctor_id FROM doctors WHERE user_id=?", (session['user_id'],)
        ).fetchone()
        if not doc:
            return jsonify([])
        rows = conn.execute("""
            SELECT a.appointment_id, p.name AS patient,
                   c.clinic_name, a.appt_date, a.appt_time, a.status
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN clinics  c ON a.clinic_id  = c.clinic_id
            WHERE a.doctor_id = ?
            ORDER BY a.appt_date DESC, a.appt_time
        """, (doc['doctor_id'],)).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/doctor/appointments/<int:appt_id>/status', methods=['PATCH'])
@require_role('DOCTOR')
def update_status(appt_id):
    status = (request.json or {}).get('status', '')
    valid = ('COMPLETED', 'CANCELLED', 'NOSHOW')
    if status not in valid:
        return jsonify({'error': f'status must be one of {valid}'}), 400
    with get_db() as conn:
        doc = conn.execute(
            "SELECT doctor_id FROM doctors WHERE user_id=?", (session['user_id'],)
        ).fetchone()
        if not doc:
            return jsonify({'error': 'Doctor not found'}), 404
        conn.execute(
            "UPDATE appointments SET status=? WHERE appointment_id=? AND doctor_id=?",
            (status, appt_id, doc['doctor_id'])
        )
        conn.commit()
    return jsonify({'ok': True})


# ─────────────────────────────────────────────────────────────────────────────
# PATIENT ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/patient/doctors')
@require_role('PATIENT')
def patient_doctors():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DISTINCT d.doctor_id, d.name, d.speciality, c.clinic_name, c.clinic_id
            FROM doctors d
            JOIN doctor_roster r ON d.doctor_id = r.doctor_id
            JOIN clinics c ON r.clinic_id = c.clinic_id
            ORDER BY d.name
        """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/patient/availability')
@require_role('PATIENT')
def availability():
    doctor_id = request.args.get('doctor_id', type=int)
    appt_date = request.args.get('date', '').strip()

    if not doctor_id or not appt_date:
        return jsonify({'error': 'Missing params'}), 400

    try:
        d = datetime.strptime(appt_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Bad date format, use YYYY-MM-DD'}), 400

    if d < date.today():
        return jsonify({'error': 'Date must be today or in the future'}), 400

    day_name = d.strftime('%a')  # Mon, Tue, …

    with get_db() as conn:
        # Check if doctor is on leave for this date
        on_leave = conn.execute("""
            SELECT 1 FROM doctor_leave
            WHERE doctor_id=? AND start_date <= ? AND end_date >= ?
        """, (doctor_id, appt_date, appt_date)).fetchone()

        if on_leave:
            return jsonify({'slots': [], 'message': 'Doctor is on leave on this day'})

        roster = conn.execute("""
            SELECT r.start_time, r.end_time, r.clinic_id, c.clinic_name
            FROM doctor_roster r JOIN clinics c ON r.clinic_id = c.clinic_id
            WHERE r.doctor_id=? AND r.day_of_week=?
        """, (doctor_id, day_name)).fetchone()

        if not roster:
            return jsonify({'slots': [], 'message': 'Doctor not available on this day'})

        booked = {row['appt_time'] for row in conn.execute("""
            SELECT appt_time FROM appointments
            WHERE doctor_id=? AND appt_date=? AND status NOT IN ('CANCELLED')
        """, (doctor_id, appt_date)).fetchall()}

    # Generate 30-min slots
    slots = []
    cur = datetime.strptime(roster['start_time'], '%H:%M')
    end = datetime.strptime(roster['end_time'],   '%H:%M')
    while cur < end:
        t = cur.strftime('%H:%M')
        slots.append({'time': t, 'available': t not in booked})
        cur += timedelta(minutes=30)

    return jsonify({
        'slots':      slots,
        'clinic_id':  roster['clinic_id'],
        'clinic_name': roster['clinic_name']
    })


@app.route('/api/patient/book', methods=['POST'])
@require_role('PATIENT')
def book():
    data      = request.json or {}
    doctor_id = data.get('doctor_id')
    clinic_id = data.get('clinic_id')
    appt_date = (data.get('appt_date') or '').strip()
    appt_time = (data.get('appt_time') or '').strip()

    if not all([doctor_id, clinic_id, appt_date, appt_time]):
        return jsonify({'error': 'Missing fields'}), 400

    try:
        d = datetime.strptime(appt_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Bad date format'}), 400

    if d < date.today():
        return jsonify({'error': 'Cannot book past dates'}), 400

    with get_db() as conn:
        patient = conn.execute(
            "SELECT patient_id FROM patients WHERE user_id=?", (session['user_id'],)
        ).fetchone()
        if not patient:
            return jsonify({'error': 'Patient profile not found'}), 404
        try:
            conn.execute("""
                INSERT INTO appointments (patient_id,doctor_id,clinic_id,appt_date,appt_time,status)
                VALUES (?,?,?,?,?,'BOOKED')
            """, (patient['patient_id'], doctor_id, clinic_id, appt_date, appt_time))
            conn.commit()
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Slot already booked'}), 409

    return jsonify({'ok': True, 'message': 'Appointment booked!'})


@app.route('/api/patient/appointments')
@require_role('PATIENT')
def patient_appointments():
    with get_db() as conn:
        patient = conn.execute(
            "SELECT patient_id FROM patients WHERE user_id=?", (session['user_id'],)
        ).fetchone()
        if not patient:
            return jsonify([])
        rows = conn.execute("""
            SELECT a.appointment_id, d.name AS doctor, d.speciality,
                   c.clinic_name, a.appt_date, a.appt_time, a.status
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.doctor_id
            JOIN clinics c ON a.clinic_id = c.clinic_id
            WHERE a.patient_id = ?
            ORDER BY a.appt_date DESC, a.appt_time
        """, (patient['patient_id'],)).fetchall()
    return jsonify([dict(r) for r in rows])


# ─────────────────────────────────────────────────────────────────────────────
# STATIC PAGES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')


@app.route('/dashboard')
def dashboard():
    return send_from_directory('templates', 'dashboard.html')


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if not os.path.exists(DB):
        print(f"[app.py] {DB} not found — run `python db.py` first!")
    app.run(debug=True, port=5000)