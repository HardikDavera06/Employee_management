"""
admin_dashboard.py - Admin Dashboard Module
Contains all admin-related UI and functionality for employee management, payroll, and leave management.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
from pathlib import Path
import csv
import importlib


class AdminDashboard:
    """Admin dashboard functionality for the Employee Management System."""
    
    def __init__(self, app):
        """
        Initialize the admin dashboard.
        
        Args:
            app: Main EmployeeManagementSystem instance
        """
        self.app = app
    
    def show_admin_dashboard(self):
        """Display the main admin dashboard layout."""
        self.app.clear_window()
        
        # Top bar
        top_frame = tk.Frame(self.app.root, bg="#2196F3", height=60)
        top_frame.pack(fill="x")
        
        tk.Label(top_frame, text=f"🏢  Admin Dashboard - Welcome {self.app.current_user['name']}", 
                font=("Arial", 16, "bold"), bg="#2196F3", fg="white").pack(side="left", padx=20, pady=15)

        # Profile button on top bar (icon-only)
        if self.app.profile_icon:
            tk.Button(
                top_frame,
                image=self.app.profile_icon,
                command=self.app.show_profile_dialog,
                bg="#2196F3",
                activebackground="#2196F3",
                bd=0,
                highlightthickness=0,
                cursor="hand2",
            ).pack(side="right", padx=10, pady=10)
        else:
            tk.Button(
                top_frame,
                text="👤",
                command=self.app.show_profile_dialog,
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
        
        # Sidebar
        sidebar = tk.Frame(self.app.root, bg="#0B2545", width=220)
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
        self.app._create_scrolled_content()

        self.show_admin_dashboard_home()
    
    def show_admin_dashboard_home(self):
        """Display the admin dashboard home page with statistics."""
        for widget in self.app.content_frame.winfo_children():
            widget.destroy()

        tk.Label(self.app.content_frame, text="Admin Dashboard", font=("Arial", 18, "bold"), bg="white").pack(pady=(12, 8))

        # Ensure latest data from DB
        self.app.refresh_employees()
        self.app.refresh_leaves()

        # Top stats row (responsive)
        stats_row = tk.Frame(self.app.content_frame, bg="white")
        stats_row.pack(fill="x", padx=20)

        total_emps = len(self.app.employees)
        total_leaves = len(self.app.leaves)
        pending_leaves_count = len([l for l in self.app.leaves if l["status"] == "Pending"])
        approved_count = len([l for l in self.app.leaves if l["status"] == "Approved"])
        rejected_count = len([l for l in self.app.leaves if l["status"] == "Rejected"])

        # Use horizontal cards for a cleaner dashboard
        self.app._make_stat_card(stats_row, "Total Employees", str(total_emps), "#2E7D32", "👥", onclick=self.show_employee_management).pack(side="left", padx=10, pady=6, expand=True, fill="x")
        self.app._make_stat_card(stats_row, "Total Leave Apps", str(total_leaves), "#1565C0", "📝").pack(side="left", padx=10, pady=6, expand=True, fill="x")
        self.app._make_stat_card(stats_row, "Pending Requests", str(pending_leaves_count), "#F57C00", "⏳", onclick=self.show_leave_management).pack(side="left", padx=10, pady=6, expand=True, fill="x")
        self.app._make_stat_card(stats_row, "Net Approvals", str(approved_count), "#388E3C", "✅").pack(side="left", padx=10, pady=6, expand=True, fill="x")

        # Main area: two-column layout
        main_area = tk.Frame(self.app.content_frame, bg="white")
        main_area.pack(fill="both", expand=True, padx=20, pady=(10,20))
        main_area.grid_columnconfigure(0, weight=3)
        main_area.grid_columnconfigure(1, weight=1)

        # Left: Pending corrections + recent payroll table
        left_frame = tk.Frame(main_area, bg="white")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        tk.Label(left_frame, text="Pending Salary Correction Requests", font=("Arial", 14, "bold"), bg="white").pack(anchor="w", pady=(6,8))
        pending_corr_rows = self.app.correction_repo.list_corrections_filtered(status="Pending")
        cols = ("ID", "Emp ID", "Month", "Submitted On")
        corr_frame_inner, ctree, corr_vscroll, corr_xscroll = self.app._create_table_with_scroll(left_frame, cols, height=12, enable_xscroll=True)
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
    
    def show_employee_management(self):
        """Display employee management interface."""
        for widget in self.app.content_frame.winfo_children():
            widget.destroy()

        # Refresh from DB
        self.app.refresh_employees()
        
        tk.Label(self.app.content_frame, text="Employee Management", font=("Arial", 18, "bold"), bg="white").pack(pady=20)
        
        # Add Employee Button
        tk.Button(self.app.content_frame, text="+ Add New Employee", command=self.add_employee_dialog, 
                 bg="#4CAF50", fg="white", font=("Arial", 11), width=20).pack(pady=10)
        
        # Employee List with Actions column included in table
        columns = ("ID", "Name", "Email", "Phone", "Department", "Role", "Salary (Yearly)", "Actions")
        tree_frame, self.app.emp_tree, emp_vscroll, emp_xscroll = self.app._create_table_with_scroll(
            self.app.content_frame,
            columns,
            height=12,
            enable_xscroll=True,
        )
        
        for i, col in enumerate(columns):
            self.app.emp_tree.heading(col, text=col)
            if col == "Salary (Yearly)":
                self.app.emp_tree.column(col, width=160, anchor="e")
            elif col == "Actions":
                self.app.emp_tree.column(col, width=150, anchor="center")
            else:
                self.app.emp_tree.column(col, width=120)
        
        # Store which items have action buttons
        self.app.emp_tree._action_items = {}
        self.app.emp_tree._hovered_item = None
        
        for emp in self.app.employees:
            yearly_salary = float(emp.get("salary", 0)) * 12
            item_id = self.app.emp_tree.insert(
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
                    "▶ Assign Salary",
                ),
                tags=("action_row",)
            )
            self.app.emp_tree._action_items[item_id] = emp["id"]
        
        # Bind click on the Actions column
        self.app.emp_tree.bind("<Button-1>", self.app._on_emp_tree_click)
        self.app.emp_tree.bind("<Motion>", self.app._on_emp_tree_motion)
        self.app.emp_tree.bind("<Leave>", self.app._on_emp_tree_leave)
        
        # Configure tags for styling
        self.app.emp_tree.tag_configure("action_row", background="white")
        self.app.emp_tree.tag_configure("action_hover", background="#E8F5E9")
        
        # Action Buttons
        btn_frame = tk.Frame(self.app.content_frame, bg="white")
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Edit", command=self.edit_employee, bg="#2196F3", fg="white", 
             font=("Arial", 10), width=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_employee, bg="#f44336", fg="white", 
             font=("Arial", 10), width=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="View Assignments", command=self.view_assignments_dialog, bg="#FF9800", fg="white", 
             font=("Arial", 10), width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Export to Excel", command=self.export_assigned_salaries_to_excel, bg="#4CAF50", fg="white", 
             font=("Arial", 10), width=14).pack(side="left", padx=5)
    
    def add_employee_dialog(self):
        """Open dialog to add a new employee."""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Add New Employee")
        dialog.geometry("480x420")
        dialog.resizable(False, False)
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        departments = ["Human Resources", "Engineering", "Marketing", "Sales", "Finance", "Operations", "IT", "Management"]
        
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
        phone_vcmd = (self.app.root.register(self.app.validate_phone_input), "%P")
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
            emp_id = self.app.generate_new_employee_id()
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
            
            # Check if email already exists
            if self.app.employee_repo.email_exists(new_emp["email"]):
                messagebox.showerror("Error", "This email is already registered!")
                return
            
            # Check if phone already exists
            if self.app.employee_repo.phone_exists(new_emp["phone"]):
                messagebox.showerror("Error", "This phone number is already registered!")
                return
            
            self.app.employee_repo.add_employee(new_emp)
            self.app.refresh_employees()
            messagebox.showinfo("Success", f"Employee added successfully! ID: {emp_id}")
            dialog.destroy()
            self.show_employee_management()
        
        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=18)
        tk.Button(btn_frame, text="Save", command=save_employee, bg="#4CAF50", fg="white", font=("Arial", 12), width=14).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, bg="#f44336", fg="white", font=("Arial", 12), width=14).pack(side="left", padx=8)

        name_entry.focus_set()
        dialog.bind('<Return>', lambda e: save_employee())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def edit_employee(self):
        """Open dialog to edit selected employee."""
        selected = self.app.emp_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an employee to edit!")
            return
        
        emp_id = self.app.emp_tree.item(selected[0])["values"][0]
        emp = self.app.employee_repo.get_employee(emp_id)
        
        if not emp:
            messagebox.showerror("Error", "Unable to load employee details.")
            return
        
        dialog = tk.Toplevel(self.app.root)
        dialog.title(f"Edit Employee - {emp['name']}")
        dialog.geometry("500x600")
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.resizable(True, True)
        
        dialog.columnconfigure(1, weight=1)
        
        label_font = ("Arial", 11)
        entry_font = ("Arial", 11)
        button_font = ("Arial", 11, "bold")
        padx = 20
        pady = 8
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        title_label = ttk.Label(
            main_frame, 
            text="Edit Employee Details",
            font=("Arial", 14, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")
        
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
            
            label = ttk.Label(main_frame, text=label_text, font=label_font)
            label.grid(row=i, column=0, padx=padx, pady=pady, sticky="e")
            
            if field_type == "entry" or field_type == "phone":
                entry = ttk.Entry(main_frame, font=entry_font, width=30)
                entry.insert(0, str(emp.get(field_name, "")))
                entry.grid(row=i, column=1, padx=padx, pady=pady, sticky="ew")
                entries[field_name] = entry
                
                if field_type == "phone":
                    phone_vcmd = (self.app.root.register(self.app.validate_phone_input), "%P")
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
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=20)
        
        def update_employee():
            phone = entries["phone"].get()
            if not (phone.isdigit() and len(phone) == 10):
                messagebox.showerror("Error", "Phone number must be exactly 10 digits!")
                return

            try:
                salary_value = float(entries["salary"].get())
                if salary_value < 0:
                    raise ValueError("Salary cannot be negative")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid positive number for salary!")
                return

            try:
                self.app.employee_repo.update_employee(
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
                self.app.refresh_employees()
                messagebox.showinfo("Success", "Employee updated successfully!")
                dialog.destroy()
                self.show_employee_management()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update employee: {str(e)}")
        
        update_btn = ttk.Button(
            button_frame, 
            text="Update Employee", 
            command=update_employee,
            style="Accent.TButton"
        )
        update_btn.pack(side="left", padx=5)
       
        style = ttk.Style()
        style.configure("Accent.TButton", font=button_font, padding=6)
        style.configure("Secondary.TButton", font=button_font, padding=6)
        
        main_frame.columnconfigure(1, weight=1)
        
        entries["name"].focus_set()
        
        dialog.bind("<Return>", lambda e: update_employee())
        
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def delete_employee(self):
        """Delete the selected employee."""
        selected = self.app.emp_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an employee to delete!")
            return
        
        emp_id = self.app.emp_tree.item(selected[0])["values"][0]
        
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this employee?"):
            self.app.employee_repo.delete_employee(emp_id)
            self.app.refresh_employees()
            messagebox.showinfo("Success", "Employee deleted successfully!")
            self.show_employee_management()

    def assign_salary_dialog(self, emp_id: str | None = None, month_value: str | None = None):
        """Open dialog to assign salary to an employee."""
        # If emp_id unspecified, use selected in table
        if not emp_id:
            selected = getattr(self.app, 'emp_tree', None).selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select an employee to assign salary.")
                return
            emp_id = self.app.emp_tree.item(selected[0])["values"][0]

        emp = self.app.employee_repo.get_employee(emp_id)
        if not emp:
            messagebox.showerror("Error", "Employee not found.")
            return

        dialog = tk.Toplevel(self.app.root)
        dialog.title(f"Assign Salary - {emp['name']} ({emp['id']})")
        dialog.geometry("580x500")
        dialog.transient(self.app.root)
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
        admin_entry.insert(0, self.app.current_user.get("id") if self.app.current_user else "")
        admin_entry.grid(row=6, column=1, pady=6, sticky="w")

        def calculate_net_salary():
            """Calculate NET salary (base + bonus - leave deductions)"""
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
                self.app.refresh_leaves()
                
                # Calculate leave deduction
                try:
                    leave_days, leave_deduction = self.app.calculate_leave_deduction(emp['id'], month_val, base_salary)
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
            
            admin_id = admin_entry.get().strip() or (self.app.current_user.get("id") if self.app.current_user else None)
            
            # Make a new assignment record with NET salary
            asg_id = self.app.assignment_repo.generate_assignment_id()
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
                self.app.assignment_repo.add_assignment(record)
                # Update current employee base salary (not NET salary)
                base_salary_val = float(base_salary_var.get())
                self.app.employee_repo.update_employee(emp['id'], {
                    "name": emp['name'],
                    "email": emp['email'],
                    "phone": emp['phone'],
                    "department": emp['department'],
                    "role": emp['role'],
                    "salary": base_salary_val,  # Store base salary, not NET
                })
                self.app.refresh_employees()
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
            assignments = self.app.assignment_repo.list_assignments(emp['id'])
            if not assignments:
                messagebox.showinfo("No Data", f"No assigned salaries found for {emp['name']}.")
                return
            
            self.export_employee_salaries_to_excel(emp['id'], emp['name'], assignments)
        
        tk.Button(btn_frame, text="📊 Export Excel", bg="#2196F3", fg="white", command=export_employee_assignments, font=("Arial", 10)).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Assign NET Salary", bg="#4CAF50", fg="white", command=do_assign, font=("Arial", 11, "bold"), width=15).pack(side="right", padx=12)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, font=("Arial", 11), width=10).pack(side="right")

    def view_assignments_dialog(self, emp_id: str | None = None):
        """Display salary assignments for an employee."""
        if not emp_id:
            selected = getattr(self.app, 'emp_tree', None).selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select an employee to view assignments.")
                return
            emp_id = self.app.emp_tree.item(selected[0])["values"][0]

        emp = self.app.employee_repo.get_employee(emp_id)
        if not emp:
            messagebox.showerror("Error", "Employee not found.")
            return

        dialog = tk.Toplevel(self.app.root)
        dialog.title(f"Salary Assignments - {emp['name']} ({emp['id']})")
        dialog.geometry("950x480")
        dialog.transient(self.app.root)
        dialog.grab_set()

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
        tf, tree, vscroll, xscroll = self.app._create_table_with_scroll(frame, cols, height=10, enable_xscroll=True)
        
        for c in cols:
            tree.heading(c, text=c)
            if c in ("Assigned Salary", "Bonus", "NET Salary"):
                tree.column(c, width=140, anchor="e")
            elif c == "Month":
                tree.column(c, width=100)
            else:
                tree.column(c, width=140)

        rows = self.app.assignment_repo.list_assignments(emp['id'])
        for r in rows:
            assigned_sal = float(r.get('assigned_salary', 0))
            bonus = float(r.get('bonus', 0))
            net_sal = assigned_sal + bonus
            
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
                self.app.assignment_repo.delete_assignment(asg_id)
                messagebox.showinfo("Success", f"Assignment {asg_id} for {month} has been deleted.\n"
                                   "The employee's base salary remains unchanged.\n"
                                   "You can now assign a different salary for this month if needed.")
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to delete assignment: {exc}")
                return
            
            dialog.destroy()
            self.view_assignments_dialog(emp_id)

        btn_frame = tk.Frame(dialog, bg="white")
        btn_frame.pack(pady=10, fill="x")
        
        tk.Button(btn_frame, text="Delete Assignment", command=delete_selected_assignment, 
                 bg="#f44336", fg="white", font=("Arial", 11), width=20).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Close", command=dialog.destroy, 
                 bg="#607D8B", fg="white", font=("Arial", 11), width=20).pack(side="left", padx=5)

    def export_assigned_salaries_to_excel(self):
        """Export all assigned salaries to Excel/CSV file."""
        try:
            all_assignments = []
            for emp in self.app.employee_repo.list_employees():
                assignments = self.app.assignment_repo.list_assignments(emp['id'])
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
            
            all_assignments.sort(key=lambda x: (x['month'], x['employee_name']), reverse=True)
            
            try:
                openpyxl = importlib.import_module("openpyxl")
                openpyxl_styles = importlib.import_module("openpyxl.styles")
                Font = openpyxl_styles.Font
                PatternFill = openpyxl_styles.PatternFill
                Alignment = openpyxl_styles.Alignment
                
                out_dir = Path("salary_exports")
                out_dir.mkdir(exist_ok=True)
                filename = out_dir / f"assigned_salaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Assigned Salaries"
                
                headers = ["Assignment ID", "Employee ID", "Employee Name", "Department", 
                          "Month", "Assigned Salary (NET)", "Assigned On", "Assigned By"]
                ws.append(headers)
                
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF")
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                
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
                
                for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=6, max_col=6):
                    for cell in row:
                        cell.number_format = '#,##0.00'
                        cell.alignment = Alignment(horizontal="right")
                
                for column in ws.columns:
                    max_length = 0
                    column_letter = None
                    for cell in column:
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
        """Export assigned salaries for a specific employee to Excel/CSV file."""
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
                
                # Auto-adjust column widths
                for column in ws.columns:
                    max_length = 0
                    column_letter = None
                    for cell in column:
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

    def show_leave_management(self):
        """Display leave request management interface."""
        # This method will be called from main employee.py
        self.app.show_leave_management()
    
    def show_payroll_management(self):
        """Display payroll management interface."""
        # This method will be called from main employee.py
        self.app.show_payroll_management()
