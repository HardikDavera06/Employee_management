"""
Migration helper: copies data from an existing SQLite DB file to the configured MySQL instance.

Usage:
    python -m scripts.migrate_sqlite_to_mysql

This script expects `config.DB['mysql']` to contain proper connection details and attempts to create all tables before migrating.
"""
from pathlib import Path
import sqlite3
import sys
from database_manager import DatabaseManager
from config import DB

SQLITE_DB = Path('employee_system.db')


def migrate():
    if not SQLITE_DB.exists():
        print(f"No SQLite DB found at {SQLITE_DB}; nothing to migrate.")
        return

    # Connect to sqlite source
    sconn = sqlite3.connect(SQLITE_DB)
    sconn.row_factory = sqlite3.Row
    scur = sconn.cursor()

    # Connect to MySQL target via DatabaseManager
    try:
        target_db = DatabaseManager()
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")
        sys.exit(1)

    # Helper fn to run a list of rows into a target SQL with %s placeholders
    def bulk_insert(sql, rows):
        if not rows:
            return
        for r in rows:
            params = tuple(r[k] for k in r.keys())
            try:
                target_db.execute(sql, params)
            except Exception as e:
                print("Warning: insert row failed:", e)

    print("Migrating employees...")
    scur.execute("SELECT * FROM employees")
    rows = [dict(r) for r in scur.fetchall()]
    insert_sql = "INSERT IGNORE INTO employees (id, name, email, phone, department, role, password, salary) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    bulk_insert(insert_sql, rows)

    print("Migrating leaves...")
    scur.execute("SELECT * FROM leaves")
    rows = [dict(r) for r in scur.fetchall()]
    insert_sql = "INSERT IGNORE INTO leaves (id, emp_id, emp_name, leave_type, start_date, end_date, reason, status, applied_date, duration_type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    bulk_insert(insert_sql, rows)

    print("Migrating payroll_records...")
    scur.execute("SELECT * FROM payroll_records")
    rows = [dict(r) for r in scur.fetchall()]
    insert_sql = "INSERT IGNORE INTO payroll_records (id, emp_id, month, base_salary, overtime_hours, overtime_rate, bonus, other_deductions, leave_deduction, net_salary, generated_on, slip_path) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    bulk_insert(insert_sql, rows)

    print("Migrating salary_assignments...")
    scur.execute("SELECT * FROM salary_assignments")
    rows = [dict(r) for r in scur.fetchall()]
    # If the old DB doesn't have a 'month' column, we'll set a default '0000-00' placeholder
    insert_sql = "INSERT IGNORE INTO salary_assignments (id, emp_id, month, assigned_salary, assigned_on, assigned_by) VALUES (%s, %s, %s, %s, %s, %s)"
    if rows:
        for r in rows:
            # Some legacy SQLite DB may not have a month property; default to placeholder
            month_val = r.get('month') or '0000-00'
            params = (
                r.get('id'),
                r.get('emp_id'),
                month_val,
                r.get('assigned_salary'),
                r.get('assigned_on'),
                r.get('assigned_by'),
            )
            try:
                target_db.execute(insert_sql, params)
            except Exception as e:
                print("Warning: insert row failed:", e)

    print("Migrating salary_corrections...")
    scur.execute("SELECT * FROM salary_corrections")
    rows = [dict(r) for r in scur.fetchall()]
    insert_sql = "INSERT IGNORE INTO salary_corrections (id, emp_id, month, description, submitted_on, status, assignment_id, payroll_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    bulk_insert(insert_sql, rows)

    print("Migration completed. Please verify data in MySQL.")
    # Optionally rename backup
    try:
        SQLITE_DB.rename(SQLITE_DB.with_suffix('.db.bak'))
        print(f"Renamed local sqlite DB to {SQLITE_DB.with_suffix('.db.bak')}")
    except Exception as e:
        print("Could not rename sqlite DB: ", e)

    # Attempt to deduplicate salary_assignments on the target if the engine is mysql
    try:
        if target_db.engine == 'mysql':
            print('Checking duplicate salary_assignments on MySQL target...')
            dup_rows = target_db.query("SELECT emp_id, month, COUNT(*) AS c FROM salary_assignments GROUP BY emp_id, month HAVING c > 1")
            if dup_rows:
                print('Found duplicates; removing older entries and keeping the most recent assigned_on per emp/month')
                # For each duplicate set, keep the latest assigned_on and delete others (simple strategy)
                for r in dup_rows:
                    emp_id = r['emp_id']
                    month = r['month']
                    # keep the one with max assigned_on
                    keep = target_db.query("SELECT id FROM salary_assignments WHERE emp_id = %s AND month = %s ORDER BY assigned_on DESC LIMIT 1", (emp_id, month))
                    if keep:
                        keep_id = keep[0]['id']
                        # delete others
                        target_db.execute("DELETE FROM salary_assignments WHERE emp_id = %s AND month = %s AND id <> %s", (emp_id, month, keep_id))
            # Now attempt to add unique index (if not present)
            try:
                cur = target_db._get_cursor()
                cur.execute("ALTER TABLE salary_assignments ADD UNIQUE INDEX unique_emp_month (emp_id, month)")
            except Exception:
                # maybe it already exists; ignore
                pass
    except Exception as e:
        print('Warning: dedup/unique-index step failed:', e)


if __name__ == '__main__':
    migrate()
