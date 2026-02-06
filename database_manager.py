from typing import Any, Optional, Sequence
import re
import json
import sqlite3
from pathlib import Path
from config import DB

try:
    import mysql.connector as mysql_connector  # type: ignore
except Exception:
    mysql_connector = None


class DatabaseManager:
    """Database manager that prefers MySQL and falls back to SQLite.

    Light, engine-aware API with `query`, `execute`, and `execute_and_fetch`.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.conn = None
        self.engine = None
        self._param_style = "format"

        allow_fallback = DB.get("allow_sqlite_fallback", False)
        if mysql_connector is not None and DB.get("mysql"):
            cfg = DB.get("mysql", {})
            try:
                self.conn = mysql_connector.connect(
                    host=cfg.get("host", "localhost"),
                    port=cfg.get("port", 3306),
                    user=cfg.get("user", "root"),
                    password=cfg.get("password", ""),
                    database=cfg.get("database", "employee_db"),
                )
                self.engine = "mysql"
                self._param_style = "format"
            except Exception:
                if allow_fallback:
                    self._init_sqlite(db_path)
                else:
                    raise
        else:
            # No mysql config in DB or mysql library not available
            if allow_fallback:
                self._init_sqlite(db_path)
            else:
                raise RuntimeError("MySQL is configured but not available and SQLite fallback is disabled")

        if self.conn is None:
            raise RuntimeError("No DB connection available")

        self._init_schema()
        self._ensure_default_admin()

    def _init_sqlite(self, db_path: Optional[str] = None) -> None:
        self.engine = "sqlite"
        if db_path is None:
            # prefer explicit sqlite path in config, else keep existing project DB if present
            db_path = DB.get("sqlite", {}).get("path") or ("employee_system.db" if Path("employee_system.db").exists() else "employee_system_local.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._param_style = "qmark"

    def _get_cursor(self, dict_cursor: bool = False):
        if self.engine == "mysql":
            return self.conn.cursor(dictionary=dict_cursor)
        return self.conn.cursor()

    def _init_schema(self) -> None:
        cur = self._get_cursor()
        if self.engine == "mysql":
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS employees (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    phone VARCHAR(64),
                    department VARCHAR(128),
                    role VARCHAR(64) NOT NULL,
                    password VARCHAR(128) NOT NULL,
                    salary DECIMAL(12,2) DEFAULT 0
                ) ENGINE=InnoDB;
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS employees (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    phone TEXT,
                    department TEXT,
                    role TEXT NOT NULL,
                    password TEXT NOT NULL,
                    salary REAL DEFAULT 0
                )
                """
            )
        if self.engine == "mysql":
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS salary_assignments (
                    id VARCHAR(36) PRIMARY KEY,
                    emp_id VARCHAR(36) NOT NULL,
                    month VARCHAR(7) NOT NULL,
                    assigned_salary DECIMAL(12,2) NOT NULL,
                    assigned_on DATETIME NOT NULL,
                    assigned_by VARCHAR(36),
                    bonus DECIMAL(12,2) DEFAULT 0
                ) ENGINE=InnoDB;
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS salary_assignments (
                    id TEXT PRIMARY KEY,
                    emp_id TEXT NOT NULL,
                    month TEXT NOT NULL,
                    assigned_salary REAL NOT NULL,
                    assigned_on TEXT NOT NULL,
                    assigned_by TEXT,
                    bonus REAL DEFAULT 0
                )
                """
            )
        if self.engine == "mysql":
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS salary_corrections (
                    id VARCHAR(36) PRIMARY KEY,
                    emp_id VARCHAR(36) NOT NULL,
                    month VARCHAR(7) NOT NULL,
                    description TEXT,
                    submitted_on DATETIME NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    assignment_id VARCHAR(36) NULL,
                    payroll_id VARCHAR(36) NULL,
                    admin_notes TEXT NULL
                ) ENGINE=InnoDB;
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS salary_corrections (
                    id TEXT PRIMARY KEY,
                    emp_id TEXT NOT NULL,
                    month TEXT NOT NULL,
                    description TEXT,
                    submitted_on TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assignment_id TEXT NULL,
                    payroll_id TEXT NULL,
                    admin_notes TEXT NULL
                )
                """
            )
        # Also ensure leaves and payroll_records tables exist (used across app)
        if self.engine == "mysql":
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS leaves (
                    id VARCHAR(36) PRIMARY KEY,
                    emp_id VARCHAR(36) NOT NULL,
                    emp_name VARCHAR(255) NOT NULL,
                    leave_type VARCHAR(64) NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    reason TEXT,
                    status VARCHAR(32) NOT NULL,
                    applied_date DATETIME NOT NULL,
                    duration_type VARCHAR(64) DEFAULT 'Full Day'
                ) ENGINE=InnoDB;
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS leaves (
                    id TEXT PRIMARY KEY,
                    emp_id TEXT NOT NULL,
                    emp_name TEXT NOT NULL,
                    leave_type TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    reason TEXT,
                    status TEXT NOT NULL,
                    applied_date TEXT NOT NULL,
                    duration_type TEXT DEFAULT 'Full Day'
                )
                """
            )
        if self.engine == "mysql":
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS payroll_records (
                    id VARCHAR(36) PRIMARY KEY,
                    emp_id VARCHAR(36) NOT NULL,
                    month VARCHAR(7) NOT NULL,
                    base_salary DECIMAL(12,2) NOT NULL,
                    overtime_hours DECIMAL(8,2) DEFAULT 0,
                    overtime_rate DECIMAL(12,2) DEFAULT 0,
                    bonus DECIMAL(12,2) DEFAULT 0,
                    other_deductions DECIMAL(12,2) DEFAULT 0,
                    leave_deduction DECIMAL(12,2) DEFAULT 0,
                    net_salary DECIMAL(12,2) NOT NULL,
                    generated_on DATETIME NOT NULL,
                    slip_path VARCHAR(1024)
                ) ENGINE=InnoDB;
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS payroll_records (
                    id TEXT PRIMARY KEY,
                    emp_id TEXT NOT NULL,
                    month TEXT NOT NULL,
                    base_salary REAL NOT NULL,
                    overtime_hours REAL DEFAULT 0,
                    overtime_rate REAL DEFAULT 0,
                    bonus REAL DEFAULT 0,
                    other_deductions REAL DEFAULT 0,
                    leave_deduction REAL DEFAULT 0,
                    net_salary REAL NOT NULL,
                    generated_on TEXT NOT NULL,
                    slip_path TEXT
                )
                """
            )
        self.conn.commit()
        # Ensure required columns exist (with engine-specific type definitions)
        if self.engine == "mysql":
            self._ensure_column("employees", "salary", "DECIMAL(12,2) DEFAULT 0")
            self._ensure_column("salary_corrections", "assignment_id", "VARCHAR(36) NULL")
            self._ensure_column("salary_corrections", "payroll_id", "VARCHAR(36) NULL")
            self._ensure_column("salary_corrections", "admin_notes", "TEXT NULL")
            self._ensure_column("salary_corrections", "rejection_reason", "TEXT NULL")
            self._ensure_column("salary_assignments", "month", "VARCHAR(7) DEFAULT '0000-00' NOT NULL")
            self._ensure_column("salary_assignments", "bonus", "DECIMAL(12,2) DEFAULT 0")
        else:
            self._ensure_column("employees", "salary", "REAL DEFAULT 0")
            self._ensure_column("salary_corrections", "assignment_id", "TEXT NULL")
            self._ensure_column("salary_corrections", "payroll_id", "TEXT NULL")
            self._ensure_column("salary_corrections", "admin_notes", "TEXT NULL")
            self._ensure_column("salary_corrections", "rejection_reason", "TEXT NULL")
            self._ensure_column("salary_assignments", "month", "TEXT DEFAULT '0000-00' NOT NULL")
            self._ensure_column("salary_assignments", "bonus", "REAL DEFAULT 0")
        self._ensure_unique_emp_month_index()

    def _ensure_default_admin(self) -> None:
        row = self.execute_and_fetch("SELECT COUNT(*) AS c FROM employees")
        try:
            count = int(row.get("c", 0)) if row else 0
        except Exception:
            try:
                count = int(row[0])
            except Exception:
                count = 0
        if count == 0:
            if self.engine == "mysql":
                sql = "INSERT IGNORE INTO employees (id, name, email, phone, department, role, password, salary) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            else:
                sql = "INSERT OR IGNORE INTO employees (id, name, email, phone, department, role, password, salary) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            self.execute(sql, ("EMP001", "Admin", "admin@company.com", "1234567890", "Management", "admin", "admin123", 60000))

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        cur = self._get_cursor()
        if self.engine == "mysql":
            cfg = DB.get("mysql", {})
            dbname = cfg.get("database") or getattr(self.conn, "database", None)
            if dbname:
                sql = "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s AND column_name = %s"
                params = (dbname, table, column)
            else:
                sql = "SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = %s"
                params = (table, column)
            try:
                cur.execute(sql, params)
                res = cur.fetchone()
            except Exception:
                res = None
            if not res:
                cur2 = self._get_cursor()
                cur2.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                self.conn.commit()
        else:
            cur.execute(f"PRAGMA table_info({table})")
            info = cur.fetchall()
            cols = [r[1] if not hasattr(r, "keys") else r["name"] for r in info]
            if column not in cols:
                cur2 = self._get_cursor()
                cur2.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                self.conn.commit()

    def _ensure_unique_emp_month_index(self) -> None:
        cur = self._get_cursor()
        if self.engine == "mysql":
            try:
                # detect duplicates first; if duplicates exist, remove them keeping latest assigned_on
                dup_rows = self.query("SELECT emp_id, month, COUNT(*) AS c FROM salary_assignments GROUP BY emp_id, month HAVING c > 1")
                if dup_rows:
                    for r in dup_rows:
                        emp_id = r.get("emp_id")
                        month = r.get("month")
                        keep = self.query("SELECT id FROM salary_assignments WHERE emp_id = %s AND month = %s ORDER BY assigned_on DESC LIMIT 1", (emp_id, month))
                        if keep:
                            keep_id = keep[0].get("id")
                            self.execute("DELETE FROM salary_assignments WHERE emp_id = %s AND month = %s AND id <> %s", (emp_id, month, keep_id))
                cur.execute("ALTER TABLE salary_assignments ADD UNIQUE INDEX unique_emp_month (emp_id, month)")
                self.conn.commit()
            except Exception:
                pass
        else:
            try:
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_emp_month ON salary_assignments(emp_id, month)")
                self.conn.commit()
            except Exception:
                pass

    def query(self, sql: str, params: Sequence[Any] | None = None):
        cur = self._get_cursor(dict_cursor=True)
        sql, params = self._convert_query(sql, params)
        cur.execute(sql, params or [])
        return cur.fetchall()

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> None:
        cur = self._get_cursor()
        sql, params = self._convert_query(sql, params)
        cur.execute(sql, params or [])
        self.conn.commit()

    def execute_and_fetch(self, sql: str, params: Sequence[Any] | None = None) -> Optional[dict]:
        cur = self._get_cursor(dict_cursor=True)
        sql, params = self._convert_query(sql, params)
        cur.execute(sql, params or [])
        return cur.fetchone()

    def _convert_query(self, sql: str, params: Sequence[Any] | None = None):
        if self.engine == "mysql":
            sql = re.sub(r":(\w+)", lambda m: f"%({m.group(1)})s", sql)
            if isinstance(params, (list, tuple)):
                if "?" in sql:
                    sql = sql.replace("?", "%s")
            return sql, params
        if params is None:
            sql = re.sub(r"%\((\w+)\)s", lambda m: f":{m.group(1)}", sql)
            sql = sql.replace("%s", "?")
            return sql, None
        if isinstance(params, dict):
            sql = re.sub(r"%\((\w+)\)s", lambda m: f":{m.group(1)}", sql)
            return sql, params
        if isinstance(params, (list, tuple)):
            if "%s" in sql:
                sql = sql.replace("%s", "?")
            return sql, params
        return sql, params

    def close(self) -> None:
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

    def _migrate_corrections_from_json(self) -> None:
        json_file = Path("salary_corrections.json")
        try:
            cur = self._get_cursor()
            cur.execute("SELECT COUNT(*) AS c FROM salary_corrections")
            row = cur.fetchone()
            if row is None:
                count = 0
            else:
                try:
                    count = int(row.get("c", 0))
                except Exception:
                    try:
                        count = int(row[0])
                    except Exception:
                        count = 0
        except Exception:
            count = 0

        if count > 0 or not json_file.exists():
            return
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        if self.engine == "mysql":
            sql = "INSERT IGNORE INTO salary_corrections (id, emp_id, month, description, submitted_on, status) VALUES (%s, %s, %s, %s, %s, %s)"
        else:
            sql = "INSERT OR IGNORE INTO salary_corrections (id, emp_id, month, description, submitted_on, status) VALUES (?, ?, ?, ?, ?, ?)"
        for entry in data:
            self.execute(
                sql,
                (
                    entry.get("id"),
                    entry.get("emp_id"),
                    entry.get("month"),
                    entry.get("description"),
                    entry.get("submitted_on"),
                    entry.get("status", "Pending"),
                ),
            )
        try:
            json_file.rename(json_file.with_suffix(".json.bak"))
        except Exception:
            pass
