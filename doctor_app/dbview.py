#!/usr/bin/env python3
"""
dbview.py — CLI browser & editor for clinic.db
Usage:  python dbview.py
"""

import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash

DB = 'clinic.db'

# ─── ANSI colors ──────────────────────────────────────────────────────────────
R  = "\033[0m"       # reset
B  = "\033[1m"       # bold
DIM= "\033[2m"       # dim
T  = "\033[96m"      # teal/cyan
GR = "\033[92m"      # green
RD = "\033[91m"      # red
YL = "\033[93m"      # yellow
BL = "\033[94m"      # blue
MG = "\033[95m"      # magenta
GY = "\033[90m"      # grey

def clr(text, *codes): return "".join(codes) + str(text) + R
def header(title): print(f"\n{clr('━'*55, T)}\n  {clr(title, B, T)}\n{clr('━'*55, T)}")
def success(msg):  print(f"  {clr('✓', GR)} {msg}")
def error(msg):    print(f"  {clr('✗', RD)} {msg}")
def info(msg):     print(f"  {clr('·', BL)} {msg}")
def warn(msg):     print(f"  {clr('!', YL)} {msg}")

# ─── DB helpers ───────────────────────────────────────────────────────────────

def get_conn():
    if not os.path.exists(DB):
        error(f"{DB} not found. Run `python db.py` first.")
        sys.exit(1)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_tables():
    with get_conn() as c:
        rows = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [r['name'] for r in rows]

def get_row_count(table):
    with get_conn() as c:
        return c.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]

# ─── Pretty table printer ─────────────────────────────────────────────────────

def print_table(cols, rows, max_col_width=22):
    if not cols:
        info("No columns.")
        return
    if not rows:
        info("(no rows)")
        return

    # Calculate column widths
    widths = [min(max(len(str(c)), max(len(str(r[i] if r[i] is not None else 'NULL'))
                for r in rows)), max_col_width)
              for i, c in enumerate(cols)]
    widths = [max(w, len(str(cols[i]))) for i, w in enumerate(widths)]

    sep  = clr("┼", GY).join(clr("─" * (w+2), GY) for w in widths)
    top  = clr("┬", GY).join(clr("─" * (w+2), GY) for w in widths)
    bot  = clr("┴", GY).join(clr("─" * (w+2), GY) for w in widths)

    def row_str(vals, bold=False):
        cells = []
        for i, v in enumerate(vals):
            s = str(v) if v is not None else clr("NULL", DIM)
            if len(str(v) if v is not None else "NULL") > max_col_width:
                s = (str(v)[:max_col_width-1] if v else "NULL") + clr("…", DIM)
            pad = widths[i] - len(str(v) if v is not None else "NULL")
            pad = max(pad, 0)
            cell = f" {clr(s, B) if bold else s}{' '*pad} "
            cells.append(cell)
        return clr("│", GY).join(cells)

    print(f"  {clr('┌', GY)}{top}{clr('┐', GY)}")
    print(f"  {clr('│', GY)}{row_str(cols, bold=True)}{clr('│', GY)}")
    print(f"  {clr('├', GY)}{sep}{clr('┤', GY)}")
    for r in rows:
        print(f"  {clr('│', GY)}{row_str(list(r))}{clr('│', GY)}")
    print(f"  {clr('└', GY)}{bot}{clr('┘', GY)}")
    print(f"  {clr(f'{len(rows)} row(s)', DIM)}\n")

# ─── SCREENS ──────────────────────────────────────────────────────────────────

def screen_home():
    os.system('cls' if os.name == 'nt' else 'clear')
    tables = get_tables()
    header("MediBook — dbview")
    print(f"\n  {clr('DB:', DIM)} {clr(os.path.abspath(DB), YL)}\n")
    print(f"  {clr('TABLES', B)}\n")
    for i, t in enumerate(tables, 1):
        cnt = get_row_count(t)
        print(f"  {clr(str(i).rjust(2), GY)}  {clr(t, T):<28} {clr(str(cnt)+' rows', DIM)}")

    print(f"""
  {clr('COMMANDS', B)}
  {clr('v', GR)} <table>  — view table rows       {clr('e.g. v users', DIM)}
  {clr('v', GR)} all     — view ALL tables at once
  {clr('s', GR)} <sql>    — run any SQL            {clr('e.g. s SELECT * FROM doctors', DIM)}
  {clr('a', GR)}          — add user/doctor/patient (guided)
  {clr('d', GR)} <table> <id> — delete a row       {clr('e.g. d users 3', DIM)}
  {clr('q', GR)}          — quit
""")


def screen_view(table):
    with get_conn() as c:
        exists = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            error(f"Table '{table}' not found.")
            return
        rows = c.execute(f"SELECT * FROM [{table}]").fetchall()
        cols = [d[0] for d in c.execute(f"SELECT * FROM [{table}] LIMIT 0").description] if not rows else list(rows[0].keys())

    header(f"TABLE: {table}  ({len(rows)} rows)")
    print_table(cols, rows)


def screen_view_all():
    tables = get_tables()
    header("ALL TABLES")
    for table in tables:
        with get_conn() as c:
            rows = c.execute(f"SELECT * FROM [{table}]").fetchall()
            cols = [d[0] for d in c.execute(f"SELECT * FROM [{table}] LIMIT 0").description] if not rows else list(rows[0].keys())
        print(f"\n  {clr('▶ ' + table, B, T)}  {clr(str(len(rows))+' rows', DIM)}")
        print_table(cols, rows)


def screen_sql(sql):
    try:
        with get_conn() as c:
            cur = c.execute(sql)
            c.commit()
            if cur.description:
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                header(f"SQL Result  ({len(rows)} rows)")
                print_table(cols, rows)
            else:
                success(f"Query OK. Rows affected: {cur.rowcount}")
    except sqlite3.Error as e:
        error(str(e))


def screen_add():
    header("Add Record (Guided)")
    print(f"""
  What do you want to add?
  {clr('1', T)} User      (creates a login account)
  {clr('2', T)} Doctor    (links to a DOCTOR user)
  {clr('3', T)} Patient   (links to a PATIENT user)
  {clr('4', T)} Clinic
  {clr('5', T)} Roster    (doctor schedule)
  {clr('b', T)} Back
""")
    choice = input(f"  {clr('>', T)} ").strip()

    if choice == '1':
        _add_user()
    elif choice == '2':
        _add_doctor()
    elif choice == '3':
        _add_patient()
    elif choice == '4':
        _add_clinic()
    elif choice == '5':
        _add_roster()
    elif choice == 'b':
        return
    else:
        warn("Invalid choice.")


def _add_user():
    header("Add User")
    username = input(f"  Username       : ").strip()
    password = input(f"  Password       : ").strip()
    role     = input(f"  Role (ADMIN/DOCTOR/PATIENT): ").strip().upper()

    if not username or not password:
        error("Username and password are required.")
        return
    if role not in ('ADMIN', 'DOCTOR', 'PATIENT'):
        error("Role must be ADMIN, DOCTOR, or PATIENT.")
        return
    try:
        with get_conn() as c:
            c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                      (username, generate_password_hash(password), role))
            c.commit()
        success(f"User '{username}' added with role {role}.")
    except sqlite3.IntegrityError:
        error(f"Username '{username}' already exists.")


def _add_doctor():
    header("Add Doctor")
    # Show DOCTOR users not yet linked
    with get_conn() as c:
        users = c.execute("""
            SELECT u.user_id, u.username FROM users u
            WHERE u.role='DOCTOR'
            AND u.user_id NOT IN (SELECT user_id FROM doctors)
        """).fetchall()

    if not users:
        warn("No unlinked DOCTOR-role users found.")
        info("First add a user with role=DOCTOR using option 1, then come back here.")
        return

    print(f"\n  {clr('Available DOCTOR users:', B)}")
    for u in users:
        print(f"    {clr(u['user_id'], T)}  {u['username']}")

    try:
        uid = int(input(f"\n  user_id to link : ").strip())
    except ValueError:
        error("Invalid user_id.")
        return

    name  = input(f"  Doctor name     : ").strip()
    spec  = input(f"  Speciality      : ").strip()
    phone = input(f"  Phone (optional): ").strip()
    email = input(f"  Email (optional): ").strip()

    if not name or not spec:
        error("Name and Speciality are required.")
        return

    with get_conn() as c:
        c.execute("INSERT INTO doctors (user_id,name,speciality,phone,email) VALUES (?,?,?,?,?)",
                  (uid, name, spec, phone, email))
        c.commit()
    success(f"Doctor '{name}' added.")


def _add_patient():
    header("Add Patient")
    with get_conn() as c:
        users = c.execute("""
            SELECT u.user_id, u.username FROM users u
            WHERE u.role='PATIENT'
            AND u.user_id NOT IN (SELECT user_id FROM patients)
        """).fetchall()

    if not users:
        warn("No unlinked PATIENT-role users found.")
        info("First add a user with role=PATIENT using option 1, then come back here.")
        return

    print(f"\n  {clr('Available PATIENT users:', B)}")
    for u in users:
        print(f"    {clr(u['user_id'], T)}  {u['username']}")

    try:
        uid = int(input(f"\n  user_id to link : ").strip())
    except ValueError:
        error("Invalid user_id.")
        return

    name = input(f"  Patient name    : ").strip()
    if not name:
        error("Name is required.")
        return

    with get_conn() as c:
        c.execute("INSERT INTO patients (user_id,name) VALUES (?,?)", (uid, name))
        c.commit()
    success(f"Patient '{name}' added.")


def _add_clinic():
    header("Add Clinic")
    name    = input(f"  Clinic name     : ").strip()
    address = input(f"  Address         : ").strip()
    phone   = input(f"  Phone           : ").strip()
    if not name:
        error("Clinic name is required.")
        return
    with get_conn() as c:
        c.execute("INSERT INTO clinics (clinic_name,address,phone) VALUES (?,?,?)",
                  (name, address, phone))
        c.commit()
    success(f"Clinic '{name}' added.")


def _add_roster():
    header("Add Roster Entry")
    with get_conn() as c:
        doctors = c.execute("SELECT doctor_id, name FROM doctors").fetchall()
        clinics = c.execute("SELECT clinic_id, clinic_name FROM clinics").fetchall()

    if not doctors or not clinics:
        error("Need at least one doctor and one clinic first.")
        return

    print(f"\n  {clr('Doctors:', B)}")
    for d in doctors:
        print(f"    {clr(d['doctor_id'], T)}  {d['name']}")
    try:
        did = int(input(f"\n  doctor_id : ").strip())
    except ValueError:
        error("Invalid doctor_id.")
        return

    print(f"\n  {clr('Clinics:', B)}")
    for c_ in clinics:
        print(f"    {clr(c_['clinic_id'], T)}  {c_['clinic_name']}")
    try:
        cid = int(input(f"\n  clinic_id : ").strip())
    except ValueError:
        error("Invalid clinic_id.")
        return

    print(f"\n  Days: Mon Tue Wed Thu Fri Sat Sun")
    day   = input(f"  Day       : ").strip().capitalize()[:3]
    start = input(f"  Start (HH:MM): ").strip()
    end   = input(f"  End   (HH:MM): ").strip()

    valid_days = ('Mon','Tue','Wed','Thu','Fri','Sat','Sun')
    if day not in valid_days:
        error(f"Day must be one of {valid_days}")
        return
    if start >= end:
        error("Start time must be before end time.")
        return

    with get_conn() as c:
        c.execute("""INSERT INTO doctor_roster (doctor_id,clinic_id,day_of_week,start_time,end_time)
                     VALUES (?,?,?,?,?)""", (did, cid, day, start, end))
        c.commit()
    success(f"Roster entry added: doctor {did} @ clinic {cid} on {day} {start}–{end}.")


def screen_delete(table, pk_val):
    with get_conn() as c:
        exists = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            error(f"Table '{table}' not found.")
            return
        # Find PK column
        pk_info = c.execute(f"PRAGMA table_info([{table}])").fetchall()
        pk_col  = next((r['name'] for r in pk_info if r['pk'] == 1), None)
        if not pk_col:
            error("Cannot find primary key column for this table.")
            return
        row = c.execute(f"SELECT * FROM [{table}] WHERE [{pk_col}]=?", (pk_val,)).fetchone()
        if not row:
            error(f"No row with {pk_col}={pk_val} in {table}.")
            return

        print(f"\n  {clr('About to delete:', RD)}")
        print_table(list(row.keys()), [list(row)])
        confirm = input(f"  {clr('Type YES to confirm: ', YL)}").strip()
        if confirm == 'YES':
            c.execute(f"DELETE FROM [{table}] WHERE [{pk_col}]=?", (pk_val,))
            c.commit()
            success(f"Row deleted from {table}.")
        else:
            info("Cancelled.")

# ─── REPL ─────────────────────────────────────────────────────────────────────

def main():
    while True:
        screen_home()
        raw = input(f"  {clr('dbview', T)}{clr('>', GY)} ").strip()
        if not raw:
            continue

        parts = raw.split(None, 1)
        cmd   = parts[0].lower()
        rest  = parts[1] if len(parts) > 1 else ''

        if cmd == 'q':
            print(f"\n  {clr('Bye!', GR)}\n")
            break

        elif cmd == 'v':
            if not rest:
                error("Usage: v <table_name>  or  v all")
                input(f"  {clr('Press Enter...', DIM)}")
            elif rest.strip().lower() == 'all':
                screen_view_all()
                input(f"  {clr('Press Enter to go back...', DIM)}")
            else:
                screen_view(rest.strip())
                input(f"  {clr('Press Enter to go back...', DIM)}")

        elif cmd == 's':
            if not rest:
                error("Usage: s <SQL statement>")
                input(f"  {clr('Press Enter...', DIM)}")
            else:
                screen_sql(rest.strip())
                input(f"  {clr('Press Enter to go back...', DIM)}")

        elif cmd == 'a':
            screen_add()
            input(f"\n  {clr('Press Enter to go back...', DIM)}")

        elif cmd == 'd':
            d_parts = rest.split()
            if len(d_parts) < 2:
                error("Usage: d <table> <id>")
                input(f"  {clr('Press Enter...', DIM)}")
            else:
                screen_delete(d_parts[0], d_parts[1])
                input(f"\n  {clr('Press Enter to go back...', DIM)}")

        else:
            warn(f"Unknown command: '{cmd}'. Use v, s, a, d, or q.")
            input(f"  {clr('Press Enter...', DIM)}")


if __name__ == '__main__':
    main()