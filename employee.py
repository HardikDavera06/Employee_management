"""
Employee Management System - Main Entry Point
Modular employee management system with payroll and leave management.

This module orchestrates the main application and delegates specific functionality to specialized modules:
- admin_dashboard.py: Admin dashboard and employee management features
- employee_dashboard.py: Employee dashboard and leave application features
- employee_salary.py: Salary correction and payslip features
- database_manager.py: Database operations
- repositories.py: Data layer repositories
"""

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, date
import os
import re
from pathlib import Path
from calendar import monthrange
from config import DEFAULT_OVERTIME_RATE
import importlib
import hashlib

# Import modular components
from admin_dashboard import AdminDashboard
from employee_dashboard import EmployeeDashboard
from database_manager import DatabaseManager
from repositories import EmployeeRepository, LeaveRepository, PayrollRepository, CorrectionRepository
from repositories import SalaryAssignmentRepository
from employee_salary import SalaryUI

FPDF = None

def _get_fpdf_class():
    """Lazy load FPDF class to avoid hard dependency."""
    global FPDF
    if FPDF is None:
        try:
            module = importlib.import_module("fpdf")
            FPDF = module.FPDF
        except ImportError as exc:
            raise RuntimeError("FPDF library is not installed. Please run 'pip install fpdf2'.") from exc
    return FPDF


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


class EmployeeManagementSystem:
    """Main application class for the Employee Management System."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Employee Management System")
        self.root.geometry("1000x700")

        # Try to load profile icon
        self.profile_icon = None
        try:
            if os.path.exists("profile_icon.png"):
                self.profile_icon = tk.PhotoImage(file="profile_icon.png")
        except Exception:
            self.profile_icon = None
        
        # Initialize data layer
        self.db = DatabaseManager()
        self.employee_repo = EmployeeRepository(self.db)
        self.leave_repo = LeaveRepository(self.db)
        self.payroll_repo = PayrollRepository(self.db)
        self.correction_repo = CorrectionRepository(self.db)
        self.assignment_repo = SalaryAssignmentRepository(self.db)
        self.salary_ui = SalaryUI(self)

        # Initialize in-memory caches
        self.employees = self.employee_repo.list_employees(force_refresh=True)
        self.leaves = self.leave_repo.list_leaves(force_refresh=True)
        self.current_user = None

        # Initialize modular components
        self.admin_dashboard = AdminDashboard(self)
        self.employee_dashboard = EmployeeDashboard(self)

        # Setup window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Show login screen
        self.show_login_screen()

    # ============================================================================
    # SHARED UTILITY METHODS
    # ============================================================================

    def validate_phone_input(self, new_value: str) -> bool:
        """Validate phone number input (max 10 digits)."""
        if new_value == "":
            return True
        return bool(re.fullmatch(r"\d{0,10}", new_value))

    def _make_stat_card(self, parent, title, value, bg_color, icon="", onclick=None):
        """Create a styled statistics card."""
        card = tk.Frame(parent, bg=bg_color, width=240, height=120, bd=0, relief="ridge")
        card.pack_propagate(False)
        title_lbl = tk.Label(card, text=f"{icon}  {title}", font=("Arial", 12, "bold"), bg=bg_color, fg="white", wraplength=220, justify="left")
        title_lbl.pack(pady=(12, 0), padx=10, anchor="w")
        tk.Label(card, text=value, font=("Arial", 20, "bold"), bg=bg_color, fg="white").pack(pady=(6, 8))
        if onclick is not None:
            card.bind('<Button-1>', lambda e: onclick())
            title_lbl.bind('<Button-1>', lambda e: onclick())
            card.configure(cursor='hand2')
        return card

    def _create_table_with_scroll(self, parent, columns, height: int = 10, enable_xscroll: bool = False):
        """Create a treeview table with scrollbars."""
        frame = tk.Frame(parent, bg="white")
        frame.pack(fill="both", expand=True)
        
        vscroll = tk.Scrollbar(frame, orient="vertical")
        vscroll.pack(side="right", fill="y")
        
        if enable_xscroll:
            xscroll = tk.Scrollbar(frame, orient="horizontal")
            xscroll.pack(side="bottom", fill="x")
            tree = ttk.Treeview(frame, columns=columns, show="headings", yscrollcommand=vscroll.set, xscrollcommand=xscroll.set, height=height)
            xscroll.config(command=tree.xview)
        else:
            xscroll = None
            tree = ttk.Treeview(frame, columns=columns, show="headings", yscrollcommand=vscroll.set, height=height)
        
        vscroll.config(command=tree.yview)
        tree.pack(fill="both", expand=True)
        return frame, tree, vscroll, xscroll

    # ============================================================================
    # DATA MANAGEMENT METHODS
    # ============================================================================

    def refresh_employees(self):
        """Refresh employee cache from database."""
        self.employees = self.employee_repo.list_employees(force_refresh=True)

    def refresh_leaves(self):
        """Refresh leave cache from database."""
        self.leaves = self.leave_repo.list_leaves(force_refresh=True)

    def generate_new_employee_id(self) -> str:
        """Generate a new employee ID."""
        return self.employee_repo.generate_employee_id()

    def generate_new_leave_id(self) -> str:
        """Generate a new leave ID."""
        return self.leave_repo.generate_leave_id()

    def _normalize_date(self, val):
        """Normalize and return a datetime.date for the given value."""
        if val is None:
            return None
        if isinstance(val, date):
            return val
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, str):
            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(val, fmt).date()
                except Exception:
                    continue
            try:
                return datetime.fromisoformat(val).date()
            except Exception:
                raise ValueError(f"Unsupported date format: {val}")
        raise ValueError(f"Unsupported date type: {type(val)}")

    def calculate_leave_deduction(self, emp_id: str, month_str: str, base_salary: float):
        """Calculate leave deduction for an employee in a given month."""
        try:
            year, month = map(int, month_str.split("-"))
        except ValueError as exc:
            raise ValueError("Month must be in YYYY-MM format") from exc

        _, days_in_month = monthrange(year, month)
        per_day_salary = base_salary / days_in_month if days_in_month else 0
        month_start = date(year, month, 1)
        month_end = date(year, month, days_in_month)

        leave_days = 0.0

        def _normalize_to_date(val):
            if val is None:
                return None
            if isinstance(val, date):
                return val
            if isinstance(val, datetime):
                return val.date()
            if isinstance(val, str):
                for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
                    try:
                        return datetime.strptime(val, fmt).date()
                    except Exception:
                        continue
                try:
                    return datetime.fromisoformat(val).date()
                except Exception:
                    raise ValueError(f"Unsupported date format: {val}")
            raise ValueError(f"Unsupported date type: {type(val)}")

        for leave in self.leave_repo.list_leaves(force_refresh=True):
            if leave["emp_id"] != emp_id or leave["status"] != "Approved":
                continue
            try:
                leave_start = _normalize_to_date(leave.get("start_date"))
                leave_end = _normalize_to_date(leave.get("end_date"))
                
                if leave_start is None or leave_end is None:
                    continue
                
                overlap_start = max(month_start, leave_start)
                overlap_end = min(month_end, leave_end)
                
                if overlap_start > overlap_end:
                    continue
                
                days = (overlap_end - overlap_start).days + 1
                duration_type = leave.get("duration_type", "Full Day")
                
                if duration_type == "Half Day" and leave_start == leave_end:
                    effective = 0.5
                else:
                    effective = float(days)
                
                leave_days += effective
            except Exception:
                continue

        return leave_days, leave_days * per_day_salary

    def generate_salary_slip_pdf(self, record: dict, employee: dict) -> str:
        """Generate a PDF salary slip for an employee."""
        try:
            pdf_class = _get_fpdf_class()
        except RuntimeError as e:
            raise RuntimeError("FPDF library is not installed. Please run 'pip install fpdf2'") from e

        slips_dir = Path("salary_slips")
        slips_dir.mkdir(exist_ok=True)
        file_path = slips_dir / f"{record['id']}_{employee['id']}_{record['month']}.pdf"

        pdf = pdf_class()
        pdf.add_page()
        
        overtime_pay = record["overtime_hours"] * record["overtime_rate"]
        total_earnings = record['base_salary'] + overtime_pay + record['bonus']
        total_deductions = record['leave_deduction'] + record['other_deductions']
        
        # Header
        pdf.set_fill_color(41, 128, 185)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 24)
        pdf.cell(0, 15, "SALARY SLIP", ln=True, align="C", fill=True)
        
        pdf.ln(5)
        pdf.set_text_color(0, 0, 0)
        
        pdf.ln(8)
        
        # Employee Information
        pdf.set_fill_color(240, 240, 240)
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Employee Information", ln=True, fill=True)
        
        pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Arial", "", 10)
        pdf.cell(95, 7, f"Employee ID: {employee['id']}", border=1, fill=True)
        pdf.cell(95, 7, f"Department: {employee.get('department', 'N/A')}", border=1, ln=True, fill=True)
        pdf.cell(95, 7, f"Employee Name: {employee['name']}", border=1, fill=True)
        pdf.cell(95, 7, f"Designation: {employee.get('role', 'N/A').title()}", border=1, ln=True, fill=True)
        pdf.cell(95, 7, f"Pay Period: {record['month']}", border=1, fill=True)
        pdf.cell(95, 7, f"Payroll ID: {record['id']}", border=1, ln=True, fill=True)
        
        pdf.ln(10)
        
        # Earnings Section
        pdf.set_fill_color(46, 204, 113)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "EARNINGS", ln=True, fill=True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.set_fill_color(255, 255, 255)

        pdf.cell(140, 7, "Basic Salary", border=1, fill=True)
        pdf.cell(50, 7, f"Rs. {record['base_salary']:,.2f}", border=1, ln=True, align="R", fill=True)

        if overtime_pay > 0:
            pdf.cell(140, 7, f"Overtime ({record['overtime_hours']} hrs @ Rs.{record['overtime_rate']}/hr)", border=1, fill=True)
            pdf.cell(50, 7, f"Rs. {overtime_pay:,.2f}", border=1, ln=True, align="R", fill=True)

        if record['bonus'] > 0:
            pdf.cell(140, 7, "Bonus & Incentives", border=1, fill=True)
            pdf.cell(50, 7, f"Rs. {record['bonus']:,.2f}", border=1, ln=True, align="R", fill=True)

        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(230, 255, 230)
        pdf.cell(140, 7, "Total Earnings", border=1, fill=True)
        pdf.cell(50, 7, f"Rs. {total_earnings:,.2f}", border=1, ln=True, align="R", fill=True)

        pdf.ln(5)
        
        # Deductions Section
        pdf.set_fill_color(231, 76, 60)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "DEDUCTIONS", ln=True, fill=True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.set_fill_color(255, 255, 255)
        
        if record['leave_deduction'] > 0:
            pdf.cell(140, 7, "Leave Deduction", border=1, fill=True)
            pdf.cell(50, 7, f"Rs. {record['leave_deduction']:,.2f}", border=1, ln=True, align="R", fill=True)
        
        if record['other_deductions'] > 0:
            pdf.cell(140, 7, "Other Deductions", border=1, fill=True)
            pdf.cell(50, 7, f"Rs. {record['other_deductions']:,.2f}", border=1, ln=True, align="R", fill=True)
        
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(255, 230, 230)
        pdf.cell(140, 7, "Total Deductions", border=1, fill=True)
        pdf.cell(50, 7, f"Rs. {total_deductions:,.2f}", border=1, ln=True, align="R", fill=True)
        
        pdf.ln(10)
        
        # NET Salary
        pdf.set_fill_color(52, 152, 219)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 16)
        pdf.cell(140, 10, "NET SALARY", border=1, fill=True, align="L")
        pdf.cell(50, 10, f"Rs. {record['net_salary']:,.2f}", border=1, ln=True, align="R", fill=True)
        
        pdf.ln(15)
        
        # Footer
        pdf.set_text_color(100, 100, 100)
        pdf.set_font("Arial", "", 9)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.cell(0, 5, f"Generated On: {record['generated_on']}", ln=True, align="C")
        pdf.cell(0, 5, "This is a computer-generated document and does not require a signature.", ln=True, align="C")
        pdf.cell(0, 5, "For any queries, please contact the HR Department.", ln=True, align="C")

        pdf.output(str(file_path))
        return str(file_path)

    # ============================================================================
    # WINDOW MANAGEMENT METHODS
    # ============================================================================

    def _on_close(self):
        """Handle window close event."""
        self.db.close()
        self.root.destroy()

    def logout(self):
        """Log out current user and return to login screen."""
        try:
            self.current_user = None
            self.show_login_screen()
        except Exception:
            try:
                self.root.destroy()
            except Exception:
                pass

    def _create_scrolled_content(self, vertical_scroll: bool = False):
        """Create scrollable content area for dashboard."""
        try:
            if hasattr(self, "content_container") and self.content_container:
                self.content_container.destroy()
        except Exception:
            pass

        self.content_container = tk.Frame(self.root, bg="white")
        self.content_container.pack(side="right", fill="both", expand=True)

        self.content_top = tk.Frame(self.content_container, bg="white")
        self.content_top.pack(fill="x")

        if vertical_scroll:
            canvas = tk.Canvas(self.content_container, bg="white", highlightthickness=0)
            vscroll = tk.Scrollbar(self.content_container, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=vscroll.set)
            vscroll.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)

            inner = tk.Frame(canvas, bg="white")
            canvas.create_window((0, 0), window=inner, anchor="nw")

            def _on_frame_config(event):
                canvas.configure(scrollregion=canvas.bbox("all"))

            inner.bind("<Configure>", _on_frame_config)
            self.content_frame = inner
            self.content_canvas = canvas
        else:
            self.content_frame = tk.Frame(self.content_container, bg="white")
            self.content_frame.pack(fill="both", expand=True)

    def clear_window(self):
        """Clear all widgets from the window."""
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login_screen(self):
        """Display the login screen."""
        self.clear_window()
        
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(frame, text="Employee Management System", font=("Arial", 20, "bold"), bg="#f0f0f0").pack(pady=20)
        
        tk.Label(frame, text="Employee ID:", font=("Arial", 12), bg="#f0f0f0").pack(pady=5)
        emp_id_entry = tk.Entry(frame, font=("Arial", 12), width=25)
        emp_id_entry.pack(pady=5)
        
        tk.Label(frame, text="Password:", font=("Arial", 12), bg="#f0f0f0").pack(pady=5)
        password_entry = tk.Entry(frame, font=("Arial", 12), width=25, show="*")
        password_entry.pack(pady=5)
        
        def login():
            emp_id = emp_id_entry.get().strip()
            password = password_entry.get().strip()
            
            if not emp_id or not password:
                messagebox.showerror("Error", "Please enter Employee ID and Password!")
                return

            emp = self.employee_repo.get_employee(emp_id)
            if not emp or emp.get("password") != hash_password(password):
                messagebox.showerror("Error", "Invalid Employee ID or Password!")
                emp_id_entry.delete(0, "end")
                password_entry.delete(0, "end")
                emp_id_entry.focus_set()
                return

            self.current_user = emp

            if emp.get("role") == "admin":
                self.admin_dashboard.show_admin_dashboard()
            else:
                self.employee_dashboard.show_employee_dashboard()
        
        tk.Button(frame, text="Login", command=login, font=("Arial", 12), bg="#4CAF50", fg="white", width=20).pack(pady=20)
        
        emp_id_entry.focus_set()
        self.root.bind('<Return>', lambda e: login())

    def show_profile_dialog(self):
        """Display user profile dialog."""
        user = self.current_user
        dialog = tk.Toplevel(self.root)
        dialog.title("User Profile")
        dialog.geometry("350x250")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        header = tk.Frame(dialog, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title_label = tk.Label(header, text="👤 User Profile", font=("Arial", 14, "bold"), fg="black")
        title_label.pack(side="left", pady=12, padx=12)
        
        logout_btn = tk.Button(header, text="Logout", command=self.logout, 
                              bg="#f44336", fg="white", font=("Arial", 10), width=8)
        logout_btn.pack(side="right", padx=12, pady=12)

        info_frame = tk.Frame(dialog)
        info_frame.pack(pady=5, padx=20, fill="x")

        def add_row(label, value, row):
            tk.Label(info_frame, text=f"{label}:", font=("Arial", 11, "bold"), anchor="w").grid(
                row=row, column=0, sticky="w", pady=3
            )
            tk.Label(info_frame, text=value, font=("Arial", 11), anchor="w").grid(
                row=row, column=1, sticky="w", pady=3, padx=(5, 0)
            )

        add_row("ID", user.get("id", ""), 0)
        add_row("Name", user.get("name", ""), 1)
        add_row("Email", user.get("email", ""), 2)
        add_row("Phone", user.get("phone", ""), 3)
        add_row("Department", user.get("department", ""), 4)
        add_row("Role", user.get("role", ""), 5)

    # ============================================================================
    # DELEGATION METHODS - FOR COMPATIBILITY
    # ============================================================================

    def show_admin_dashboard(self):
        """Delegate to AdminDashboard module."""
        self.admin_dashboard.show_admin_dashboard()

    def show_admin_dashboard_home(self):
        """Delegate to AdminDashboard module."""
        self.admin_dashboard.show_admin_dashboard_home()

    def show_employee_dashboard(self):
        """Delegate to EmployeeDashboard module."""
        self.employee_dashboard.show_employee_dashboard()

    def show_employee_management(self):
        """Delegate to AdminDashboard module."""
        self.admin_dashboard.show_employee_management()

    def add_employee_dialog(self):
        """Delegate to AdminDashboard module."""
        self.admin_dashboard.add_employee_dialog()

    def edit_employee(self):
        """Delegate to AdminDashboard module."""
        self.admin_dashboard.edit_employee()

    def delete_employee(self):
        """Delegate to AdminDashboard module."""
        self.admin_dashboard.delete_employee()

    def _on_emp_tree_click(self, event):
        """Handle employee tree click events."""
        try:
            if self.emp_tree.identify_region(event.x, event.y) != "cell":
                return

            col_id = self.emp_tree.identify_column(event.x)
            columns = self.emp_tree["columns"]
            if "Actions" not in columns:
                return
            actions_index = columns.index("Actions") + 1
            if col_id != f"#{actions_index}":
                return

            item_id = self.emp_tree.identify_row(event.y)
            if not item_id:
                return

            values = self.emp_tree.item(item_id, "values")
            if not values:
                return

            emp_id = values[0]
            if emp_id:
                self.admin_dashboard.assign_salary_dialog(emp_id)
        except Exception:
            return

    def _on_emp_tree_motion(self, event):
        """Handle employee tree motion events."""
        try:
            if self.emp_tree.identify_region(event.x, event.y) != "cell":
                if self.emp_tree._hovered_item:
                    self.emp_tree.item(self.emp_tree._hovered_item, tags=("action_row",))
                    self.emp_tree._hovered_item = None
                self.emp_tree.configure(cursor="")
                return

            col_id = self.emp_tree.identify_column(event.x)
            columns = self.emp_tree["columns"]
            if "Actions" not in columns:
                if self.emp_tree._hovered_item:
                    self.emp_tree.item(self.emp_tree._hovered_item, tags=("action_row",))
                    self.emp_tree._hovered_item = None
                self.emp_tree.configure(cursor="")
                return

            actions_index = columns.index("Actions") + 1
            item_id = self.emp_tree.identify_row(event.y)
            
            if col_id == f"#{actions_index}" and item_id:
                self.emp_tree.configure(cursor="hand2")
                if self.emp_tree._hovered_item != item_id:
                    if self.emp_tree._hovered_item:
                        self.emp_tree.item(self.emp_tree._hovered_item, tags=("action_row",))
                    self.emp_tree.item(item_id, tags=("action_row", "action_hover"))
                    self.emp_tree._hovered_item = item_id
            else:
                if self.emp_tree._hovered_item:
                    self.emp_tree.item(self.emp_tree._hovered_item, tags=("action_row",))
                    self.emp_tree._hovered_item = None
                self.emp_tree.configure(cursor="")
        except Exception:
            if hasattr(self.emp_tree, '_hovered_item') and self.emp_tree._hovered_item:
                try:
                    self.emp_tree.item(self.emp_tree._hovered_item, tags=("action_row",))
                except:
                    pass
                self.emp_tree._hovered_item = None
            self.emp_tree.configure(cursor="")

    def _on_emp_tree_leave(self, event):
        """Handle employee tree leave events."""
        try:
            if hasattr(self.emp_tree, '_hovered_item') and self.emp_tree._hovered_item:
                self.emp_tree.item(self.emp_tree._hovered_item, tags=("action_row",))
                self.emp_tree._hovered_item = None
            self.emp_tree.configure(cursor="")
        except Exception:
            pass

    def assign_salary_dialog(self, emp_id: str | None = None, month_value: str | None = None):
        """Delegate to AdminDashboard module."""
        self.admin_dashboard.assign_salary_dialog(emp_id, month_value)

    def export_assigned_salaries_to_excel(self):
        """Delegate to AdminDashboard module."""
        self.admin_dashboard.export_assigned_salaries_to_excel()

    def export_employee_salaries_to_excel(self, emp_id: str, emp_name: str, assignments: list):
        """Delegate to AdminDashboard module."""
        self.admin_dashboard.export_employee_salaries_to_excel(emp_id, emp_name, assignments)

    def view_assignments_dialog(self, emp_id: str | None = None):
        """Delegate to AdminDashboard module."""
        self.admin_dashboard.view_assignments_dialog(emp_id)

    def show_leave_application(self):
        """Delegate to EmployeeDashboard module."""
        self.employee_dashboard.show_leave_application()

    def show_my_leaves(self):
        """Delegate to EmployeeDashboard module."""
        self.employee_dashboard.show_my_leaves()

    def edit_leave_application(self):
        """Delegate to EmployeeDashboard module."""
        self.employee_dashboard.edit_leave_application()

    def view_my_leave_details(self):
        """Delegate to EmployeeDashboard module."""
        self.employee_dashboard.view_my_leave_details()

    def show_leave_management(self):
        """Show leave request management (admin feature)."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        tk.Label(self.content_frame, text="Leave Requests Management", font=("Arial", 18, "bold"), bg="white").pack(pady=20)

        filter_frame = tk.Frame(self.content_frame, bg="white")
        filter_frame.pack(pady=10)
        
        self.leave_filter = tk.StringVar(value="All")
        
        tk.Radiobutton(filter_frame, text="All", variable=self.leave_filter, value="All", 
                      font=("Arial", 10), bg="white", command=self.refresh_leave_list).pack(side="left", padx=10)
        tk.Radiobutton(filter_frame, text="Pending", variable=self.leave_filter, value="Pending", 
                      font=("Arial", 10), bg="white", command=self.refresh_leave_list).pack(side="left", padx=10)
        tk.Radiobutton(filter_frame, text="Approved", variable=self.leave_filter, value="Approved", 
                      font=("Arial", 10), bg="white", command=self.refresh_leave_list).pack(side="left", padx=10)
        tk.Radiobutton(filter_frame, text="Rejected", variable=self.leave_filter, value="Rejected", 
                      font=("Arial", 10), bg="white", command=self.refresh_leave_list).pack(side="left", padx=10)
        
        stats_frame = tk.Frame(self.content_frame, bg="white")
        stats_frame.pack(pady=10)
        
        pending_count = len([l for l in self.leaves if l["status"] == "Pending"])
        approved_count = len([l for l in self.leaves if l["status"] == "Approved"])
        rejected_count = len([l for l in self.leaves if l["status"] == "Rejected"])
        
        tk.Label(stats_frame, text=f"Pending: {pending_count}", font=("Arial", 11, "bold"), 
                bg="#FF9800", fg="white", padx=15, pady=5).pack(side="left", padx=10)
        tk.Label(stats_frame, text=f"Approved: {approved_count}", font=("Arial", 11, "bold"), 
                bg="#4CAF50", fg="white", padx=15, pady=5).pack(side="left", padx=10)
        tk.Label(stats_frame, text=f"Rejected: {rejected_count}", font=("Arial", 11, "bold"), 
                bg="#f44336", fg="white", padx=15, pady=5).pack(side="left", padx=10)
        
        cols = ("ID", "Employee", "Type", "Start", "End", "Duration", "Status")
        tree_frame, self.leave_tree, leave_vscroll, leave_xscroll = self._create_table_with_scroll(self.content_frame, cols, height=12, enable_xscroll=True)
        
        for col in cols:
            self.leave_tree.heading(col, text=col)
            self.leave_tree.column(col, width=120)
        
        self.refresh_leave_list()
        
        btn_frame = tk.Frame(self.content_frame, bg="white")
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Approve", command=lambda: self.update_leave_status("Approved"), 
                 bg="#4CAF50", fg="white", font=("Arial", 10), width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Reject", command=lambda: self.update_leave_status("Rejected"), 
                 bg="#f44336", fg="white", font=("Arial", 10), width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="View Details", command=self.view_leave_details, 
                 bg="#2196F3", fg="white", font=("Arial", 10), width=12).pack(side="left", padx=5)

    def refresh_leave_list(self):
        """Refresh the leave management list."""
        for item in self.leave_tree.get_children():
            self.leave_tree.delete(item)
        
        self.refresh_leaves()

        filter_value = self.leave_filter.get()
        if filter_value == "All":
            filtered_leaves = self.leaves
        else:
            filtered_leaves = [l for l in self.leaves if l["status"] == filter_value]
        
        for leave in filtered_leaves:
            self.leave_tree.insert("", "end", values=(
                leave["id"], leave["emp_name"], leave["leave_type"], 
                leave["start_date"], leave["end_date"], leave.get("duration_type", "Full Day"), leave["status"]
            ))

    def update_leave_status(self, status):
        """Update status of a leave request."""
        selected = self.leave_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a leave request!")
            return
        
        leave_id = self.leave_tree.item(selected[0])["values"][0]

        self.leave_repo.update_status(leave_id, status)
        self.refresh_leaves()

        messagebox.showinfo("Success", f"Leave request {status.lower()} successfully!")
        self.show_leave_management()

    def view_leave_details(self):
        """View details of a leave request."""
        selected = self.leave_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a leave request!")
            return
        
        leave_id = self.leave_tree.item(selected[0])["values"][0]
        self.refresh_leaves()
        leave = self.leave_repo.get_leave(leave_id)
        
        if leave:
            details = f"""Leave ID: {leave['id']}
Employee: {leave['emp_name']} ({leave['emp_id']})
Leave Type: {leave['leave_type']}
Start Date: {leave['start_date']}
End Date: {leave['end_date']}
Duration: {leave.get('duration_type', 'Full Day')}
Status: {leave['status']}
Applied Date: {leave['applied_date']}

Reason:
{leave['reason']}"""
            
            messagebox.showinfo("Leave Details", details)

    def show_payroll_management(self):
        """Show payroll and salary correction management (admin feature)."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        tk.Label(self.content_frame, text="Payroll/Salary Correction Requests", font=("Arial", 18, "bold"), bg="white").pack(pady=20)

        # Filtering controls (status, employee, start date, end date)
        filter_frame = tk.Frame(self.content_frame, bg="white")
        filter_frame.pack(fill="x", padx=20, pady=8)

        tk.Label(filter_frame, text="Status:", font=("Arial", 10), bg="white").grid(row=0, column=0, padx=6, sticky="w")
        status_combo = ttk.Combobox(filter_frame, values=["All", "Pending", "Resolved", "Rejected", "Withdrawn"], width=14, state="readonly")
        status_combo.set("Pending")
        status_combo.grid(row=0, column=1, padx=6, sticky="w")

        tk.Label(filter_frame, text="Employee:", font=("Arial", 10), bg="white").grid(row=0, column=2, padx=6, sticky="w")
        employee_opts = ["All"] + [f"{e['id']} - {e['name']}" for e in self.employee_repo.list_employees()]
        employee_combo = ttk.Combobox(filter_frame, values=employee_opts, width=28, state="readonly")
        employee_combo.set("All")
        employee_combo.grid(row=0, column=3, padx=6, sticky="w")

        tk.Label(filter_frame, text="From (YYYY-MM-DD):", font=("Arial", 10), bg="white").grid(row=1, column=0, padx=6, pady=4, sticky="w")
        start_entry = tk.Entry(filter_frame, width=14, font=("Arial", 10))
        start_entry.grid(row=1, column=1, padx=6, pady=4, sticky="w")

        tk.Label(filter_frame, text="To (YYYY-MM-DD):", font=("Arial", 10), bg="white").grid(row=1, column=2, padx=6, pady=4, sticky="w")
        end_entry = tk.Entry(filter_frame, width=14, font=("Arial", 10))
        end_entry.grid(row=1, column=3, padx=6, pady=4, sticky="w")

        # Corrections table
        table_frame = tk.Frame(self.content_frame, bg="white")
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        cols = ("ID", "Employee", "Month", "Description", "Submitted On", "Status", "Notes/Reason")
        tf, tree, vscroll, xscroll = self._create_table_with_scroll(table_frame, cols, height=14, enable_xscroll=True)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=140)

        def apply_filters():
            """Apply filters and reload the correction requests table"""
            selected_status = status_combo.get()
            selected_emp = employee_combo.get()
            emp_id = None
            if selected_emp and selected_emp != "All":
                emp_id = selected_emp.split(" - ")[0].strip()
            status_filter = None if selected_status == "All" else selected_status
            start_date = start_entry.get().strip() or None
            end_date = end_entry.get().strip() or None
            rows = self.correction_repo.list_corrections_filtered(emp_id=emp_id, status=status_filter, start_date=start_date, end_date=end_date)
            # Clear tree and repopulate
            for i in tree.get_children():
                tree.delete(i)
            for r in rows:
                emp = self.employee_repo.get_employee(r.get("emp_id"))
                emp_name = emp.get("name") if emp else r.get("emp_id")
                # Show admin_notes if Resolved, rejection_reason if Rejected
                notes_or_reason = ""
                if r.get("status") == "Rejected":
                    notes_or_reason = r.get("rejection_reason", "")[:50]
                elif r.get("status") == "Resolved":
                    notes_or_reason = r.get("admin_notes", "")[:50]
                tree.insert("", "end", values=(r.get("id"), f"{emp_name} ({r.get('emp_id')})", r.get("month"), r.get("description")[:40], r.get("submitted_on"), r.get("status"), notes_or_reason))

        # Apply default filter to show Pending requests initially
        apply_filters()

        def resolve_with_notes():
            """Resolve a correction request and add admin notes"""
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Warning", "Please select a correction request to resolve.")
                return
            req_id = tree.item(sel[0])["values"][0]
            req = self.correction_repo.get_correction(req_id)
            if not req:
                messagebox.showerror("Error", "Selected request not found.")
                return
            if req.get("status") != "Pending":
                messagebox.showinfo("Info", "Only Pending requests can be resolved.")
                return

            # Dialog to add notes and resolve
            dialog = tk.Toplevel(self.root)
            dialog.title(f"Resolve Correction Request - {req_id}")
            dialog.geometry("500x380")
            dialog.transient(self.root)
            dialog.grab_set()

            tk.Label(dialog, text="Correction Request Details", font=("Arial", 12, "bold")).pack(pady=10)
            
            info_frame = tk.Frame(dialog, bg="#f5f5f5")
            info_frame.pack(fill="x", padx=15, pady=5)
            
            tk.Label(info_frame, text=f"Request ID: {req.get('id')}", font=("Arial", 10), bg="#f5f5f5").pack(anchor="w", pady=2)
            tk.Label(info_frame, text=f"Employee: {req.get('emp_id')}", font=("Arial", 10), bg="#f5f5f5").pack(anchor="w", pady=2)
            tk.Label(info_frame, text=f"Month: {req.get('month')}", font=("Arial", 10), bg="#f5f5f5").pack(anchor="w", pady=2)
            tk.Label(info_frame, text=f"Description: {req.get('description')}", font=("Arial", 10), bg="#f5f5f5", wraplength=400, justify="left").pack(anchor="w", pady=2)

            tk.Label(dialog, text="Admin Resolution Notes:", font=("Arial", 11)).pack(anchor="w", padx=15, pady=(15, 5))
            notes_text = tk.Text(dialog, height=8, width=60, font=("Arial", 10))
            notes_text.pack(padx=15, pady=5, fill="both", expand=True)

            def save_resolution():
                notes = notes_text.get("1.0", "end-1c").strip()
                if not notes:
                    messagebox.showwarning("Warning", "Please add resolution notes before resolving.")
                    return
                
                # Update correction status to Resolved and save notes
                self.correction_repo.update_correction(req_id, {
                    "status": "Resolved",
                    "admin_notes": notes,
                })
                
                messagebox.showinfo("Success", f"Request {req_id} marked as Resolved with notes.")
                
                # Notify employee
                try:
                    emp = self.employee_repo.get_employee(req.get("emp_id"))
                    employee_email = emp.get("email") if emp else None
                    employee_name = emp.get("name") if emp else req.get("emp_id")
                    from notifier import notify_request_updated
                    notify_request_updated(employee_email, employee_name, req_id, "Resolved")
                except Exception:
                    pass
                
                dialog.destroy()
                apply_filters()

            btn_frame = tk.Frame(dialog)
            btn_frame.pack(pady=10)
            tk.Button(btn_frame, text="Save & Resolve", command=save_resolution, bg="#4CAF50", fg="white", font=("Arial", 11), width=16).pack(side="left", padx=6)
            tk.Button(btn_frame, text="Cancel", command=dialog.destroy, font=("Arial", 11), width=12).pack(side="left", padx=6)

        def reject_correction_with_reason():
            """Reject a correction request with a reason"""
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Warning", "Please select a correction request to reject.")
                return
            req_id = tree.item(sel[0])["values"][0]
            req = self.correction_repo.get_correction(req_id)
            if not req:
                messagebox.showerror("Error", "Selected request not found.")
                return
            if req.get("status") != "Pending":
                messagebox.showinfo("Info", "Only Pending requests can be rejected.")
                return

            # Dialog to add rejection reason
            dialog = tk.Toplevel(self.root)
            dialog.title(f"Reject Correction Request - {req_id}")
            dialog.geometry("500x380")
            dialog.transient(self.root)
            dialog.grab_set()

            tk.Label(dialog, text="Rejection Reason", font=("Arial", 12, "bold")).pack(pady=10)
            
            info_frame = tk.Frame(dialog, bg="#fff3cd")
            info_frame.pack(fill="x", padx=15, pady=5)
            
            tk.Label(info_frame, text=f"Request ID: {req.get('id')}", font=("Arial", 10), bg="#fff3cd").pack(anchor="w", pady=2)
            tk.Label(info_frame, text=f"Employee: {req.get('emp_id')}", font=("Arial", 10), bg="#fff3cd").pack(anchor="w", pady=2)
            tk.Label(info_frame, text=f"Month: {req.get('month')}", font=("Arial", 10), bg="#fff3cd").pack(anchor="w", pady=2)
            tk.Label(info_frame, text=f"Requested Changes: {req.get('description')}", font=("Arial", 10), bg="#fff3cd", wraplength=400, justify="left").pack(anchor="w", pady=2)

            tk.Label(dialog, text="Why are you rejecting this request?", font=("Arial", 11)).pack(anchor="w", padx=15, pady=(15, 5))
            reason_text = tk.Text(dialog, height=8, width=60, font=("Arial", 10))
            reason_text.pack(padx=15, pady=5, fill="both", expand=True)

            def save_rejection():
                reason = reason_text.get("1.0", "end-1c").strip()
                if not reason:
                    messagebox.showwarning("Warning", "Please provide a rejection reason before rejecting.")
                    return
                
                # Update correction status to Rejected and save reason
                self.correction_repo.reject_correction(req_id, reason)
                
                messagebox.showinfo("Success", f"Request {req_id} has been rejected.")
                
                # Notify employee about rejection
                try:
                    emp = self.employee_repo.get_employee(req.get("emp_id"))
                    employee_email = emp.get("email") if emp else None
                    employee_name = emp.get("name") if emp else req.get("emp_id")
                    from notifier import notify_request_rejected
                    notify_request_rejected(employee_email, employee_name, req_id, reason)
                except Exception:
                    pass
                
                dialog.destroy()
                apply_filters()

            btn_frame = tk.Frame(dialog)
            btn_frame.pack(pady=10)
            tk.Button(btn_frame, text="Reject Request", command=save_rejection, bg="#f44336", fg="white", font=("Arial", 11), width=16).pack(side="left", padx=6)
            tk.Button(btn_frame, text="Cancel", command=dialog.destroy, font=("Arial", 11), width=12).pack(side="left", padx=6)

        def approve_and_edit_salary():
            """Approve correction and update/create salary assignment for that month"""
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Warning", "Please select a correction request to approve.")
                return
            req_id = tree.item(sel[0])["values"][0]
            req = self.correction_repo.get_correction(req_id)
            if not req:
                messagebox.showerror("Error", "Selected request not found.")
                return
            if req.get("status") != "Pending":
                messagebox.showinfo("Info", "Only Pending requests can be approved.")
                return

            emp_id = req.get("emp_id")
            month = req.get("month")
            
            # Get employee details
            emp = self.employee_repo.get_employee(emp_id)
            if not emp:
                messagebox.showerror("Error", "Employee not found.")
                return
            
            # Check if there's an existing assignment for this month
            existing_assignments = self.db.query(
                "SELECT * FROM salary_assignments WHERE emp_id = %s AND month = %s",
                (emp_id, month)
            )
            existing_assignment = dict(existing_assignments[0]) if existing_assignments else None
            
            # Get current salary from assignment or employee base salary
            if existing_assignment:
                current_salary = existing_assignment.get("assigned_salary", emp.get("salary", 0))
            else:
                current_salary = emp.get("salary", 0)

            # Dialog to approve with salary edit
            dialog = tk.Toplevel(self.root)
            dialog.title(f"Approve & Edit Monthly Salary - {req_id}")
            dialog.geometry("550x500")
            dialog.transient(self.root)
            dialog.grab_set()

            tk.Label(dialog, text="Approve Correction & Update Monthly Salary", font=("Arial", 12, "bold")).pack(pady=10)
            
            info_frame = tk.Frame(dialog, bg="#e8f5e9")
            info_frame.pack(fill="x", padx=15, pady=5)
            
            tk.Label(info_frame, text=f"Request ID: {req.get('id')}", font=("Arial", 10), bg="#e8f5e9").pack(anchor="w", pady=2)
            tk.Label(info_frame, text=f"Employee: {emp.get('name')} ({emp_id})", font=("Arial", 10), bg="#e8f5e9").pack(anchor="w", pady=2)
            tk.Label(info_frame, text=f"Month: {month}", font=("Arial", 10), bg="#e8f5e9").pack(anchor="w", pady=2)
            tk.Label(info_frame, text=f"Correction Request: {req.get('description')}", font=("Arial", 10), bg="#e8f5e9", wraplength=480, justify="left").pack(anchor="w", pady=2)

            tk.Label(dialog, text="Monthly Salary for this correction:", font=("Arial", 11, "bold")).pack(anchor="w", padx=15, pady=(15, 5))
            
            salary_frame = tk.Frame(dialog, bg="white")
            salary_frame.pack(fill="x", padx=15, pady=5)
            
            tk.Label(salary_frame, text="Assigned Salary (Rs.):", font=("Arial", 10)).pack(side="left", padx=5)
            salary_entry = tk.Entry(salary_frame, width=20, font=("Arial", 10))
            salary_entry.insert(0, str(current_salary))
            salary_entry.pack(side="left", padx=5)

            # Info label
            info_label = tk.Label(dialog, text="Note: This updates the salary assignment for the specified month only.\nEmployee's base salary remains unchanged.", 
                                font=("Arial", 9), bg="#fff9c4", fg="#333", wraplength=500, justify="left")
            info_label.pack(padx=15, pady=5)

            tk.Label(dialog, text="Admin Resolution Notes:", font=("Arial", 11)).pack(anchor="w", padx=15, pady=(15, 5))
            notes_text = tk.Text(dialog, height=6, width=65, font=("Arial", 10))
            notes_text.pack(padx=15, pady=5, fill="both", expand=True)

            def save_approval():
                try:
                    new_salary = float(salary_entry.get().strip())
                    if new_salary < 0:
                        messagebox.showwarning("Invalid", "Salary cannot be negative.")
                        return
                except ValueError:
                    messagebox.showerror("Error", "Please enter a valid salary amount.")
                    return
                
                notes = notes_text.get("1.0", "end-1c").strip()
                if not notes:
                    messagebox.showwarning("Warning", "Please add approval notes.")
                    return
                
                # Update correction to Resolved with notes
                self.correction_repo.approve_correction(req_id, notes)
                
                # Create or update salary assignment for this month
                try:
                    if existing_assignment:
                        # Update existing assignment
                        self.db.execute(
                            "UPDATE salary_assignments SET assigned_salary = %s WHERE id = %s",
                            (new_salary, existing_assignment["id"])
                        )
                        assignment_msg = f"Salary assignment updated for {month}"
                        assignment_id = existing_assignment["id"]
                    else:
                        # Create new assignment for this month
                        assignment_id = self.assignment_repo.generate_assignment_id()
                        self.assignment_repo.add_assignment({
                            "id": assignment_id,
                            "emp_id": emp_id,
                            "month": month,
                            "assigned_salary": new_salary,
                            "assigned_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "assigned_by": self.current_user.get("name", "Admin"),
                            "bonus": 0
                        })
                        assignment_msg = f"New salary assignment created for {month}"
                    
                    # Link assignment to correction request
                    self.correction_repo.update_correction(req_id, {"assignment_id": assignment_id})
                    
                    messagebox.showinfo("Success", f"Request {req_id} approved.\n{assignment_msg}\nAssigned Salary: Rs. {new_salary}")
                except Exception as exc:
                    messagebox.showerror("Error", f"Failed to update salary assignment: {exc}")
                    return
                
                dialog.destroy()
                apply_filters()

            btn_frame = tk.Frame(dialog)
            btn_frame.pack(pady=10)
            tk.Button(btn_frame, text="Save & Approve", command=save_approval, bg="#4CAF50", fg="white", font=("Arial", 11), width=16).pack(side="left", padx=6)
            tk.Button(btn_frame, text="Cancel", command=dialog.destroy, font=("Arial", 11), width=12).pack(side="left", padx=6)

        def view_request_details():
            """View full details of a correction request"""
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Warning", "Please select a correction request to view.")
                return
            req_id = tree.item(sel[0])["values"][0]
            req = self.correction_repo.get_correction(req_id)
            if not req:
                messagebox.showerror("Error", "Selected request not found.")
                return
            
            # Show appropriate status-based info
            status_info = ""
            if req.get("status") == "Rejected":
                status_info = f"\nRejection Reason:\n{req.get('rejection_reason', 'No reason provided')}"
            elif req.get("status") == "Resolved":
                status_info = f"\nAdmin Notes:\n{req.get('admin_notes', 'No notes yet')}"
            
            details = f"""Request ID: {req.get('id')}
Employee ID: {req.get('emp_id')}
Month: {req.get('month')}
Status: {req.get('status')}
Description:
{req.get('description')}{status_info}

Submitted On: {req.get('submitted_on')}"""
            
            messagebox.showinfo("Correction Request Details", details)

        def export_to_csv():
            """Export filtered corrections to CSV"""
            selected_status = status_combo.get()
            selected_emp = employee_combo.get()
            emp_id = None
            if selected_emp and selected_emp != "All":
                emp_id = selected_emp.split(" - ")[0].strip()
            status_filter = None if selected_status == "All" else selected_status
            start_date = start_entry.get().strip() or None
            end_date = end_entry.get().strip() or None
            rows = self.correction_repo.list_corrections_filtered(emp_id=emp_id, status=status_filter, start_date=start_date, end_date=end_date)
            if not rows:
                messagebox.showinfo("No Data", "No correction requests to export.")
                return
            out_dir = Path("salary_exports")
            out_dir.mkdir(exist_ok=True)
            filename = out_dir / f"corrections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            try:
                with open(filename, "w", newline='', encoding='utf-8') as f:
                    writer = __import__('csv').writer(f)
                    writer.writerow(["ID", "Emp ID", "Month", "Description", "Submitted On", "Status", "Admin Notes", "Rejection Reason"])
                    for r in rows:
                        writer.writerow([r.get('id'), r.get('emp_id'), r.get('month'), r.get('description'), r.get('submitted_on'), r.get('status'), r.get('admin_notes', ''), r.get('rejection_reason', '')])
                messagebox.showinfo("Exported", f"Corrections exported to {filename}")
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to export: {exc}")

        # Filter buttons
        filter_btn_frame = tk.Frame(self.content_frame, bg="white")
        filter_btn_frame.pack(pady=8)
        tk.Button(filter_btn_frame, text="Apply Filters", command=apply_filters, bg="#2196F3", fg="white", font=("Arial", 10)).pack(side="left", padx=6)
        tk.Button(filter_btn_frame, text="Clear Filters", command=lambda: (status_combo.set("Pending"), employee_combo.set("All"), start_entry.delete(0, 'end'), end_entry.delete(0, 'end'), apply_filters()), bg="#FF9800", fg="white", font=("Arial", 10)).pack(side="left", padx=6)

        # Action buttons
        action_frame = tk.Frame(self.content_frame, bg="white")
        action_frame.pack(pady=10)
        tk.Button(action_frame, text="✓ Approve & Edit Salary", command=approve_and_edit_salary, bg="#4CAF50", fg="white", font=("Arial", 11), width=20).pack(side="left", padx=6)
        tk.Button(action_frame, text="✗ Reject with Reason", command=reject_correction_with_reason, bg="#f44336", fg="white", font=("Arial", 11), width=20).pack(side="left", padx=6)
        tk.Button(action_frame, text="View Details", command=view_request_details, bg="#2196F3", fg="white", font=("Arial", 11), width=16).pack(side="left", padx=6)
        tk.Button(action_frame, text="Export to CSV", command=export_to_csv, bg="#FF9800", fg="white", font=("Arial", 11), width=14).pack(side="left", padx=6)

    def run(self):
        """Run the application."""
        self.root.mainloop()


if __name__ == "__main__":
    app = EmployeeManagementSystem()
    app.run()
