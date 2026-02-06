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

FPDF = None

def _get_fpdf_class():
    global FPDF
    if FPDF is None:
        try:
            module = importlib.import_module("fpdf")
            FPDF = module.FPDF
        except ImportError as exc:
            raise RuntimeError("FPDF library is not installed. Please run 'pip install fpdf'.") from exc
    return FPDF

from database_manager import DatabaseManager
from repositories import EmployeeRepository, LeaveRepository, PayrollRepository, CorrectionRepository
from repositories import SalaryAssignmentRepository
from employee_salary import SalaryUI

class EmployeeManagementSystem:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Employee Management System")
        self.root.geometry("1000x700")

        # Optional profile icon (use image-only button if available)
        self.profile_icon = None
        try:
            if os.path.exists("profile_icon.png"):
                self.profile_icon = tk.PhotoImage(file="profile_icon.png")
        except Exception:
            self.profile_icon = None
        
        # Data layer
        # DatabaseManager will read config for MySQL connection
        self.db = DatabaseManager()
        self.employee_repo = EmployeeRepository(self.db)
        self.leave_repo = LeaveRepository(self.db)
        self.payroll_repo = PayrollRepository(self.db)
        self.correction_repo = CorrectionRepository(self.db)
        self.assignment_repo = SalaryAssignmentRepository(self.db)
        # Employee salary UI helper
        self.salary_ui = SalaryUI(self)

        # In-memory caches synced via repositories
        self.employees = self.employee_repo.list_employees(force_refresh=True)
        self.leaves = self.leave_repo.list_leaves(force_refresh=True)
        self.current_user = None

        # Ensure DB connection closes cleanly when window closes
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.show_login_screen()

    def validate_phone_input(self, new_value: str) -> bool:
        """
        Tkinter validatecommand for phone Entry widgets.
        Allows only digits, max length 10.
        new_value is the would-be value after the key press.
        """
        # Allow empty value so user can delete
        if new_value == "":
            return True
        # Regex: 0 to 10 digits
        return bool(re.fullmatch(r"\d{0,10}", new_value))

    def _make_stat_card(self, parent, title, value, bg_color, icon="", onclick=None):
        card = tk.Frame(parent, bg=bg_color, width=240, height=120, bd=0, relief="ridge")
        card.pack_propagate(False)
        title_lbl = tk.Label(card, text=f"{icon}  {title}", font=("Arial", 12, "bold"), bg=bg_color, fg="white", wraplength=220, justify="left")
        title_lbl.pack(pady=(12, 0), padx=10, anchor="w")
        tk.Label(card, text=value, font=("Arial", 20, "bold"), bg=bg_color, fg="white").pack(pady=(6, 8))
        if onclick is not None:
            # Bind click to card and title label
            card.bind('<Button-1>', lambda e: onclick())
            title_lbl.bind('<Button-1>', lambda e: onclick())
            card.configure(cursor='hand2')
        return card

    def _create_table_with_scroll(self, parent, columns, height: int = 10, enable_xscroll: bool = False):
        """Create a treeview with vertical scrollbar and optional horizontal scrollbar.
        Returns (frame, tree, vscroll, xscroll) where scroll elements may be None.
        """
        frame = tk.Frame(parent, bg="white")
        frame.pack(fill="both", expand=True)
        # Vertical scrollbar on right of table
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

    # ---------- Data helpers ----------in 

    def refresh_employees(self):
        self.employees = self.employee_repo.list_employees(force_refresh=True)

    def refresh_leaves(self):
        self.leaves = self.leave_repo.list_leaves(force_refresh=True)

    def generate_new_employee_id(self) -> str:
        return self.employee_repo.generate_employee_id()

    def generate_new_leave_id(self) -> str:
        return self.leave_repo.generate_leave_id()

    def calculate_leave_deduction(self, emp_id: str, month_str: str, base_salary: float):
        try:
            year, month = map(int, month_str.split("-"))
        except ValueError as exc:
            raise ValueError("Month must be in YYYY-MM format") from exc

        _, days_in_month = monthrange(year, month)
        per_day_salary = base_salary / days_in_month if days_in_month else 0
        month_start = date(year, month, 1)
        month_end = date(year, month, days_in_month)

        leave_days = 0.0
        # Add a small helper available elsewhere; if other modules need it we can make it a separate function
        def _normalize_to_date(val):
            # Accepts date, datetime, or str in common formats and returns a date object
            if val is None:
                return None
            if isinstance(val, date):
                return val
            if isinstance(val, datetime):
                return val.date()
            # Try common string formats
            if isinstance(val, str):
                for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
                    try:
                        return datetime.strptime(val, fmt).date()
                    except Exception:
                        continue
                # Fall back to parsing date component only
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
                
                # Skip if dates couldn't be parsed
                if leave_start is None or leave_end is None:
                    continue
                
                # Calculate overlap with the month
                overlap_start = max(month_start, leave_start)
                overlap_end = min(month_end, leave_end)
                
                # Skip if no overlap
                if overlap_start > overlap_end:
                    continue
                
                days = (overlap_end - overlap_start).days + 1
                duration_type = leave.get("duration_type", "Full Day")
                
                # Handle half-day leaves
                if duration_type == "Half Day" and leave_start == leave_end:
                    effective = 0.5
                else:
                    effective = float(days)
                
                leave_days += effective
            except Exception:
                # Skip leaves with invalid date formats
                continue

        return leave_days, leave_days * per_day_salary

    def _normalize_date(self, val):
        """Normalize and return a datetime.date for the given value.
        Accepts datetime, date, or ISO string formats like 'YYYY-MM-DD' and 'YYYY-MM-DD HH:MM:SS'.
        """
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

    def generate_salary_slip_pdf(self, record: dict, employee: dict) -> str:
        # Try to import FPDF if not already imported
        try:
            pdf_class = _get_fpdf_class()
        except RuntimeError as e:
            raise RuntimeError("FPDF library is not installed. Please run 'pip install fpdf'") from e

        slips_dir = Path("salary_slips")
        slips_dir.mkdir(exist_ok=True)
        file_path = slips_dir / f"{record['id']}_{employee['id']}_{record['month']}.pdf"

        pdf = pdf_class()
        pdf.add_page()
        
        # Calculate values
        overtime_pay = record["overtime_hours"] * record["overtime_rate"]
        total_earnings = record['base_salary'] + overtime_pay + record['bonus']
        total_deductions = record['leave_deduction'] + record['other_deductions']
        
        # Header Section with Company Details
        pdf.set_fill_color(41, 128, 185)  # Blue background
        pdf.set_text_color(255, 255, 255)  # White text
        pdf.set_font("Arial", "B", 24)
        pdf.cell(0, 15, "SALARY SLIP", ln=True, align="C", fill=True)
        
        pdf.ln(5)
        # Removed the company title and payroll department lines from the PDF header as requested.
        pdf.set_text_color(0, 0, 0)  # Black text
        
        pdf.ln(8)
        
        # Employee Information Box
        pdf.set_fill_color(240, 240, 240)  # Light gray background
        pdf.set_draw_color(200, 200, 200)  # Gray border
        pdf.set_line_width(0.5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Employee Information", ln=True, fill=True)
        
        pdf.set_fill_color(255, 255, 255)  # White background
        pdf.set_font("Arial", "", 10)
        pdf.cell(95, 7, f"Employee ID: {employee['id']}", border=1, fill=True)
        pdf.cell(95, 7, f"Department: {employee.get('department', 'N/A')}", border=1, ln=True, fill=True)
        pdf.cell(95, 7, f"Employee Name: {employee['name']}", border=1, fill=True)
        pdf.cell(95, 7, f"Designation: {employee.get('role', 'N/A').title()}", border=1, ln=True, fill=True)
        pdf.cell(95, 7, f"Pay Period: {record['month']}", border=1, fill=True)
        pdf.cell(95, 7, f"Payroll ID: {record['id']}", border=1, ln=True, fill=True)
        
        pdf.ln(10)
        
        # Earnings Section
        pdf.set_fill_color(46, 204, 113)  # Green background
        pdf.set_text_color(255, 255, 255)  # White text
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "EARNINGS", ln=True, fill=True)
        
        pdf.set_text_color(0, 0, 0)  # Black text
        pdf.set_font("Arial", "", 10)
        pdf.set_fill_color(255, 255, 255)  # White background

        # Earnings table
        # Use ASCII-friendly currency text (Rs.) to avoid unicode encoding issues with FPDF's default latin-1
        pdf.cell(140, 7, "Basic Salary", border=1, fill=True)
        pdf.cell(50, 7, f"Rs. {record['base_salary']:,.2f}", border=1, ln=True, align="R", fill=True)

        if overtime_pay > 0:
            pdf.cell(140, 7, f"Overtime ({record['overtime_hours']} hrs @ Rs.{record['overtime_rate']}/hr)", border=1, fill=True)
            pdf.cell(50, 7, f"Rs. {overtime_pay:,.2f}", border=1, ln=True, align="R", fill=True)

        if record['bonus'] > 0:
            pdf.cell(140, 7, "Bonus & Incentives", border=1, fill=True)
            pdf.cell(50, 7, f"Rs. {record['bonus']:,.2f}", border=1, ln=True, align="R", fill=True)

        # Total Earnings
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(230, 255, 230)  # Light green
        pdf.cell(140, 7, "Total Earnings", border=1, fill=True)
        pdf.cell(50, 7, f"Rs. {total_earnings:,.2f}", border=1, ln=True, align="R", fill=True)

        pdf.ln(5)
        
        # Deductions Section
        pdf.set_fill_color(231, 76, 60)  # Red background
        pdf.set_text_color(255, 255, 255)  # White text
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "DEDUCTIONS", ln=True, fill=True)
        
        pdf.set_text_color(0, 0, 0)  # Black text
        pdf.set_font("Arial", "", 10)
        pdf.set_fill_color(255, 255, 255)  # White background
        
        # Deductions table
        if record['leave_deduction'] > 0:
            pdf.cell(140, 7, "Leave Deduction", border=1, fill=True)
            pdf.cell(50, 7, f"Rs. {record['leave_deduction']:,.2f}", border=1, ln=True, align="R", fill=True)
        
        if record['other_deductions'] > 0:
            pdf.cell(140, 7, "Other Deductions", border=1, fill=True)
            pdf.cell(50, 7, f"Rs. {record['other_deductions']:,.2f}", border=1, ln=True, align="R", fill=True)
        
        # Total Deductions
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(255, 230, 230)  # Light red
        pdf.cell(140, 7, "Total Deductions", border=1, fill=True)
        pdf.cell(50, 7, f"Rs. {total_deductions:,.2f}", border=1, ln=True, align="R", fill=True)
        
        pdf.ln(10)
        
        # Net Salary Section (Highlighted)
        pdf.set_fill_color(52, 152, 219)  # Blue background
        pdf.set_text_color(255, 255, 255)  # White text
        pdf.set_font("Arial", "B", 16)
        pdf.cell(140, 10, "NET SALARY", border=1, fill=True, align="L")
        pdf.cell(50, 10, f"Rs. {record['net_salary']:,.2f}", border=1, ln=True, align="R", fill=True)
        
        pdf.ln(15)
        
        # Footer Section
        pdf.set_text_color(100, 100, 100)  # Gray text
        pdf.set_font("Arial", "", 9)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.cell(0, 5, f"Generated On: {record['generated_on']}", ln=True, align="C")
        pdf.cell(0, 5, "This is a computer-generated document and does not require a signature.", ln=True, align="C")
        pdf.cell(0, 5, "For any queries, please contact the HR Department.", ln=True, align="C")

        pdf.output(str(file_path))
        return str(file_path)

    def _on_close(self):
        self.db.close()
        self.root.destroy()

    def logout(self):
        """Log out the current user and return to the login screen."""
        try:
            self.current_user = None
            # Clear any content and show login screen
            self.show_login_screen()
        except Exception:
            # Fallback: destroy window
            try:
                self.root.destroy()
            except Exception:
                pass
    def _create_scrolled_content(self, vertical_scroll: bool = False):
        """
        Create a right-side content area that is vertically scrollable.
        Sets:
          - self.content_container : outer frame that holds canvas + scrollbar
          - self.content_canvas : the canvas used for scrolling
          - self.content_frame : the inner frame where callers can pack widgets

        The sidebar (left) remains independent and won't scroll.
        """
        # If an old content container exists, destroy it first
        try:
            if hasattr(self, "content_container") and self.content_container:
                self.content_container.destroy()
        except Exception:
            pass

        self.content_container = tk.Frame(self.root, bg="white")
        self.content_container.pack(side="right", fill="both", expand=True)

        # Persistent top area inside content container e.g. for tabs / buttons
        self.content_top = tk.Frame(self.content_container, bg="white")
        self.content_top.pack(fill="x")

        if vertical_scroll:
            # Create canvas + vertical scrollbar
            canvas = tk.Canvas(self.content_container, bg="white", highlightthickness=0)
            vscroll = tk.Scrollbar(self.content_container, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=vscroll.set)
            vscroll.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)

            # Create content frame inside canvas
            inner = tk.Frame(canvas, bg="white")
            canvas.create_window((0, 0), window=inner, anchor="nw")

            # Bind to update scroll region
            def _on_frame_config(event):
                canvas.configure(scrollregion=canvas.bbox("all"))

            inner.bind("<Configure>", _on_frame_config)

            # Enable mousewheel scrolling only when pointer is over the canvas
            def _on_mousewheel(event):
                delta = event.delta
                # handle typical Windows behavior where delta is multiple of 120
                try:
                    canvas.yview_scroll(int(-1 * (delta / 120)), "units")
                except Exception:
                    canvas.yview_scroll(int(-1 * delta), "units")

            def _bind_mousewheel(event):
                # Bind the MouseWheel to the canvas only (no global binding)
                canvas.bind('<MouseWheel>', _on_mousewheel)

            def _unbind_mousewheel(event):
                try:
                    canvas.unbind('<MouseWheel>')
                except Exception:
                    pass

            canvas.bind('<Enter>', _bind_mousewheel)
            canvas.bind('<Leave>', _unbind_mousewheel)
            # Keep references
            self.content_canvas = canvas
            self.content_frame = inner
        else:
            # Simple inner frame for actual page content (no canvas scrolling)
            inner = tk.Frame(self.content_container, bg="white")
            inner.pack(fill="both", expand=True)
            self.content_canvas = None
            self.content_frame = inner

    
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def show_login_screen(self):
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
            emp_id = emp_id_entry.get()
            password = password_entry.get()
            
            emp = self.employee_repo.authenticate(emp_id, password)
            if emp:
                    self.current_user = emp
                    if emp["role"] == "admin":
                        self.show_admin_dashboard()
                    else:
                        self.show_employee_dashboard()
                    return
            
            messagebox.showerror("Error", "Invalid credentials!")
        
        tk.Button(frame, text="Login", command=login, font=("Arial", 12), bg="#4CAF50", fg="white", width=20).pack(pady=20)
        
    
    def show_profile_dialog(self):
        if not self.current_user:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("My Profile")
        dialog.geometry("350x280")
        dialog.transient(self.root)
        dialog.grab_set()

        user = self.current_user

        # Header row: title on the left, actions (Logout / Close) on the right
        header_frame = tk.Frame(dialog)
        header_frame.pack(fill="x", pady=10, padx=15)

        tk.Label(header_frame, text="My Profile", font=("Arial", 16, "bold")).pack(side="left")

        actions_frame = tk.Frame(header_frame)
        actions_frame.pack(side="right")

        def logout_from_profile():
            dialog.destroy()
            self.current_user = None
            self.show_login_screen()

        tk.Button(actions_frame, text="Logout", command=logout_from_profile,
                 bg="#f44336", fg="white", font=("Arial", 10), width=8).pack(side="left", padx=5)

        # Info rows under the header
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

    def show_admin_dashboard(self):
        self.clear_window()
        
        # Top bar
        top_frame = tk.Frame(self.root, bg="#2196F3", height=60)
        top_frame.pack(fill="x")
        
        tk.Label(top_frame, text=f"🏢  Admin Dashboard - Welcome {self.current_user['name']}", 
                font=("Arial", 16, "bold"), bg="#2196F3", fg="white").pack(side="left", padx=20, pady=15)

        # Profile button on top bar (icon-only)
        if self.profile_icon:
            # Use image icon (e.g., rounded user PNG) if available
            tk.Button(
                top_frame,
                image=self.profile_icon,
                command=self.show_profile_dialog,
                bg="#2196F3",
                activebackground="#2196F3",
                bd=0,
                highlightthickness=0,
                cursor="hand2",
            ).pack(side="right", padx=10, pady=10)
        else:
            # Fallback: text icon (user glyph) without label
            tk.Button(
                top_frame,
                text="👤",
                command=self.show_profile_dialog,
                font=("Arial", 16),
                bg="#2196F3",
                fg="white",
                activebackground="#1976D2",
                activeforeground="white",
                bd=0,
                highlightthickness=0,
                cursor="hand2",
                width=2,
            ).pack(side="right", padx=10, pady=10)
        
        # Sidebar (styled like employee sidebar for consistent admin UX)
        sidebar = tk.Frame(self.root, bg="#0B2545", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Sidebar header
        sidebar_header = tk.Frame(sidebar, bg="#0D47A1", height=56)
        sidebar_header.pack(fill="x")
        sidebar_header.pack_propagate(False)
        tk.Label(sidebar_header, text="🏢 Admin Menu", font=("Arial", 12, "bold"), bg="#0D47A1", fg="white").pack(pady=14)

        # Admin menu items
        menu_items = [
            ("🏠 Dashboard", self.show_admin_dashboard_home),
            ("👥 Manage Employees", self.show_employee_management),
            ("📝 Leave Requests", self.show_leave_management),
            ("💰 Payroll / Salary", self.show_payroll_management),
        ]

        menu_buttons_frame = tk.Frame(sidebar, bg="#0B2545")
        menu_buttons_frame.pack(fill="both", expand=True, padx=0, pady=10)

        menu_button_refs = []

        def create_menu_click_admin(menu_cmd, btn_ref_list, btn_widget):
            def on_click():
                for btn in btn_ref_list:
                    btn.config(bg="#0B2545", fg="#BBD1FF")
                btn_widget.config(bg="#083E78", fg="white")
                menu_cmd()
            return on_click

        for idx, (menu_text, menu_cmd) in enumerate(menu_items):
            mbtn = tk.Button(
                menu_buttons_frame,
                text=menu_text,
                command=None,
                bg="#0B2545",
                fg="#BBD1FF",
                font=("Arial", 11),
                relief="flat",
                bd=0,
                padx=15,
                pady=12,
                anchor="w",
                cursor="hand2",
                activebackground="#083E78",
                activeforeground="white",
            )
            mbtn.pack(fill="x", padx=8, pady=4)
            menu_button_refs.append(mbtn)

        for btn, (_, cmd) in zip(menu_button_refs, menu_items):
            btn.config(command=create_menu_click_admin(cmd, menu_button_refs, btn))

        if menu_button_refs:
            menu_button_refs[0].config(bg="#083E78", fg="white")

        # Sidebar footer
        sidebar_footer = tk.Frame(sidebar, bg="#0B2545", height=60)
        sidebar_footer.pack(side="bottom", fill="x")
        sidebar_footer.pack_propagate(False)
        tk.Frame(sidebar_footer, bg="#0D47A1", height=2).pack(fill="x")
        
        # Main content area (scrollable)
        self._create_scrolled_content()

        self.show_admin_dashboard_home()
    
    def show_admin_dashboard_home(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        tk.Label(self.content_frame, text="Admin Dashboard", font=("Arial", 18, "bold"), bg="white").pack(pady=(12, 8))

        # Ensure latest data from DB
        self.refresh_employees()
        self.refresh_leaves()

        # Top stats row (responsive)
        stats_row = tk.Frame(self.content_frame, bg="white")
        stats_row.pack(fill="x", padx=20)

        total_emps = len(self.employees)
        total_leaves = len(self.leaves)
        pending_leaves_count = len([l for l in self.leaves if l["status"] == "Pending"])
        approved_count = len([l for l in self.leaves if l["status"] == "Approved"])
        rejected_count = len([l for l in self.leaves if l["status"] == "Rejected"])

        # Use horizontal cards for a cleaner dashboard
        self._make_stat_card(stats_row, "Total Employees", str(total_emps), "#2E7D32", "👥", onclick=self.show_employee_management).pack(side="left", padx=10, pady=6, expand=True, fill="x")
        self._make_stat_card(stats_row, "Total Leave Apps", str(total_leaves), "#1565C0", "📝").pack(side="left", padx=10, pady=6, expand=True, fill="x")
        self._make_stat_card(stats_row, "Pending Requests", str(pending_leaves_count), "#F57C00", "⏳", onclick=self.show_leave_management).pack(side="left", padx=10, pady=6, expand=True, fill="x")
        self._make_stat_card(stats_row, "Net Approvals", str(approved_count), "#388E3C", "✅").pack(side="left", padx=10, pady=6, expand=True, fill="x")

        # Main area: two-column layout
        main_area = tk.Frame(self.content_frame, bg="white")
        main_area.pack(fill="both", expand=True, padx=20, pady=(10,20))
        main_area.grid_columnconfigure(0, weight=3)
        main_area.grid_columnconfigure(1, weight=1)

        # Left: Pending corrections + recent payroll table
        left_frame = tk.Frame(main_area, bg="white")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        tk.Label(left_frame, text="Pending Salary Correction Requests", font=("Arial", 14, "bold"), bg="white").pack(anchor="w", pady=(6,8))
        pending_corr_rows = self.correction_repo.list_corrections_filtered(status="Pending")
        cols = ("ID", "Emp ID", "Month", "Submitted On")
        corr_frame_inner, ctree, corr_vscroll, corr_xscroll = self._create_table_with_scroll(left_frame, cols, height=12, enable_xscroll=True)
        for col in cols:
            ctree.heading(col, text=col)
            ctree.column(col, width=120 if col != "Submitted On" else 200)
        for r in pending_corr_rows[:100]:
            ctree.insert("", "end", values=(r.get('id'), r.get('emp_id'), r.get('month'), r.get('submitted_on')))

        # Spacer and quick button
        tk.Button(left_frame, text="Open Payroll / Corrections", command=self.show_payroll_management, bg="#FB8C00", fg="white", font=("Arial", 11)).pack(pady=12, anchor="e")

        # Right: Quick actions and leave distribution
        right_frame = tk.Frame(main_area, bg="white")
        right_frame.grid(row=0, column=1, sticky="nsew")
        tk.Label(right_frame, text="Quick Actions", font=("Arial", 14, "bold"), bg="white").pack(anchor="w", pady=(6,8))

        actions = [
            ("Assign Salary", self.show_payroll_management, "💰"),
            ("Manage Employees", self.show_employee_management, "👥"),
            ("View Leaves", self.show_leave_management, "📝"),
        ]
        for title, cmd, icon in actions:
            tk.Button(right_frame, text=f"{icon}  {title}", command=cmd, bg="#1976D2", fg="white", font=("Arial", 11), width=22).pack(pady=6, anchor="w")

        # Simple leave distribution visual
        tk.Label(right_frame, text="Leave Status", font=("Arial", 12, "bold"), bg="white").pack(anchor="w", pady=(16,6))
        chart = tk.Canvas(right_frame, height=120, bg="white", highlightthickness=0)
        chart.pack(fill="x")
        total = max(total_leaves, 1)
        w = 200
        chart.create_rectangle(10, 20, 10 + int(w * pending_leaves_count / total), 50, fill="#F57C00", outline='')
        chart.create_text(12 + int(w * pending_leaves_count / total), 35, anchor='w', text=f"Pending: {pending_leaves_count}")
        chart.create_rectangle(10, 60, 10 + int(w * approved_count / total), 90, fill="#388E3C", outline='')
        chart.create_text(12 + int(w * approved_count / total), 75, anchor='w', text=f"Approved: {approved_count}")
        chart.create_rectangle(10, 100, 10 + int(w * rejected_count / total), 130, fill="#D32F2F", outline='')
        chart.create_text(12 + int(w * rejected_count / total), 115, anchor='w', text=f"Rejected: {rejected_count}")
    
    def show_employee_dashboard(self):
        self.clear_window()

        # Top bar with gradient-like effect
        top_frame = tk.Frame(self.root, bg="#1E88E5", height=70)
        top_frame.pack(fill="x")
        top_frame.pack_propagate(False)

        # Left side: Welcome message
        left_top = tk.Frame(top_frame, bg="#1E88E5")
        left_top.pack(side="left", padx=20, pady=15)
        
        tk.Label(left_top, text="Employee Dashboard", font=("Arial", 18, "bold"), bg="#1E88E5", fg="white").pack(anchor="w")
        tk.Label(left_top, text=f"Welcome, {self.current_user['name']}", font=("Arial", 11), bg="#1E88E5", fg="#E3F2FD").pack(anchor="w")

        # Right side: Profile button and Logout
        right_top = tk.Frame(top_frame, bg="#1E88E5")
        right_top.pack(side="right", padx=20, pady=15)
        
        if self.profile_icon:
            tk.Button(right_top, image=self.profile_icon, command=self.show_profile_dialog, bg="#1E88E5", bd=0, highlightthickness=0, cursor="hand2").pack(side="right", padx=10)
        else:
            tk.Button(right_top, text="👤", command=self.show_profile_dialog, font=("Arial", 16), bg="#1E88E5", fg="white", bd=0, highlightthickness=0, cursor="hand2", width=2).pack(side="right", padx=10)

        # Main container with sidebar
        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill="both", expand=True)

        # Sidebar (admin-style)
        sidebar = tk.Frame(main_frame, bg="#0B2545", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Sidebar header (admin color)
        sidebar_header = tk.Frame(sidebar, bg="#0D47A1", height=56)
        sidebar_header.pack(fill="x")
        sidebar_header.pack_propagate(False)
        tk.Label(sidebar_header, text="⚙️ Employee Menu", font=("Arial", 12, "bold"), bg="#0D47A1", fg="white").pack(pady=14)

        # Sidebar menu items (admin-like look). Note: removed Salary Correction and Salary Estimate for employees
        menu_items = [
            ("🏠 Dashboard", self.show_employee_dashboard),
            ("💰 My Salary", self.salary_ui.show_my_salary),
            ("📋 Apply Leave", self.show_leave_application),
            ("📅 My Leaves", self.show_my_leaves),
            ("✅ My Requests", self.salary_ui.show_my_requests),
        ]

        # Store current view for highlighting
        if not hasattr(self, 'current_menu_item'):
            self.current_menu_item = None

        menu_buttons_frame = tk.Frame(sidebar, bg="#0B2545")
        menu_buttons_frame.pack(fill="both", expand=True, padx=0, pady=10)

        menu_button_refs = []

        def create_menu_click(menu_cmd, btn_ref_list, btn_widget):
            def on_click():
                # Reset all button styles
                for btn in btn_ref_list:
                    btn.config(bg="#0B2545", fg="#BBD1FF")
                # Highlight current button
                btn_widget.config(bg="#083E78", fg="white")
                # Execute command
                menu_cmd()
            return on_click

        for idx, (menu_text, menu_cmd) in enumerate(menu_items):
            menu_btn = tk.Button(
                menu_buttons_frame,
                text=menu_text,
                command=None,  # Will be set below
                bg="#0B2545",
                fg="#BBD1FF",
                font=("Arial", 10),
                relief="flat",
                bd=0,
                padx=15,
                pady=12,
                anchor="w",
                cursor="hand2",
                activebackground="#083E78",
                activeforeground="white"
            )
            menu_btn.pack(fill="x", padx=8, pady=3)
            menu_button_refs.append(menu_btn)

        # Now set the commands
        for btn, (_, menu_cmd) in zip(menu_button_refs, menu_items):
            btn.config(command=create_menu_click(menu_cmd, menu_button_refs, btn))

        # Highlight Dashboard by default
        if menu_button_refs:
            menu_button_refs[0].config(bg="#083E78", fg="white")

        # Sidebar footer
        sidebar_footer = tk.Frame(sidebar, bg="#0B2545", height=60)
        sidebar_footer.pack(side="bottom", fill="x")
        sidebar_footer.pack_propagate(False)

        separator = tk.Frame(sidebar_footer, bg="#0D47A1", height=2)
        separator.pack(fill="x")

        # Content area (right side)
        content_wrapper = tk.Frame(main_frame, bg="white")
        content_wrapper.pack(side="right", fill="both", expand=True)

        # Create scrollable content area
        self.content_canvas = tk.Canvas(content_wrapper, bg="white", highlightthickness=0)
        self.content_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(content_wrapper, orient="vertical", command=self.content_canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.content_canvas.configure(yscrollcommand=scrollbar.set)
        self.content_frame = tk.Frame(self.content_canvas, bg="white")
        self.content_window = self.content_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        def on_frame_configure(event=None):
            self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))
            # Make content window span canvas width
            canvas_width = self.content_canvas.winfo_width()
            if canvas_width > 1:
                self.content_canvas.itemconfig(self.content_window, width=canvas_width)

        self.content_frame.bind("<Configure>", on_frame_configure)
        self.content_canvas.bind("<Configure>", lambda e: self.content_canvas.itemconfig(self.content_window, width=e.width))

        # Employee stats row with better spacing
        stats_row = tk.Frame(self.content_frame, bg="white")
        stats_row.pack(fill="x", padx=20, pady=20)

        emp = self.current_user or {}
        emp_salary = emp.get("salary", 0)
        emp_pending = len(self.correction_repo.list_corrections_filtered(emp_id=emp.get("id"), status="Pending")) if emp else 0
        
        # Get assigned salaries (monthly salaries) instead of payroll records
        emp_assignments = self.assignment_repo.list_assignments(emp.get("id") if emp else None)
        last_assignment = emp_assignments[0] if emp_assignments else None
        last_pay_text = f"{last_assignment.get('month')} — Rs. {last_assignment.get('assigned_salary', 0):,.2f}" if last_assignment else "No Assignment"

        self._make_stat_card(stats_row, "Monthly Salary", f"Rs. {emp_salary:,.2f}", "#2E7D32", "💵").pack(side="left", padx=10, expand=True, fill="x")
        self._make_stat_card(stats_row, "Pending Requests", str(emp_pending), "#F57C00", "🔔", onclick=self.salary_ui.show_my_requests).pack(side="left", padx=10, expand=True, fill="x")
        self._make_stat_card(stats_row, "Last Payslip", last_pay_text, "#1565C0", "📄").pack(side="left", padx=10, expand=True, fill="x")

        # Main content area with 2-column layout
        main_container = tk.Frame(self.content_frame, bg="white")
        main_container.pack(fill="both", expand=True, padx=20, pady=10)
        main_container.grid_columnconfigure(0, weight=3)
        main_container.grid_columnconfigure(1, weight=2)
        main_container.grid_rowconfigure(0, weight=1)

        # Left Column: Quick Actions
        left_panel = tk.Frame(main_container, bg="white", relief="flat", bd=0)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)

        # Section title with icon
        left_title_frame = tk.Frame(left_panel, bg="white")
        left_title_frame.pack(fill="x", pady=(0, 12))
        tk.Label(left_title_frame, text="⚡ Quick Actions", font=("Arial", 13, "bold"), bg="white", fg="#1E88E5").pack(anchor="w")
        
        # Action buttons with consistent styling
        buttons_config = [
            ("📋 Apply for Leave", self.show_leave_application, "#1E88E5"),
            ("📅 My Leaves", self.show_my_leaves, "#1565C0"),
            ("💰 Request Salary Correction", self.salary_ui.request_correction_on_assignment, "#FF5722"),
            ("✅ My Correction Requests", self.salary_ui.show_my_requests, "#F57C00"),
        ]
        
        for btn_text, btn_cmd, btn_color in buttons_config:
            btn = tk.Button(
                left_panel,
                text=btn_text,
                command=btn_cmd,
                bg=btn_color,
                fg="white",
                font=("Arial", 10, "bold"),
                padx=12,
                pady=10,
                relief="flat",
                cursor="hand2",
                activebackground=btn_color,
                activeforeground="white"
            )
            btn.pack(fill="x", pady=6)

        # Right Column: Recent Payslips
        right_panel = tk.Frame(main_container, bg="white", relief="flat", bd=0)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        # Section title with icon
        right_title_frame = tk.Frame(right_panel, bg="white")
        right_title_frame.pack(fill="x", pady=(0, 12))
        tk.Label(right_title_frame, text="📊 Recent Assignments", font=("Arial", 13, "bold"), bg="white", fg="#1E88E5").pack(anchor="w")

        # Salary assignments table with better styling
        assignments = emp_assignments[:10] if emp_assignments else []
        if assignments:
            cols = ("Month", "Assigned Salary", "Bonus")
            pf, ptree, pv, px = self._create_table_with_scroll(right_panel, cols, height=10)
            
            # Configure column headings and widths
            for c in cols:
                ptree.heading(c, text=c)
            ptree.column("Month", width=80)
            ptree.column("Assigned Salary", width=110, anchor="e")
            ptree.column("Bonus", width=80, anchor="e")
            
            # Insert assignment data with alternating colors
            for idx, a in enumerate(assignments):
                tag = "oddrow" if idx % 2 == 0 else "evenrow"
                ptree.insert("", "end", values=(
                    a.get("month"), 
                    f"Rs. {a.get('assigned_salary', 0):,.2f}",
                    f"Rs. {a.get('bonus', 0):,.2f}"
                ), tags=(tag,))
            
            # Configure tag colors for alternating rows
            ptree.tag_configure("oddrow", background="#FAFAFA")
            ptree.tag_configure("evenrow", background="white")
        else:
            tk.Label(right_panel, text="No salary assignments yet.", font=("Arial", 10), bg="white", fg="#999").pack(pady=20)
    
    def show_employee_management(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Refresh from DB
        self.refresh_employees()
        
        tk.Label(self.content_frame, text="Employee Management", font=("Arial", 18, "bold"), bg="white").pack(pady=20)
        
        # Add Employee Button
        tk.Button(self.content_frame, text="+ Add New Employee", command=self.add_employee_dialog, 
                 bg="#4CAF50", fg="white", font=("Arial", 11), width=20).pack(pady=10)
        
        # Employee List with Actions column included in table
        columns = ("ID", "Name", "Email", "Phone", "Department", "Role", "Salary (Yearly)", "Actions")
        tree_frame, self.emp_tree, emp_vscroll, emp_xscroll = self._create_table_with_scroll(
            self.content_frame,
            columns,
            height=12,
            enable_xscroll=True,
        )
        
        for i, col in enumerate(columns):
            self.emp_tree.heading(col, text=col)
            # make Salary and Actions columns wider
            if col == "Salary (Yearly)":
                self.emp_tree.column(col, width=160, anchor="e")
            elif col == "Actions":
                self.emp_tree.column(col, width=150, anchor="center")
            else:
                self.emp_tree.column(col, width=120)
        
        # Store which items have action buttons
        self.emp_tree._action_items = {}
        self.emp_tree._hovered_item = None
        
        # Configure style for button-like appearance
        style = ttk.Style()
        # Create a custom style for action cells
        style.configure("Action.Treeview", background="#4CAF50", foreground="white")
        
        for emp in self.employees:
            yearly_salary = float(emp.get("salary", 0)) * 12
            # Insert row with Actions column - use button-like text
            item_id = self.emp_tree.insert(
                "",
                "end",
                values=(
                    emp["id"],
                    emp["name"],
                    emp["email"],
                    emp["phone"],
                    emp["department"],
                    emp["role"],
                    f"Rs. {yearly_salary:,.2f}",
                    "▶ Assign Salary",  # Arrow symbol for button-like appearance
                ),
                tags=("action_row",)
            )
            self.emp_tree._action_items[item_id] = emp["id"]
        
        # Configure tag for action rows
        # We'll use a workaround: create button-like appearance using text styling
        # Since Treeview doesn't support cell-specific styling, we'll use tags on rows
        # and handle visual feedback through hover effects
        
        # Bind click on the Actions column to open Assign Salary dialog
        self.emp_tree.bind("<Button-1>", self._on_emp_tree_click)
        # Change cursor to hand when hovering over the Actions column
        self.emp_tree.bind("<Motion>", self._on_emp_tree_motion)
        self.emp_tree.bind("<Leave>", self._on_emp_tree_leave)
        
        # Configure tags for styling
        self.emp_tree.tag_configure("action_row", background="white")
        self.emp_tree.tag_configure("action_hover", background="#E8F5E9")  # Light green on hover
        
        # Action Buttons
        btn_frame = tk.Frame(self.content_frame, bg="white")
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Edit", command=self.edit_employee, bg="#2196F3", fg="white", 
             font=("Arial", 10), width=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_employee, bg="#f44336", fg="white", 
             font=("Arial", 10), width=10).pack(side="left", padx=5)
        # Assign Salary moved to Payroll module; keep a shortcut in Edit dialog only
        tk.Button(btn_frame, text="View Assignments", command=self.view_assignments_dialog, bg="#FF9800", fg="white", 
             font=("Arial", 10), width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Export to Excel", command=self.export_assigned_salaries_to_excel, bg="#4CAF50", fg="white", 
             font=("Arial", 10), width=14).pack(side="left", padx=5)
    
    def add_employee_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Employee")
        dialog.geometry("480x420")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        departments = ["Human Resources", "Engineering", "Marketing", "Sales", "Finance", "Operations", "IT", "Management"]
        
        # Make columns responsive and entries wider for readability
        dialog.grid_columnconfigure(0, weight=0, minsize=140)
        dialog.grid_columnconfigure(1, weight=1)
        tk.Label(dialog, text="Name:", font=("Arial", 11)).grid(row=0, column=0, padx=12, pady=6, sticky="w")
        name_entry = tk.Entry(dialog, font=("Arial", 11), width=36)
        name_entry.grid(row=0, column=1, padx=20, pady=10)
        
        tk.Label(dialog, text="Email:", font=("Arial", 11)).grid(row=1, column=0, padx=12, pady=6, sticky="w")
        email_entry = tk.Entry(dialog, font=("Arial", 11), width=36)
        email_entry.grid(row=1, column=1, padx=20, pady=10)
        
        tk.Label(dialog, text="Phone:", font=("Arial", 11)).grid(row=2, column=0, padx=12, pady=6, sticky="w")
        phone_entry = tk.Entry(dialog, font=("Arial", 11), width=36)
        # Live validation: only up to 10 digits
        phone_vcmd = (self.root.register(self.validate_phone_input), "%P")
        phone_entry.configure(validate="key", validatecommand=phone_vcmd)
        phone_entry.grid(row=2, column=1, padx=20, pady=10)
        
        tk.Label(dialog, text="Department:", font=("Arial", 11)).grid(row=3, column=0, padx=12, pady=6, sticky="w")
        dept_combo = ttk.Combobox(dialog, values=departments, font=("Arial", 11), width=34, state="readonly")
        dept_combo.set(departments[0])
        dept_combo.grid(row=3, column=1, padx=20, pady=10)
        
        tk.Label(dialog, text="Role:", font=("Arial", 11)).grid(row=4, column=0, padx=12, pady=6, sticky="w")
        role_combo = ttk.Combobox(dialog, values=["admin", "employee"], font=("Arial", 11), width=34, state="readonly")
        role_combo.set("employee")
        role_combo.grid(row=4, column=1, padx=20, pady=10)
        
        tk.Label(dialog, text="Password:", font=("Arial", 11)).grid(row=5, column=0, padx=12, pady=6, sticky="w")
        password_entry = tk.Entry(dialog, font=("Arial", 11), width=36, show="*")
        password_entry.grid(row=5, column=1, padx=20, pady=10)
        
        tk.Label(dialog, text="Base Salary (Monthly):", font=("Arial", 11)).grid(row=6, column=0, padx=12, pady=6, sticky="w")
        salary_entry = tk.Entry(dialog, font=("Arial", 11), width=36)
        salary_entry.insert(0, "60000")
        salary_entry.grid(row=6, column=1, padx=20, pady=10)
        
        def save_employee():
            emp_id = self.generate_new_employee_id()
            try:
                salary_value = float(salary_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Salary must be a valid number!")
                return

            new_emp = {
                "id": emp_id,
                "name": name_entry.get(),
                "email": email_entry.get(),
                "phone": phone_entry.get(),
                "department": dept_combo.get(),
                "role": role_combo.get(),
                "password": password_entry.get(),
                "salary": salary_value,
            }
            
            if not all([new_emp["name"], new_emp["email"], new_emp["password"]]):
                messagebox.showerror("Error", "Please fill all required fields!")
                return

            phone = new_emp["phone"]
            if not (phone.isdigit() and len(phone) == 10):
                messagebox.showerror("Error", "Phone number must be exactly 10 digits!")
                return
            
            self.employee_repo.add_employee(new_emp)
            self.refresh_employees()
            messagebox.showinfo("Success", f"Employee added successfully! ID: {emp_id}")
            dialog.destroy()
            self.show_employee_management()
        
        # Buttons: Save and Cancel
        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=18)
        tk.Button(btn_frame, text="Save", command=save_employee, bg="#4CAF50", fg="white", font=("Arial", 12), width=14).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, bg="#f44336", fg="white", font=("Arial", 12), width=14).pack(side="left", padx=8)

        # Focus and keyboard shortcuts
        name_entry.focus_set()
        dialog.bind('<Return>', lambda e: save_employee())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def edit_employee(self):
        selected = self.emp_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an employee to edit!")
            return
        
        emp_id = self.emp_tree.item(selected[0])["values"][0]
        emp = self.employee_repo.get_employee(emp_id)
        
        if not emp:
            messagebox.showerror("Error", "Unable to load employee details.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Employee - {emp['name']}")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)
        
        # Configure grid weights
        dialog.columnconfigure(1, weight=1)
        
        # Style configuration
        label_font = ("Arial", 11)
        entry_font = ("Arial", 11)
        button_font = ("Arial", 11, "bold")
        padx = 20
        pady = 8
        
        # Main container frame
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Edit Employee Details",
            font=("Arial", 14, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")
        
        # Form fields
        fields = [
            ("Name:", "name", "entry"),
            ("Email:", "email", "entry"),
            ("Phone:", "phone", "phone"),
            ("Department:", "department", "combo", 
             ["Human Resources", "Engineering", "Marketing", "Sales", "Finance", "Operations", "IT", "Management"]),
            ("Role:", "role", "combo", ["admin", "employee"]),
            ("Base Salary (Monthly):", "salary", "entry")
        ]
        
        entries = {}
        for i, field in enumerate(fields, 1):
            label_text = field[0]
            field_name = field[1]
            field_type = field[2]
            
            # Create label
            label = ttk.Label(main_frame, text=label_text, font=label_font)
            label.grid(row=i, column=0, padx=padx, pady=pady, sticky="e")
            
            # Create appropriate input field
            if field_type == "entry" or field_type == "phone":
                entry = ttk.Entry(main_frame, font=entry_font, width=30)
                entry.insert(0, str(emp.get(field_name, "")))
                entry.grid(row=i, column=1, padx=padx, pady=pady, sticky="ew")
                entries[field_name] = entry
                
                # Add phone number validation
                if field_type == "phone":
                    phone_vcmd = (self.root.register(self.validate_phone_input), "%P")
                    entry.configure(validate="key", validatecommand=phone_vcmd)
                    
            elif field_type == "combo":
                values = field[3] if len(field) > 3 else []
                combo = ttk.Combobox(
                    main_frame, 
                    values=values, 
                    font=entry_font, 
                    state="readonly",
                    width=27
                )
                combo.set(emp.get(field_name, values[0] if values else ""))
                combo.grid(row=i, column=1, padx=padx, pady=pady, sticky="w")
                entries[field_name] = combo
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=20)
        
        def update_employee():
            # Validate phone number
            phone = entries["phone"].get()
            if not (phone.isdigit() and len(phone) == 10):
                messagebox.showerror("Error", "Phone number must be exactly 10 digits!")
                return

            # Validate salary
            try:
                salary_value = float(entries["salary"].get())
                if salary_value < 0:
                    raise ValueError("Salary cannot be negative")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid positive number for salary!")
                return

            # Update employee
            try:
                self.employee_repo.update_employee(
                    emp_id,
                    {
                        "name": entries["name"].get(),
                        "email": entries["email"].get(),
                        "phone": phone,
                        "department": entries["department"].get(),
                        "role": entries["role"].get(),
                        "salary": salary_value,
                    },
                )
                self.refresh_employees()
                messagebox.showinfo("Success", "Employee updated successfully!")
                dialog.destroy()
                self.show_employee_management()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update employee: {str(e)}")
        
        # Buttons
        update_btn = ttk.Button(
            button_frame, 
            text="Update Employee", 
            command=update_employee,
            style="Accent.TButton"
        )
        update_btn.pack(side="left", padx=5)
       
        # Configure styles
        style = ttk.Style()
        style.configure("Accent.TButton", font=button_font, padding=6)
        style.configure("Secondary.TButton", font=button_font, padding=6)
        
        # Make the window resizable
        main_frame.columnconfigure(1, weight=1)
        
        # Set focus to name field
        entries["name"].focus_set()
        
        # Bind Enter key to update
        dialog.bind("<Return>", lambda e: update_employee())
        
        # Center the dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def delete_employee(self):
        selected = self.emp_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an employee to delete!")
            return
        
        emp_id = self.emp_tree.item(selected[0])["values"][0]
        
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this employee?"):
            self.employee_repo.delete_employee(emp_id)
            self.refresh_employees()
            messagebox.showinfo("Success", "Employee deleted successfully!")
            self.show_employee_management()
    
    def _on_emp_tree_click(self, event):
        """
        Handle clicks on the Employee Management tree.
        If the user clicks in the 'Actions' column, open the assign salary dialog
        for that specific employee.
        """
        try:
            # Ensure we are clicking on a cell
            if self.emp_tree.identify_region(event.x, event.y) != "cell":
                return

            # Determine which column was clicked
            col_id = self.emp_tree.identify_column(event.x)  # e.g. '#1', '#2', ...
            columns = self.emp_tree["columns"]
            if "Actions" not in columns:
                return
            actions_index = columns.index("Actions") + 1  # Treeview columns are 1-based
            if col_id != f"#{actions_index}":
                return

            # Determine which row was clicked
            item_id = self.emp_tree.identify_row(event.y)
            if not item_id:
                return

            values = self.emp_tree.item(item_id, "values")
            if not values:
                return

            emp_id = values[0]  # First column is Employee ID
            if emp_id:
                self.assign_salary_dialog(emp_id)
        except Exception:
            # Fail gracefully; don't block normal tree usage
            return

    def _on_emp_tree_motion(self, event):
        """
        Update cursor and highlight row when hovering over the Actions column so it looks clickable,
        similar to a button.
        """
        try:
            if self.emp_tree.identify_region(event.x, event.y) != "cell":
                # Remove hover effect from previous item
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

            actions_index = columns.index("Actions") + 1  # Treeview columns are 1-based
            item_id = self.emp_tree.identify_row(event.y)
            
            if col_id == f"#{actions_index}" and item_id:
                self.emp_tree.configure(cursor="hand2")
                # Highlight the row
                if self.emp_tree._hovered_item != item_id:
                    # Remove highlight from previous item
                    if self.emp_tree._hovered_item:
                        self.emp_tree.item(self.emp_tree._hovered_item, tags=("action_row",))
                    # Add highlight to current item
                    self.emp_tree.item(item_id, tags=("action_row", "action_hover"))
                    self.emp_tree._hovered_item = item_id
            else:
                # Remove highlight if not over Actions column
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
        """
        Remove hover effects when mouse leaves the treeview.
        """
        try:
            if hasattr(self.emp_tree, '_hovered_item') and self.emp_tree._hovered_item:
                self.emp_tree.item(self.emp_tree._hovered_item, tags=("action_row",))
                self.emp_tree._hovered_item = None
            self.emp_tree.configure(cursor="")
        except Exception:
            pass

    def assign_salary_dialog(self, emp_id: str | None = None, month_value: str | None = None):
        # If emp_id unspecified, use selected in table
        if not emp_id:
            selected = getattr(self, 'emp_tree', None).selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select an employee to assign salary.")
                return
            emp_id = self.emp_tree.item(selected[0])["values"][0]

        emp = self.employee_repo.get_employee(emp_id)
        if not emp:
            messagebox.showerror("Error", "Employee not found.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Assign Salary - {emp['name']} ({emp['id']})")
        dialog.geometry("580x500")
        dialog.transient(self.root)
        dialog.grab_set()

        header = tk.Frame(dialog, bg="#f5f5f5")
        header.pack(fill="x")
        tk.Label(header, text=f"Assign Salary", font=("Arial", 14, "bold"), bg="#f5f5f5").pack(side="left", padx=12, pady=8)
        tk.Label(header, text=f"{emp['name']} ({emp['id']})", font=("Arial", 10), bg="#f5f5f5").pack(side="right", padx=12)

        frame = tk.Frame(dialog)
        frame.pack(padx=20, pady=12, fill="both", expand=True)

        tk.Label(frame, text="Month (YYYY-MM):", font=("Arial", 11)).grid(row=0, column=0, sticky="w", pady=6)
        month_var = tk.StringVar(value=month_value or datetime.now().strftime("%Y-%m"))
        month_entry = tk.Entry(frame, font=("Arial", 11), width=14, textvariable=month_var)
        month_entry.grid(row=0, column=1, pady=6, sticky="w")

        # Base salary entry
        tk.Label(frame, text="Base Salary (Rs) (Monthly):", font=("Arial", 11)).grid(row=1, column=0, sticky="w", pady=6)
        base_salary_var = tk.StringVar(value=str(emp.get("salary", 0)))
        base_salary_entry = tk.Entry(frame, font=("Arial", 11), width=20, textvariable=base_salary_var)
        base_salary_entry.grid(row=1, column=1, pady=6, sticky="w")

        # Bonus / Incentives input
        tk.Label(frame, text="Bonus / Incentives:", font=("Arial", 11)).grid(row=2, column=0, sticky="w", pady=6)
        bonus_var = tk.StringVar(value="0")
        bonus_entry = tk.Entry(frame, font=("Arial", 11), width=20, textvariable=bonus_var)
        bonus_entry.grid(row=2, column=1, pady=6, sticky="w")

        # Leave deduction display (read-only)
        tk.Label(frame, text="Leave Deduction:", font=("Arial", 11)).grid(row=3, column=0, sticky="w", pady=6)
        leave_deduction_var = tk.StringVar(value="Calculating...")
        leave_deduction_label = tk.Label(frame, textvariable=leave_deduction_var, font=("Arial", 11, "bold"), fg="#d32f2f")
        leave_deduction_label.grid(row=3, column=1, pady=6, sticky="w")

        # Leave days display
        tk.Label(frame, text="Leave Days:", font=("Arial", 11)).grid(row=4, column=0, sticky="w", pady=6)
        leave_days_var = tk.StringVar(value="")
        leave_days_label = tk.Label(frame, textvariable=leave_days_var, font=("Arial", 11))
        leave_days_label.grid(row=4, column=1, pady=6, sticky="w")

        # NET Salary display (read-only, this is the calculated NET)
        tk.Label(frame, text="NET Salary (calculated):", font=("Arial", 12, "bold")).grid(row=5, column=0, sticky="w", pady=8)
        net_salary_var = tk.StringVar(value="Rs. 0.00")
        net_salary_label = tk.Label(frame, textvariable=net_salary_var, font=("Arial", 14, "bold"), fg="#2E7D32", bg="#E8F5E9", padx=10, pady=5)
        net_salary_label.grid(row=5, column=1, pady=8, sticky="w")

        # Assigned By (Admin ID)
        tk.Label(frame, text="Assigned By (Admin ID):", font=("Arial", 11)).grid(row=6, column=0, sticky="w", pady=6)
        admin_entry = tk.Entry(frame, font=("Arial", 11), width=20)
        admin_entry.insert(0, self.current_user.get("id") if self.current_user else "")
        admin_entry.grid(row=6, column=1, pady=6, sticky="w")

        def calculate_net_salary():
            """Calculate NET salary (base - leave deductions)"""
            try:
                month_val = month_var.get().strip()
                if not month_val:
                    leave_deduction_var.set("Rs. 0.00")
                    leave_days_var.set("0 days")
                    net_salary_var.set("Rs. 0.00")
                    return
                
                # Validate month format
                try:
                    year, month = map(int, month_val.split("-"))
                    if month < 1 or month > 12:
                        raise ValueError("Invalid month")
                except (ValueError, IndexError):
                    leave_deduction_var.set("Invalid month format")
                    leave_days_var.set("0 days")
                    net_salary_var.set("Rs. 0.00")
                    return
                
                try:
                    base_salary = float(base_salary_var.get())
                except ValueError:
                    leave_deduction_var.set("Invalid base salary")
                    leave_days_var.set("0 days")
                    net_salary_var.set("Rs. 0.00")
                    return

                try:
                    bonus = float(bonus_var.get())
                except ValueError:
                    bonus = 0.0
                
                if base_salary <= 0:
                    leave_deduction_var.set("Rs. 0.00")
                    leave_days_var.set("0 days")
                    net_salary_var.set("Rs. 0.00")
                    return
                
                # Refresh leaves to ensure we have latest data
                self.refresh_leaves()
                
                # Calculate leave deduction
                try:
                    leave_days, leave_deduction = self.calculate_leave_deduction(emp['id'], month_val, base_salary)
                except Exception as calc_error:
                    # Show error but don't crash
                    leave_deduction_var.set(f"Error calculating: {str(calc_error)}")
                    leave_days_var.set("0 days")
                    net_salary_var.set(f"Rs. {base_salary:,.2f}")  # Use base salary if calculation fails
                    return
                
                # Display leave deduction and days
                leave_deduction_var.set(f"Rs. {leave_deduction:,.2f}")
                if leave_days > 0:
                    leave_days_var.set(f"{leave_days:.2f} days")
                else:
                    leave_days_var.set("0 days (No approved leaves)")
                
                # NET salary = Base salary + Bonus - Leave deduction
                net_salary = base_salary + bonus - leave_deduction
                net_salary = max(net_salary, 0)  # Ensure non-negative
                net_salary_var.set(f"Rs. {net_salary:,.2f}")
                
            except Exception as e:
                # Catch any unexpected errors
                import traceback
                error_msg = f"Error: {str(e)}"
                leave_deduction_var.set(error_msg)
                leave_days_var.set("Error")
                try:
                    base_salary = float(base_salary_var.get())
                    net_salary_var.set(f"Rs. {base_salary:,.2f}")
                except:
                    net_salary_var.set("Rs. 0.00")

        # Calculate on month or base salary change
        def on_month_change(event=None):
            calculate_net_salary()
        
        def on_salary_change(event=None):
            calculate_net_salary()

        def on_bonus_change(event=None):
            calculate_net_salary()

        
        month_entry.bind("<KeyRelease>", on_month_change)
        month_entry.bind("<FocusOut>", on_month_change)
        base_salary_entry.bind("<KeyRelease>", on_salary_change)
        base_salary_entry.bind("<FocusOut>", on_salary_change)
        bonus_entry.bind("<KeyRelease>", on_bonus_change)
        bonus_entry.bind("<FocusOut>", on_bonus_change)
        
        
        # Add a refresh button to manually recalculate
        refresh_frame = tk.Frame(frame, bg="white")
        refresh_frame.grid(row=7, column=0, columnspan=2, pady=5)
        tk.Button(
            refresh_frame, 
            text="🔄 Recalculate Leave Deduction", 
            command=calculate_net_salary,
            bg="#2196F3", 
            fg="white", 
            font=("Arial", 9),
            cursor="hand2"
        ).pack()
        
        # Initial calculation - ensure it runs after dialog is ready
        def initial_calc():
            calculate_net_salary()
        
        dialog.update_idletasks()
        dialog.after(200, initial_calc)  # Small delay to ensure everything is rendered

        def do_assign():
            try:
                # Validate month
                month_val = month_var.get().strip()
                if not month_val:
                    messagebox.showerror("Error", "Please provide a month in YYYY-MM format.")
                    return
                
                # Get NET salary from the calculated display
                net_salary_str = net_salary_var.get().replace("Rs. ", "").replace(",", "").strip()
                net_salary = float(net_salary_str)
                try:
                    bonus_val = float(bonus_var.get())
                except Exception:
                    bonus_val = 0.0
                
                if net_salary <= 0:
                    messagebox.showerror("Error", "NET salary must be greater than 0.")
                    return
                
            except ValueError:
                messagebox.showerror("Error", "Please enter valid values.")
                return
            
            admin_id = admin_entry.get().strip() or (self.current_user.get("id") if self.current_user else None)
            
            # Make a new assignment record with NET salary
            asg_id = self.assignment_repo.generate_assignment_id()
            record = {
                "id": asg_id,
                "emp_id": emp['id'],
                "month": month_val,
                "assigned_salary": net_salary,  # Store NET salary (includes bonus if any)
                "bonus": bonus_val,
                "assigned_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "assigned_by": admin_id,
            }
            try:
                self.assignment_repo.add_assignment(record)
                # Update current employee base salary (not NET salary)
                base_salary_val = float(base_salary_var.get())
                self.employee_repo.update_employee(emp['id'], {
                    "name": emp['name'],
                    "email": emp['email'],
                    "phone": emp['phone'],
                    "department": emp['department'],
                    "role": emp['role'],
                    "salary": base_salary_val,  # Store base salary, not NET
                })
                self.refresh_employees()
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to assign salary: {exc}")
                return
            
            # Show success and offer Excel export
            result = messagebox.askyesno(
                "Success", 
                f"Assigned NET salary Rs. {net_salary:,.2f} to {emp['name']} for {month_val}.\n\n"
                "Would you like to export all assigned salaries to Excel?"
            )
            dialog.destroy()
            
            if result:
                self.export_assigned_salaries_to_excel()
            
            self.show_employee_management()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill="x", pady=8)
        
        def export_employee_assignments():
            """Export assigned salaries for this specific employee to Excel"""
            assignments = self.assignment_repo.list_assignments(emp['id'])
            if not assignments:
                messagebox.showinfo("No Data", f"No assigned salaries found for {emp['name']}.")
                return
            
            self.export_employee_salaries_to_excel(emp['id'], emp['name'], assignments)
        
        tk.Button(btn_frame, text="📊 Export Excel", bg="#2196F3", fg="white", command=export_employee_assignments, font=("Arial", 10)).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Assign NET Salary", bg="#4CAF50", fg="white", command=do_assign, font=("Arial", 11, "bold"), width=15).pack(side="right", padx=12)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, font=("Arial", 11), width=10).pack(side="right")

    def export_assigned_salaries_to_excel(self):
        """
        Export all assigned salaries to an Excel file (CSV format if openpyxl not available).
        """
        try:
            # Get all assignments
            all_assignments = []
            for emp in self.employee_repo.list_employees():
                assignments = self.assignment_repo.list_assignments(emp['id'])
                for asg in assignments:
                    all_assignments.append({
                        'assignment_id': asg.get('id'),
                        'employee_id': asg.get('emp_id'),
                        'employee_name': emp.get('name', ''),
                        'department': emp.get('department', ''),
                        'month': asg.get('month'),
                        'assigned_salary': asg.get('assigned_salary', 0),
                        'assigned_on': asg.get('assigned_on'),
                        'assigned_by': asg.get('assigned_by', ''),
                    })
            
            if not all_assignments:
                messagebox.showinfo("No Data", "No assigned salaries found to export.")
                return
            
            # Sort by month (newest first), then by employee name
            all_assignments.sort(key=lambda x: (x['month'], x['employee_name']), reverse=True)
            
            # Try to use openpyxl for Excel format, otherwise use CSV
            try:
                # Use importlib to avoid linter warnings for optional dependency
                openpyxl = importlib.import_module("openpyxl")
                openpyxl_styles = importlib.import_module("openpyxl.styles")
                Font = openpyxl_styles.Font
                PatternFill = openpyxl_styles.PatternFill
                Alignment = openpyxl_styles.Alignment
                
                # Create Excel file
                out_dir = Path("salary_exports")
                out_dir.mkdir(exist_ok=True)
                filename = out_dir / f"assigned_salaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Assigned Salaries"
                
                # Headers
                headers = ["Assignment ID", "Employee ID", "Employee Name", "Department", 
                          "Month", "Assigned Salary (NET)", "Assigned On", "Assigned By"]
                ws.append(headers)
                
                # Style header row
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF")
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                
                # Add data
                for asg in all_assignments:
                    ws.append([
                        asg['assignment_id'],
                        asg['employee_id'],
                        asg['employee_name'],
                        asg['department'],
                        asg['month'],
                        asg['assigned_salary'],
                        asg['assigned_on'],
                        asg['assigned_by'],
                    ])
                
                # Format salary column
                for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=6, max_col=6):
                    for cell in row:
                        cell.number_format = '#,##0.00'
                        cell.alignment = Alignment(horizontal="right")
                
                # Auto-adjust column widths (skip merged cells)
                for column in ws.columns:
                    max_length = 0
                    column_letter = None
                    for cell in column:
                        # Get column_letter from first valid cell
                        try:
                            if column_letter is None and hasattr(cell, 'column_letter'):
                                column_letter = cell.column_letter
                            if cell.value and len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    if column_letter:
                        adjusted_width = min(max_length + 2, 50)
                        ws.column_dimensions[column_letter].width = adjusted_width
                
                wb.save(filename)
                messagebox.showinfo("Export Successful", f"Assigned salaries exported to:\n{filename}")
                
            except ImportError:
                # Fallback to CSV format
                import csv
                
                out_dir = Path("salary_exports")
                out_dir.mkdir(exist_ok=True)
                filename = out_dir / f"assigned_salaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Assignment ID", "Employee ID", "Employee Name", "Department", 
                                    "Month", "Assigned Salary (NET)", "Assigned On", "Assigned By"])
                    for asg in all_assignments:
                        writer.writerow([
                            asg['assignment_id'],
                            asg['employee_id'],
                            asg['employee_name'],
                            asg['department'],
                            asg['month'],
                            f"{asg['assigned_salary']:,.2f}",
                            asg['assigned_on'],
                            asg['assigned_by'],
                        ])
                
                messagebox.showinfo(
                    "Export Successful", 
                    f"Assigned salaries exported to CSV:\n{filename}\n\n"
                    "Note: For Excel format (.xlsx), install openpyxl:\npip install openpyxl"
                )
                
        except Exception as exc:
            messagebox.showerror("Export Error", f"Failed to export assigned salaries:\n{str(exc)}")

    def export_employee_salaries_to_excel(self, emp_id: str, emp_name: str, assignments: list):
        """
        Export assigned salaries for a specific employee to Excel.
        
        Args:
            emp_id: Employee ID
            emp_name: Employee name
            assignments: List of assignment records for the employee
        """
        try:
            if not assignments:
                messagebox.showinfo("No Data", f"No assigned salaries found for {emp_name}.")
                return
            
            # Sort by month (newest first)
            assignments_sorted = sorted(assignments, key=lambda x: x.get('month', ''), reverse=True)
            
            # Try to use openpyxl for Excel format, otherwise use CSV
            try:
                openpyxl = importlib.import_module("openpyxl")
                openpyxl_styles = importlib.import_module("openpyxl.styles")
                Font = openpyxl_styles.Font
                PatternFill = openpyxl_styles.PatternFill
                Alignment = openpyxl_styles.Alignment
                
                # Create Excel file
                out_dir = Path("salary_exports")
                out_dir.mkdir(exist_ok=True)
                filename = out_dir / f"{emp_id}_salary_assignments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Salary Assignments"
                
                # Add employee info at top
                ws['A1'] = f"Employee Salary Assignments Report"
                ws['A1'].font = Font(size=14, bold=True, color="366092")
                ws['A2'] = f"Employee ID: {emp_id}"
                ws['A3'] = f"Employee Name: {emp_name}"
                ws.merge_cells('A1:H1')
                
                # Headers (starting from row 5)
                headers = ["Month", "Assigned Salary (Rs)", "Assigned On", "Assigned By", "Assignment ID"]
                for col, header in enumerate(headers, 1):
                    cell = ws.cell(row=5, column=col)
                    cell.value = header
                    cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                
                # Add data
                for row_idx, asg in enumerate(assignments_sorted, 6):
                    ws.cell(row=row_idx, column=1).value = asg.get('month', '')
                    ws.cell(row=row_idx, column=2).value = asg.get('assigned_salary', 0)
                    ws.cell(row=row_idx, column=3).value = asg.get('assigned_on', '')
                    ws.cell(row=row_idx, column=4).value = asg.get('assigned_by', '')
                    ws.cell(row=row_idx, column=5).value = asg.get('id', '')
                
                # Format salary column
                for row in ws.iter_rows(min_row=6, max_row=ws.max_row, min_col=2, max_col=2):
                    for cell in row:
                        cell.number_format = '#,##0.00'
                        cell.alignment = Alignment(horizontal="right")
                
                # Auto-adjust column widths (skip merged cells)
                for column in ws.columns:
                    max_length = 0
                    column_letter = None
                    for cell in column:
                        # Get column_letter from first valid cell
                        try:
                            if column_letter is None and hasattr(cell, 'column_letter'):
                                column_letter = cell.column_letter
                            if cell.value and len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    if column_letter:
                        adjusted_width = min(max_length + 2, 50)
                        ws.column_dimensions[column_letter].width = adjusted_width
                
                wb.save(filename)
                messagebox.showinfo("Export Successful", f"Assigned salaries for {emp_name} exported to:\n{filename}")
                
            except ImportError:
                # Fallback to CSV format
                import csv
                
                out_dir = Path("salary_exports")
                out_dir.mkdir(exist_ok=True)
                filename = out_dir / f"{emp_id}_salary_assignments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([f"Employee Salary Assignments - {emp_name} ({emp_id})"])
                    writer.writerow([])  # Empty row for spacing
                    writer.writerow(["Month", "Assigned Salary (Rs)", "Assigned On", "Assigned By", "Assignment ID"])
                    for asg in assignments_sorted:
                        writer.writerow([
                            asg.get('month', ''),
                            f"{asg.get('assigned_salary', 0):,.2f}",
                            asg.get('assigned_on', ''),
                            asg.get('assigned_by', ''),
                            asg.get('id', ''),
                        ])
                
                messagebox.showinfo(
                    "Export Successful", 
                    f"Assigned salaries for {emp_name} exported to CSV:\n{filename}\n\n"
                    "Note: For Excel format (.xlsx), install openpyxl:\npip install openpyxl"
                )
                
        except Exception as exc:
            messagebox.showerror("Export Error", f"Failed to export assigned salaries:\n{str(exc)}")

    def view_assignments_dialog(self, emp_id: str | None = None):
        # If emp_id unspecified, use selected in table
        if not emp_id:
            selected = getattr(self, 'emp_tree', None).selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select an employee to view assignments.")
                return
            emp_id = self.emp_tree.item(selected[0])["values"][0]

        emp = self.employee_repo.get_employee(emp_id)
        if not emp:
            messagebox.showerror("Error", "Employee not found.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Salary Assignments - {emp['name']} ({emp['id']})")
        dialog.geometry("950x480")
        dialog.transient(self.root)
        dialog.grab_set()

        # Header with employee info and base salary
        header_frame = tk.Frame(dialog, bg="#f5f5f5")
        header_frame.pack(fill="x", padx=12, pady=10)
        
        tk.Label(header_frame, text=f"Monthly Salary Assignments for {emp['name']}", 
                font=("Arial", 14, "bold"), bg="#f5f5f5").pack(anchor="w", pady=5)
        
        base_salary = float(emp.get("salary", 0))
        tk.Label(header_frame, 
                text=f"Base Salary (Employee Account): Rs. {base_salary:,.2f}  |  "
                     f"ID: {emp['id']}  |  Department: {emp.get('department', 'N/A')}", 
                font=("Arial", 10), bg="#f5f5f5", fg="#555").pack(anchor="w", pady=2)
        
        info_label = tk.Label(header_frame, 
                text="Note: These are monthly salary assignments for payroll calculation. Deleting an assignment will not change the employee's base salary.",
                font=("Arial", 9), bg="#FFF8E1", fg="#F57F17", padx=8, pady=4)
        info_label.pack(anchor="w", pady=5, fill="x")

        frame = tk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=12, pady=8)

        cols = ("ID", "Month", "Assigned Salary", "Bonus", "NET Salary", "Assigned On", "Assigned By")
        tf, tree, vscroll, xscroll = self._create_table_with_scroll(frame, cols, height=10, enable_xscroll=True)
        # helper already sets up and packs the tree
        for c in cols:
            tree.heading(c, text=c)
            if c in ("Assigned Salary", "Bonus", "NET Salary"):
                tree.column(c, width=140, anchor="e")
            elif c == "Month":
                tree.column(c, width=100)
            else:
                tree.column(c, width=140)

        rows = self.assignment_repo.list_assignments(emp['id'])
        for r in rows:
            assigned_sal = float(r.get('assigned_salary', 0))
            bonus = float(r.get('bonus', 0))
            net_sal = assigned_sal + bonus  # NET = Assigned + Bonus (leaves already deducted)
            
            tree.insert("", "end", values=(
                r.get('id'), 
                r.get('month'), 
                f"Rs. {assigned_sal:,.2f}",
                f"Rs. {bonus:,.2f}",
                f"Rs. {net_sal:,.2f}",
                r.get('assigned_on'), 
                r.get('assigned_by', 'N/A')
            ))

        def delete_selected_assignment():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Warning", "Please select an assignment to delete.")
                return
            asg_id = tree.item(sel[0])['values'][0]
            month = tree.item(sel[0])['values'][1]
            
            if not messagebox.askyesno("Confirm", 
                f"Are you sure you want to delete the salary assignment for {month}?\n\n"
                "Note: This will only remove the monthly assignment, not change the employee's base salary."):
                return
            
            try:
                self.assignment_repo.delete_assignment(asg_id)
                messagebox.showinfo("Success", f"Assignment {asg_id} for {month} has been deleted.\n"
                                   "The employee's base salary remains unchanged.\n"
                                   "You can now assign a different salary for this month if needed.")
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to delete assignment: {exc}")
                return
            
            # Refresh the assignments list
            dialog.destroy()
            self.view_assignments_dialog(emp_id)

        btn_frame = tk.Frame(dialog, bg="white")
        btn_frame.pack(pady=10, fill="x")
        
        tk.Button(btn_frame, text="Delete Assignment", command=delete_selected_assignment, 
                 bg="#f44336", fg="white", font=("Arial", 11), width=20).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Close", command=dialog.destroy, 
                 bg="#607D8B", fg="white", font=("Arial", 11), width=20).pack(side="left", padx=5)
    
    def show_leave_application(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.content_frame, text="Leave Application", font=("Arial", 18, "bold"), bg="white").pack(pady=20)
        
        form_frame = tk.Frame(self.content_frame, bg="white")
        form_frame.pack(pady=20)
        
        tk.Label(form_frame, text="Leave Type:", font=("Arial", 11), bg="white").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        leave_type = ttk.Combobox(form_frame, values=["Sick Leave", "Casual Leave", "Vacation", "Personal Leave"], font=("Arial", 11), width=25, state="readonly")
        leave_type.set("Sick Leave")
        leave_type.grid(row=0, column=1, padx=10, pady=10)
        
        tk.Label(form_frame, text="From Date:", font=("Arial", 11), bg="white").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        start_date = DateEntry(form_frame, font=("Arial", 11), width=24, background='darkblue', 
                              foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        start_date.grid(row=1, column=1, padx=10, pady=10)
        
        tk.Label(form_frame, text="To Date:", font=("Arial", 11), bg="white").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        end_date = DateEntry(form_frame, font=("Arial", 11), width=24, background='darkblue', 
                            foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        end_date.grid(row=2, column=1, padx=10, pady=10)

        tk.Label(form_frame, text="Duration:", font=("Arial", 11), bg="white").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        duration_combo = ttk.Combobox(
            form_frame,
            values=["Full Day", "Half Day"],
            font=("Arial", 11),
            width=25,
            state="readonly",
        )
        duration_combo.set("Full Day")
        duration_combo.grid(row=3, column=1, padx=10, pady=10)

        # Allow ESC to close any open From/To date calendars on this screen
        def close_main_calendars(event=None):
            for de in (start_date, end_date):
                try:
                    # If the calendar widget exists and is currently shown, toggle it (which hides it)
                    if hasattr(de, "_calendar") and de._calendar.winfo_ismapped():
                        de.drop_down()
                except Exception:
                    # Safely ignore any tk/tkcalendar internal errors
                    pass

        self.root.bind("<Escape>", close_main_calendars)
        
        tk.Label(form_frame, text="Reason:", font=("Arial", 11), bg="white").grid(row=4, column=0, padx=10, pady=10, sticky="nw")
        reason = tk.Text(form_frame, font=("Arial", 11), width=27, height=4)
        reason.grid(row=4, column=1, padx=10, pady=10)
        
        def submit_leave():
            new_leave = {
                "id": self.generate_new_leave_id(),
                "emp_id": self.current_user["id"],
                "emp_name": self.current_user["name"],
                "leave_type": leave_type.get(),
                "start_date": start_date.get_date().strftime("%Y-%m-%d"),
                "end_date": end_date.get_date().strftime("%Y-%m-%d"),
                "reason": reason.get("1.0", "end-1c"),
                "status": "Pending",
                "applied_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duration_type": duration_combo.get(),
            }
            
            if not all([new_leave["leave_type"], new_leave["reason"]]):
                messagebox.showerror("Error", "Please fill all fields!")
                return
            
            # Validate that the From (start) date is not after the To (end) date
            if start_date.get_date() > end_date.get_date():
                messagebox.showerror("Error", "From date cannot be after To date!")
                return
            
            self.leave_repo.add_leave(new_leave)
            self.refresh_leaves()
            messagebox.showinfo("Success", "Leave application submitted successfully!")
            leave_type.set("Sick Leave")
            reason.delete("1.0", "end")
            duration_combo.set("Full Day")
            self.show_my_leaves()
        
        tk.Button(form_frame, text="Submit Application", command=submit_leave, bg="#4CAF50", fg="white", 
                 font=("Arial", 12), width=20).grid(row=5, column=0, columnspan=2, pady=20)
        
        tk.Button(self.content_frame, text="View My Leaves", command=self.show_my_leaves, 
                 bg="#2196F3", fg="white", font=("Arial", 11), width=20).pack(pady=10)
    
    def show_my_leaves(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.content_frame, text="My Leave Applications", font=("Arial", 18, "bold"), bg="white").pack(pady=20)
        
        tk.Button(self.content_frame, text="← Back to Application", command=self.show_leave_application, 
                 bg="#607D8B", fg="white", font=("Arial", 10)).pack(pady=5)
        
        cols = ("ID", "Type", "Start", "End", "Duration", "Status", "Applied")
        tree_frame, self.my_leave_tree, my_leave_vscroll, my_leave_xscroll = self._create_table_with_scroll(self.content_frame, cols, height=12, enable_xscroll=True)

        for col in cols:
            self.my_leave_tree.heading(col, text=col)
            self.my_leave_tree.column(col, width=120)

        # Reload from DB and filter leaves for current user
        self.refresh_leaves()
        my_leaves = self.leave_repo.leaves_for_employee(self.current_user["id"])
        for leave in my_leaves:
            self.my_leave_tree.insert("", "end", values=(
                leave["id"], leave["leave_type"], leave["start_date"], leave["end_date"], 
                leave.get("duration_type", "Full Day"), leave["status"], leave["applied_date"]
            ))

        # tree already packed by helper
        
        # Action Buttons
        btn_frame = tk.Frame(self.content_frame, bg="white")
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Edit Leave", command=self.edit_leave_application, 
                 bg="#FF9800", fg="white", font=("Arial", 10), width=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="View Details", command=self.view_my_leave_details, 
                 bg="#2196F3", fg="white", font=("Arial", 10), width=15).pack(side="left", padx=5)
    
    def edit_leave_application(self):
        selected = self.my_leave_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a leave application to edit!")
            return
        
        leave_id = self.my_leave_tree.item(selected[0])["values"][0]
        leave = self.leave_repo.get_leave(leave_id)
        
        if not leave:
            messagebox.showerror("Error", "Unable to load leave details.")
            return
        
        if leave["status"] != "Pending":
            messagebox.showwarning("Warning", f"Cannot edit leave application! Status is already {leave['status']}.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Leave Application")
        dialog.geometry("450x450")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Leave Type:", font=("Arial", 11)).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        leave_type = ttk.Combobox(dialog, values=["Sick Leave", "Casual Leave", "Vacation", "Personal Leave"], 
                                 font=("Arial", 11), width=25, state="readonly")
        leave_type.set(leave["leave_type"])
        leave_type.grid(row=0, column=1, padx=20, pady=10)
        
        tk.Label(dialog, text="From Date:", font=("Arial", 11)).grid(row=1, column=0, padx=20, pady=10, sticky="w")
        start_date = DateEntry(dialog, font=("Arial", 11), width=24, background='darkblue', 
                              foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        start_date.set_date(self._normalize_date(leave.get("start_date")))
        start_date.grid(row=1, column=1, padx=20, pady=10)
        
        tk.Label(dialog, text="To Date:", font=("Arial", 11)).grid(row=2, column=0, padx=20, pady=10, sticky="w")
        end_date = DateEntry(dialog, font=("Arial", 11), width=24, background='darkblue', 
                            foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        end_date.set_date(self._normalize_date(leave.get("end_date")))
        end_date.grid(row=2, column=1, padx=20, pady=10)
        
        tk.Label(dialog, text="Duration:", font=("Arial", 11)).grid(row=3, column=0, padx=20, pady=10, sticky="w")
        duration_combo = ttk.Combobox(
            dialog,
            values=["Full Day", "Half Day"],
            font=("Arial", 11),
            width=25,
            state="readonly",
        )
        duration_combo.set(leave.get("duration_type", "Full Day"))
        duration_combo.grid(row=3, column=1, padx=20, pady=10)

        tk.Label(dialog, text="Reason:", font=("Arial", 11)).grid(row=4, column=0, padx=20, pady=10, sticky="nw")
        reason = tk.Text(dialog, font=("Arial", 11), width=27, height=5)
        reason.insert("1.0", leave["reason"])
        reason.grid(row=4, column=1, padx=20, pady=10)

        # Allow ESC to first close any open calendars using DateEntry's own API, then close the dialog
        def on_dialog_escape(event=None):
            closed_calendar = False
            for de in (start_date, end_date):
                try:
                    if hasattr(de, "_calendar") and de._calendar.winfo_ismapped():
                        de.drop_down()  # toggles and hides the calendar
                        closed_calendar = True
                except Exception:
                    # Ignore internal tk/tkcalendar errors safely
                    pass
            if not closed_calendar:
                dialog.destroy()

        dialog.bind("<Escape>", on_dialog_escape)
        
        def update_leave():
            # Validate that the From (start) date is not after the To (end) date
            if start_date.get_date() > end_date.get_date():
                messagebox.showerror("Error", "From date cannot be after To date!")
                return
            
            self.leave_repo.update_leave(
                    leave_id,
                {
                    "leave_type": leave_type.get(),
                    "start_date": start_date.get_date().strftime("%Y-%m-%d"),
                    "end_date": end_date.get_date().strftime("%Y-%m-%d"),
                    "reason": reason.get("1.0", "end-1c"),
                    "duration_type": duration_combo.get(),
                },
            )
            self.refresh_leaves()
            messagebox.showinfo("Success", "Leave application updated successfully!")
            dialog.destroy()
            self.show_my_leaves()
        
        tk.Button(dialog, text="Update", command=update_leave, bg="#FF9800", fg="white", 
                 font=("Arial", 12), width=15).grid(row=5, column=0, columnspan=2, pady=20)
    
    def view_my_leave_details(self):
        selected = self.my_leave_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a leave application!")
            return
        
        leave_id = self.my_leave_tree.item(selected[0])["values"][0]
        leave = self.leave_repo.get_leave(leave_id)
        
        if leave:
            details = f"""Leave ID: {leave['id']}
Leave Type: {leave['leave_type']}
Start Date: {leave['start_date']}
End Date: {leave['end_date']}
Duration: {leave.get('duration_type', 'Full Day')}
Status: {leave['status']}
Applied Date: {leave['applied_date']}

Reason:
{leave['reason']}"""
            
            messagebox.showinfo("Leave Details", details)
    
    def show_leave_management(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.content_frame, text="Leave Requests Management", font=("Arial", 18, "bold"), bg="white").pack(pady=20)
        
        # Filter tabs
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
        
        # Statistics
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
        
        # tree already packed by helper
        
        # Action Buttons
        btn_frame = tk.Frame(self.content_frame, bg="white")
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Approve", command=lambda: self.update_leave_status("Approved"), 
                 bg="#4CAF50", fg="white", font=("Arial", 10), width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Reject", command=lambda: self.update_leave_status("Rejected"), 
                 bg="#f44336", fg="white", font=("Arial", 10), width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="View Details", command=self.view_leave_details, 
                 bg="#2196F3", fg="white", font=("Arial", 10), width=12).pack(side="left", padx=5)
    
    def refresh_leave_list(self):
        # Clear existing items
        for item in self.leave_tree.get_children():
            self.leave_tree.delete(item)
        
        # Refresh from DB
        self.refresh_leaves()

        # Filter leaves based on selection
        filter_value = self.leave_filter.get()
        if filter_value == "All":
            filtered_leaves = self.leaves
        else:
            filtered_leaves = [l for l in self.leaves if l["status"] == filter_value]
        
        # Insert filtered leaves
        for leave in filtered_leaves:
            self.leave_tree.insert("", "end", values=(
                leave["id"], leave["emp_name"], leave["leave_type"], 
                leave["start_date"], leave["end_date"], leave.get("duration_type", "Full Day"), leave["status"]
            ))
    
    def update_leave_status(self, status):
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
        selected = self.leave_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a leave request!")
            return
        
        leave_id = self.leave_tree.item(selected[0])["values"][0]
        # Ensure we have latest data
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
        """Show Salary Correction Requests management module"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        tk.Label(self.content_frame, text="Payroll/Salary Correction Requests", font=("Arial", 18, "bold"), bg="white").pack(pady=20)

        # Filtering controls (status, employee, start date, end date)
        filter_frame = tk.Frame(self.content_frame, bg="white")
        filter_frame.pack(fill="x", padx=20, pady=8)

        tk.Label(filter_frame, text="Status:", font=("Arial", 10), bg="white").grid(row=0, column=0, padx=6, sticky="w")
        # Include 'Rejected' so admin can filter by rejected requests
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
                    notes_or_reason = r.get("rejection_reason", "")[:50]  # First 50 chars
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
                    import csv
                    writer = csv.writer(f)
                    writer.writerow(["ID", "Emp ID", "Month", "Description", "Submitted On", "Status", "Admin Notes", "Rejection Reason"])
                    for r in rows:
                        writer.writerow([r.get('id'), r.get('emp_id'), r.get('month'), r.get('description'), r.get('submitted_on'), r.get('status'), r.get('admin_notes', ''), r.get('rejection_reason', '')])
                messagebox.showinfo("Exported", f"Corrections exported to {filename}")
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to export: {exc}")


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
                
                # Notify employee
                try:
                    employee_email = emp.get("email")
                    employee_name = emp.get("name")
                    from notifier import notify_correction_approved_with_assignment
                    notify_correction_approved_with_assignment(employee_email, employee_name, req_id, notes, month, new_salary, 0)
                except Exception:
                    pass
                
                dialog.destroy()
                apply_filters()

            btn_frame = tk.Frame(dialog)
            btn_frame.pack(pady=10)
            tk.Button(btn_frame, text="Approve & Save", command=save_approval, bg="#4CAF50", fg="white", font=("Arial", 11), width=16).pack(side="left", padx=6)
            tk.Button(btn_frame, text="Cancel", command=dialog.destroy, font=("Arial", 11), width=12).pack(side="left", padx=6)

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
        self.root.mainloop()

if __name__ == "__main__":
    app = EmployeeManagementSystem()
    app.run()