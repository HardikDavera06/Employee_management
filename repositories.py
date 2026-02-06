from __future__ import annotations

from typing import Dict, List, Optional
import hashlib

from database_manager import DatabaseManager


class EmployeeRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self._cache: Optional[List[Dict]] = None

    def list_employees(self, force_refresh: bool = False) -> List[Dict]:
        if self._cache is None or force_refresh:
            rows = self.db.query("SELECT * FROM employees ORDER BY id")
            self._cache = [dict(row) for row in rows]
        # Return a shallow copy so callers do not accidentally mutate cache
        return list(self._cache)

    def invalidate(self) -> None:
        self._cache = None

    def generate_employee_id(self) -> str:
        if self.db.engine == "mysql":
            row = self.db.execute_and_fetch(
                "SELECT MAX(CAST(SUBSTR(id, 4) AS UNSIGNED)) AS max_num FROM employees WHERE id LIKE 'EMP%'"
            )
        else:
            row = self.db.execute_and_fetch(
                "SELECT MAX(CAST(SUBSTR(id, 4) AS INTEGER)) AS max_num FROM employees WHERE id LIKE 'EMP%'"
            )
        next_num = ((row["max_num"] if row else None) or 0) + 1
        return f"EMP{str(next_num).zfill(3)}"

    def add_employee(self, employee: Dict) -> None:
        # Hash the password before storing
        hashed_password = hashlib.sha256(employee["password"].encode()).hexdigest()
        self.db.execute(
            """
            INSERT INTO employees (id, name, email, phone, department, role, password, salary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                employee["id"],
                employee["name"],
                employee["email"],
                employee.get("phone"),
                employee.get("department"),
                employee["role"],
                hashed_password,
                employee.get("salary", 0),
            ),
        )
        self.invalidate()

    def update_employee(self, emp_id: str, updates: Dict) -> None:
        self.db.execute(
            """
            UPDATE employees
            SET name = %s,
                email = %s,
                phone = %s,
                department = %s,
                role = %s,
                salary = %s
            WHERE id = %s
            """,
            (
                updates["name"],
                updates["email"],
                updates.get("phone"),
                updates.get("department"),
                updates["role"],
                updates.get("salary", 0),
                emp_id,
            ),
        )
        self.invalidate()

    def delete_employee(self, emp_id: str) -> None:
        self.db.execute("DELETE FROM employees WHERE id = %s", (emp_id,))
        self.invalidate()

    def get_employee(self, emp_id: str) -> Optional[Dict]:
        rows = self.db.query("SELECT * FROM employees WHERE id = %s", (emp_id,))
        return dict(rows[0]) if rows else None

    def authenticate(self, emp_id: str, password: str) -> Optional[Dict]:
        row = self.db.execute_and_fetch(
            "SELECT * FROM employees WHERE id = %s AND password = %s", (emp_id, password)
        )
        return dict(row) if row else None

    def email_exists(self, email: str, exclude_emp_id: Optional[str] = None) -> bool:
        """Check if email already exists in the system."""
        if exclude_emp_id:
            rows = self.db.query(
                "SELECT id FROM employees WHERE email = %s AND id != %s", 
                (email, exclude_emp_id)
            )
        else:
            rows = self.db.query(
                "SELECT id FROM employees WHERE email = %s", 
                (email,)
            )
        return len(rows) > 0

    def phone_exists(self, phone: str, exclude_emp_id: Optional[str] = None) -> bool:
        """Check if phone already exists in the system."""
        if exclude_emp_id:
            rows = self.db.query(
                "SELECT id FROM employees WHERE phone = %s AND id != %s", 
                (phone, exclude_emp_id)
            )
        else:
            rows = self.db.query(
                "SELECT id FROM employees WHERE phone = %s", 
                (phone,)
            )
        return len(rows) > 0


class LeaveRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self._cache: Optional[List[Dict]] = None

    def list_leaves(
        self, force_refresh: bool = False, limit: Optional[int] = None
    ) -> List[Dict]:
        if self._cache is None or force_refresh:
            rows = self.db.query("SELECT * FROM leaves ORDER BY applied_date DESC")
            self._cache = [dict(row) for row in rows]
        leaves = list(self._cache)
        if limit is not None:
            leaves = leaves[:limit]
        return leaves

    def invalidate(self) -> None:
        self._cache = None

    def generate_leave_id(self) -> str:
        if self.db.engine == "mysql":
            row = self.db.execute_and_fetch(
                "SELECT MAX(CAST(SUBSTR(id, 3) AS UNSIGNED)) AS max_num FROM leaves WHERE id LIKE 'LV%'"
            )
        else:
            row = self.db.execute_and_fetch(
                "SELECT MAX(CAST(SUBSTR(id, 3) AS INTEGER)) AS max_num FROM leaves WHERE id LIKE 'LV%'"
            )
        next_num = ((row["max_num"] if row else None) or 0) + 1
        return f"LV{str(next_num).zfill(3)}"

    def add_leave(self, leave: Dict) -> None:
        self.db.execute(
            """
            INSERT INTO leaves (id, emp_id, emp_name, leave_type, start_date, end_date, reason, status, applied_date, duration_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                leave["id"],
                leave["emp_id"],
                leave["emp_name"],
                leave["leave_type"],
                leave["start_date"],
                leave["end_date"],
                leave.get("reason"),
                leave["status"],
                leave["applied_date"],
                leave.get("duration_type", "Full Day"),
            ),
        )
        self.invalidate()

    def update_leave(self, leave_id: str, updates: Dict) -> None:
        self.db.execute(
            """
            UPDATE leaves
            SET leave_type = %s,
                start_date = %s,
                end_date = %s,
                reason = %s,
                duration_type = %s
            WHERE id = %s
            """,
            (
                updates["leave_type"],
                updates["start_date"],
                updates["end_date"],
                updates["reason"],
                updates["duration_type"],
                leave_id,
            ),
        )
        self.invalidate()

    def update_status(self, leave_id: str, status: str) -> None:
        self.db.execute("UPDATE leaves SET status = %s WHERE id = %s", (status, leave_id))
        self.invalidate()

    def get_leave(self, leave_id: str) -> Optional[Dict]:
        rows = self.db.query("SELECT * FROM leaves WHERE id = %s", (leave_id,))
        return dict(rows[0]) if rows else None

    def leaves_for_employee(self, emp_id: str) -> List[Dict]:
        return [leave for leave in self.list_leaves() if leave["emp_id"] == emp_id]


class PayrollRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def generate_payroll_id(self) -> str:
        if self.db.engine == "mysql":
            row = self.db.execute_and_fetch(
                "SELECT MAX(CAST(SUBSTR(id, 4) AS UNSIGNED)) AS max_num FROM payroll_records WHERE id LIKE 'PAY%'"
            )
        else:
            row = self.db.execute_and_fetch(
                "SELECT MAX(CAST(SUBSTR(id, 4) AS INTEGER)) AS max_num FROM payroll_records WHERE id LIKE 'PAY%'"
            )
        next_num = ((row["max_num"] if row else None) or 0) + 1
        return f"PAY{str(next_num).zfill(4)}"

    def save_record(self, record: Dict) -> None:
        self.db.execute(
            """
            INSERT INTO payroll_records (
                id,
                emp_id,
                month,
                base_salary,
                overtime_hours,
                overtime_rate,
                bonus,
                other_deductions,
                leave_deduction,
                net_salary,
                generated_on,
                slip_path
            ) VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                record["id"],
                record["emp_id"],
                record["month"],
                record["base_salary"],
                record.get("overtime_hours", 0),
                record.get("overtime_rate", 0),
                record.get("bonus", 0),
                record.get("other_deductions", 0),
                record.get("leave_deduction", 0),
                record["net_salary"],
                record["generated_on"],
                record.get("slip_path"),
            ),
        )

    def list_records(self, emp_id: Optional[str] = None) -> List[Dict]:
        if emp_id:
            rows = self.db.query(
                "SELECT * FROM payroll_records WHERE emp_id = %s ORDER BY generated_on DESC",
                (emp_id,),
            )
        else:
            rows = self.db.query("SELECT * FROM payroll_records ORDER BY generated_on DESC")
        return [dict(row) for row in rows]

    def update_record(self, record_id: str, updates: Dict) -> None:
        # Build dynamic SET clause
        cols = []
        params = []
        for k, v in updates.items():
            cols.append(f"{k} = %s")
            params.append(v)
        params.append(record_id)
        sql = f"UPDATE payroll_records SET {', '.join(cols)} WHERE id = %s"
        self.db.execute(sql, tuple(params))


class CorrectionRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def generate_correction_id(self) -> str:
        if self.db.engine == "mysql":
            row = self.db.execute_and_fetch(
                "SELECT MAX(CAST(SUBSTR(id, 4) AS UNSIGNED)) AS max_num FROM salary_corrections WHERE id LIKE 'REQ%'"
            )
        else:
            row = self.db.execute_and_fetch(
                "SELECT MAX(CAST(SUBSTR(id, 4) AS INTEGER)) AS max_num FROM salary_corrections WHERE id LIKE 'REQ%'"
            )
        next_num = ((row["max_num"] if row else None) or 0) + 1
        return f"REQ{str(next_num).zfill(4)}"

    def add_correction(self, correction: Dict) -> None:
        # Accept optional keys assignment_id and payroll_id in correction dict
        keys = ["id", "emp_id", "month", "description", "submitted_on", "status"]
        optional = []
        if "assignment_id" in correction:
            keys.append("assignment_id")
            optional.append("assignment_id")
        if "payroll_id" in correction:
            keys.append("payroll_id")
            optional.append("payroll_id")

        cols = ", ".join(keys)
        vals = ", ".join(["%s" for _ in keys])
        sql = f"INSERT INTO salary_corrections ({cols}) VALUES ({vals})"
        params = tuple(correction.get(k) for k in keys)
        self.db.execute(sql, params)


    def list_corrections(self, emp_id: Optional[str] = None) -> List[Dict]:
        # Allow filtering by emp_id, status, and date range via parameters set in `kwargs`
        # To keep a backward-compatible signature, accept only emp_id here but allow other filters via attributes.
        rows = self.db.query("SELECT * FROM salary_corrections ORDER BY submitted_on DESC")
        return [dict(row) for row in rows]

    def list_corrections_filtered(self, emp_id: Optional[str] = None, status: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        clauses = []
        params = []
        if emp_id:
            clauses.append("emp_id = %s")
            params.append(emp_id)
        if status:
            clauses.append("status = %s")
            params.append(status)
        if start_date:
            clauses.append("submitted_on >= %s")
            params.append(start_date + " 00:00:00")
        if end_date:
            clauses.append("submitted_on <= %s")
            params.append(end_date + " 23:59:59")

        sql = "SELECT * FROM salary_corrections"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY submitted_on DESC"
        rows = self.db.query(sql, tuple(params))
        return [dict(row) for row in rows]

    def get_correction(self, req_id: str) -> Optional[Dict]:
        row = self.db.execute_and_fetch("SELECT * FROM salary_corrections WHERE id = %s", (req_id,))
        return dict(row) if row else None

    def update_status(self, req_id: str, status: str) -> None:
        self.db.execute("UPDATE salary_corrections SET status = %s WHERE id = %s", (status, req_id))

    def reject_correction(self, req_id: str, rejection_reason: str) -> None:
        """Reject a correction request with a reason"""
        self.db.execute(
            "UPDATE salary_corrections SET status = %s, rejection_reason = %s WHERE id = %s",
            ("Rejected", rejection_reason, req_id)
        )

    def approve_correction(self, req_id: str, admin_notes: str) -> None:
        """Approve a correction request with notes"""
        self.db.execute(
            "UPDATE salary_corrections SET status = %s, admin_notes = %s WHERE id = %s",
            ("Resolved", admin_notes, req_id)
        )

    def update_correction(self, req_id: str, updates: Dict) -> None:
        cols = []
        params = []
        for k, v in updates.items():
            cols.append(f"{k} = %s")
            params.append(v)
        params.append(req_id)
        sql = f"UPDATE salary_corrections SET {', '.join(cols)} WHERE id = %s"
        self.db.execute(sql, tuple(params))


class SalaryAssignmentRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def generate_assignment_id(self) -> str:
        if self.db.engine == "mysql":
            row = self.db.execute_and_fetch(
                "SELECT MAX(CAST(SUBSTR(id, 4) AS UNSIGNED)) AS max_num FROM salary_assignments WHERE id LIKE 'ASG%'"
            )
        else:
            row = self.db.execute_and_fetch(
                "SELECT MAX(CAST(SUBSTR(id, 4) AS INTEGER)) AS max_num FROM salary_assignments WHERE id LIKE 'ASG%'"
            )
        next_num = ((row["max_num"] if row else None) or 0) + 1
        return f"ASG{str(next_num).zfill(4)}"

    def add_assignment(self, assignment: Dict) -> None:
        # Enforce one assignment per employee per month at application level as well
        if "month" not in assignment or not assignment["month"]:
            raise ValueError("Assignment record must include a 'month' field in YYYY-MM format")
        exists = self.db.query("SELECT id FROM salary_assignments WHERE emp_id = %s AND month = %s", (assignment["emp_id"], assignment["month"]))
        if exists:
            raise ValueError(f"Employee {assignment['emp_id']} already has an assignment for month {assignment['month']}")
        self.db.execute(
            """
            INSERT INTO salary_assignments (id, emp_id, month, assigned_salary, assigned_on, assigned_by, bonus)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                assignment["id"],
                assignment["emp_id"],
                assignment["month"],
                assignment["assigned_salary"],
                assignment["assigned_on"],
                assignment.get("assigned_by"),
                assignment.get("bonus", 0),
            ),
        )

    def list_assignments(self, emp_id: Optional[str] = None) -> List[Dict]:
        if emp_id:
            rows = self.db.query(
                "SELECT * FROM salary_assignments WHERE emp_id = %s ORDER BY assigned_on DESC",
                (emp_id,),
            )
        else:
            rows = self.db.query("SELECT * FROM salary_assignments ORDER BY assigned_on DESC")
        return [dict(row) for row in rows]

    def list_assignments_for_month(self, month: str) -> List[Dict]:
        rows = self.db.query("SELECT * FROM salary_assignments WHERE month = %s ORDER BY assigned_on DESC", (month,))
        return [dict(row) for row in rows]

    def list_unassigned_employees_for_month(self, month: str) -> List[Dict]:
        # returns employees who do not have an assignment for the given month
        rows = self.db.query("SELECT * FROM employees WHERE id NOT IN (SELECT emp_id FROM salary_assignments WHERE month = %s)", (month,))
        return [dict(row) for row in rows]

    def get_assignment(self, asg_id: str) -> Optional[Dict]:
        row = self.db.execute_and_fetch("SELECT * FROM salary_assignments WHERE id = %s", (asg_id,))
        return dict(row) if row else None

    def delete_assignment(self, asg_id: str) -> None:
        self.db.execute("DELETE FROM salary_assignments WHERE id = %s", (asg_id,))

