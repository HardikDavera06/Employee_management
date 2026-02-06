"""
employee_dashboard.py - Employee Dashboard Module
Contains all employee-related UI and functionality for leave management and personal dashboard.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
from datetime import datetime


class EmployeeDashboard:
    """Employee dashboard functionality for the Employee Management System."""
    
    def __init__(self, app):
        """
        Initialize the employee dashboard.
        
        Args:
            app: Main EmployeeManagementSystem instance
        """
        self.app = app
    
    def show_employee_dashboard(self):
        """Display the main employee dashboard layout."""
        self.app.clear_window()

        # Top bar with gradient-like effect
        top_frame = tk.Frame(self.app.root, bg="#1E88E5", height=70)
        top_frame.pack(fill="x")
        top_frame.pack_propagate(False)

        # Left side: Welcome message
        left_top = tk.Frame(top_frame, bg="#1E88E5")
        left_top.pack(side="left", padx=20, pady=15)
        
        tk.Label(left_top, text="Employee Dashboard", font=("Arial", 18, "bold"), bg="#1E88E5", fg="white").pack(anchor="w")
        tk.Label(left_top, text=f"Welcome, {self.app.current_user['name']}", font=("Arial", 11), bg="#1E88E5", fg="#E3F2FD").pack(anchor="w")

        # Right side: Profile button
        right_top = tk.Frame(top_frame, bg="#1E88E5")
        right_top.pack(side="right", padx=20, pady=15)
        
        if self.app.profile_icon:
            tk.Button(right_top, image=self.app.profile_icon, command=self.app.show_profile_dialog, bg="#1E88E5", bd=0, highlightthickness=0, cursor="hand2").pack(side="right", padx=10)
        else:
            tk.Button(right_top, text="👤", command=self.app.show_profile_dialog, font=("Arial", 16), bg="#1E88E5", fg="white", bd=0, highlightthickness=0, cursor="hand2", width=2).pack(side="right", padx=10)

        # Main container with sidebar
        main_frame = tk.Frame(self.app.root, bg="white")
        main_frame.pack(fill="both", expand=True)

        # Sidebar
        sidebar = tk.Frame(main_frame, bg="#0B2545", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Sidebar header
        sidebar_header = tk.Frame(sidebar, bg="#0D47A1", height=56)
        sidebar_header.pack(fill="x")
        sidebar_header.pack_propagate(False)
        tk.Label(sidebar_header, text="⚙️ Employee Menu", font=("Arial", 12, "bold"), bg="#0D47A1", fg="white").pack(pady=14)

        # Sidebar menu items
        menu_items = [
            ("🏠 Dashboard", self.show_employee_dashboard),
            ("💰 My Salary", self.app.salary_ui.show_my_salary),
            ("📋 Apply Leave", self.show_leave_application),
            ("📅 My Leaves", self.show_my_leaves),
            ("✅ My Requests", self.app.salary_ui.show_my_requests),
        ]

        if not hasattr(self.app, 'current_menu_item'):
            self.app.current_menu_item = None

        menu_buttons_frame = tk.Frame(sidebar, bg="#0B2545")
        menu_buttons_frame.pack(fill="both", expand=True, padx=0, pady=10)

        menu_button_refs = []

        def create_menu_click(menu_cmd, btn_ref_list, btn_widget):
            def on_click():
                for btn in btn_ref_list:
                    btn.config(bg="#0B2545", fg="#BBD1FF")
                btn_widget.config(bg="#083E78", fg="white")
                menu_cmd()
            return on_click

        for idx, (menu_text, menu_cmd) in enumerate(menu_items):
            menu_btn = tk.Button(
                menu_buttons_frame,
                text=menu_text,
                command=None,
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

        for btn, (_, menu_cmd) in zip(menu_button_refs, menu_items):
            btn.config(command=create_menu_click(menu_cmd, menu_button_refs, btn))

        if menu_button_refs:
            menu_button_refs[0].config(bg="#083E78", fg="white")

        # Sidebar footer
        sidebar_footer = tk.Frame(sidebar, bg="#0B2545", height=60)
        sidebar_footer.pack(side="bottom", fill="x")
        sidebar_footer.pack_propagate(False)

        separator = tk.Frame(sidebar_footer, bg="#0D47A1", height=2)
        separator.pack(fill="x")

        # Content area
        content_wrapper = tk.Frame(main_frame, bg="white")
        content_wrapper.pack(side="right", fill="both", expand=True)

        # Create scrollable content area
        self.app.content_canvas = tk.Canvas(content_wrapper, bg="white", highlightthickness=0)
        self.app.content_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(content_wrapper, orient="vertical", command=self.app.content_canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.app.content_canvas.configure(yscrollcommand=scrollbar.set)
        self.app.content_frame = tk.Frame(self.app.content_canvas, bg="white")
        self.app.content_window = self.app.content_canvas.create_window((0, 0), window=self.app.content_frame, anchor="nw")

        def on_frame_configure(event=None):
            self.app.content_canvas.configure(scrollregion=self.app.content_canvas.bbox("all"))
            canvas_width = self.app.content_canvas.winfo_width()
            if canvas_width > 1:
                self.app.content_canvas.itemconfig(self.app.content_window, width=canvas_width)

        self.app.content_frame.bind("<Configure>", on_frame_configure)
        self.app.content_canvas.bind("<Configure>", lambda e: self.app.content_canvas.itemconfig(self.app.content_window, width=e.width))

        # Employee stats row
        stats_row = tk.Frame(self.app.content_frame, bg="white")
        stats_row.pack(fill="x", padx=20, pady=20)

        emp = self.app.current_user or {}
        emp_salary = emp.get("salary", 0)
        emp_pending = len(self.app.correction_repo.list_corrections_filtered(emp_id=emp.get("id"), status="Pending")) if emp else 0
        
        emp_assignments = self.app.assignment_repo.list_assignments(emp.get("id") if emp else None)
        last_assignment = emp_assignments[0] if emp_assignments else None
        last_pay_text = f"{last_assignment.get('month')} — Rs. {last_assignment.get('assigned_salary', 0):,.2f}" if last_assignment else "No Assignment"

        self.app._make_stat_card(stats_row, "Monthly Salary", f"Rs. {emp_salary:,.2f}", "#2E7D32", "💵").pack(side="left", padx=10, expand=True, fill="x")
        self.app._make_stat_card(stats_row, "Pending Requests", str(emp_pending), "#F57C00", "🔔", onclick=self.app.salary_ui.show_my_requests).pack(side="left", padx=10, expand=True, fill="x")
        self.app._make_stat_card(stats_row, "Last Payslip", last_pay_text, "#1565C0", "📄").pack(side="left", padx=10, expand=True, fill="x")

        # Main content area with 2-column layout
        main_container = tk.Frame(self.app.content_frame, bg="white")
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
        
        # Action buttons
        buttons_config = [
            ("📋 Apply for Leave", self.show_leave_application, "#1E88E5"),
            ("📅 My Leaves", self.show_my_leaves, "#1565C0"),
            ("💰 Request Salary Correction", self.app.salary_ui.request_correction_on_assignment, "#FF5722"),
            ("✅ My Correction Requests", self.app.salary_ui.show_my_requests, "#F57C00"),
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

        # Salary assignments table
        assignments = emp_assignments[:10] if emp_assignments else []
        if assignments:
            cols = ("Month", "Assigned Salary", "Bonus")
            pf, ptree, pv, px = self.app._create_table_with_scroll(right_panel, cols, height=10)
            
            for c in cols:
                ptree.heading(c, text=c)
            ptree.column("Month", width=80)
            ptree.column("Assigned Salary", width=110, anchor="e")
            ptree.column("Bonus", width=80, anchor="e")
            
            for idx, a in enumerate(assignments):
                tag = "oddrow" if idx % 2 == 0 else "evenrow"
                ptree.insert("", "end", values=(
                    a.get("month"), 
                    f"Rs. {a.get('assigned_salary', 0):,.2f}",
                    f"Rs. {a.get('bonus', 0):,.2f}"
                ), tags=(tag,))
            
            ptree.tag_configure("oddrow", background="#FAFAFA")
            ptree.tag_configure("evenrow", background="white")
        else:
            tk.Label(right_panel, text="No salary assignments yet.", font=("Arial", 10), bg="white", fg="#999").pack(pady=20)

    def show_leave_application(self):
        """Display leave application form."""
        for widget in self.app.content_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.app.content_frame, text="Leave Application", font=("Arial", 18, "bold"), bg="white").pack(pady=20)
        
        form_frame = tk.Frame(self.app.content_frame, bg="white")
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

        def close_main_calendars(event=None):
            for de in (start_date, end_date):
                try:
                    if hasattr(de, "_calendar") and de._calendar.winfo_ismapped():
                        de.drop_down()
                except Exception:
                    pass

        self.app.root.bind("<Escape>", close_main_calendars)
        
        tk.Label(form_frame, text="Reason:", font=("Arial", 11), bg="white").grid(row=4, column=0, padx=10, pady=10, sticky="nw")
        reason = tk.Text(form_frame, font=("Arial", 11), width=27, height=4)
        reason.grid(row=4, column=1, padx=10, pady=10)
        
        def submit_leave():
            new_leave = {
                "id": self.app.generate_new_leave_id(),
                "emp_id": self.app.current_user["id"],
                "emp_name": self.app.current_user["name"],
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
            
            if start_date.get_date() > end_date.get_date():
                messagebox.showerror("Error", "From date cannot be after To date!")
                return
            
            self.app.leave_repo.add_leave(new_leave)
            self.app.refresh_leaves()
            messagebox.showinfo("Success", "Leave application submitted successfully!")
            leave_type.set("Sick Leave")
            reason.delete("1.0", "end")
            duration_combo.set("Full Day")
            self.show_my_leaves()
        
        tk.Button(form_frame, text="Submit Application", command=submit_leave, bg="#4CAF50", fg="white", 
                 font=("Arial", 12), width=20).grid(row=5, column=0, columnspan=2, pady=20)
        
        tk.Button(self.app.content_frame, text="View My Leaves", command=self.show_my_leaves, 
                 bg="#2196F3", fg="white", font=("Arial", 11), width=20).pack(pady=10)
    
    def show_my_leaves(self):
        """Display employee's leave applications."""
        for widget in self.app.content_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.app.content_frame, text="My Leave Applications", font=("Arial", 18, "bold"), bg="white").pack(pady=20)
        
        tk.Button(self.app.content_frame, text="← Back to Application", command=self.show_leave_application, 
                 bg="#607D8B", fg="white", font=("Arial", 10)).pack(pady=5)
        
        cols = ("ID", "Type", "Start", "End", "Duration", "Status", "Applied")
        tree_frame, self.app.my_leave_tree, my_leave_vscroll, my_leave_xscroll = self.app._create_table_with_scroll(self.app.content_frame, cols, height=12, enable_xscroll=True)

        for col in cols:
            self.app.my_leave_tree.heading(col, text=col)
            self.app.my_leave_tree.column(col, width=120)

        self.app.refresh_leaves()
        my_leaves = self.app.leave_repo.leaves_for_employee(self.app.current_user["id"])
        for leave in my_leaves:
            self.app.my_leave_tree.insert("", "end", values=(
                leave["id"], leave["leave_type"], leave["start_date"], leave["end_date"], 
                leave.get("duration_type", "Full Day"), leave["status"], leave["applied_date"]
            ))
        
        # Action Buttons
        btn_frame = tk.Frame(self.app.content_frame, bg="white")
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Edit Leave", command=self.edit_leave_application, 
                 bg="#FF9800", fg="white", font=("Arial", 10), width=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="View Details", command=self.view_my_leave_details, 
                 bg="#2196F3", fg="white", font=("Arial", 10), width=15).pack(side="left", padx=5)
    
    def edit_leave_application(self):
        """Edit a pending leave application."""
        selected = self.app.my_leave_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a leave application to edit!")
            return
        
        leave_id = self.app.my_leave_tree.item(selected[0])["values"][0]
        leave = self.app.leave_repo.get_leave(leave_id)
        
        if not leave:
            messagebox.showerror("Error", "Unable to load leave details.")
            return
        
        if leave["status"] != "Pending":
            messagebox.showwarning("Warning", f"Cannot edit leave application! Status is already {leave['status']}.")
            return
        
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Edit Leave Application")
        dialog.geometry("450x450")
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Leave Type:", font=("Arial", 11)).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        leave_type = ttk.Combobox(dialog, values=["Sick Leave", "Casual Leave", "Vacation", "Personal Leave"], 
                                 font=("Arial", 11), width=25, state="readonly")
        leave_type.set(leave["leave_type"])
        leave_type.grid(row=0, column=1, padx=20, pady=10)
        
        tk.Label(dialog, text="From Date:", font=("Arial", 11)).grid(row=1, column=0, padx=20, pady=10, sticky="w")
        start_date = DateEntry(dialog, font=("Arial", 11), width=24, background='darkblue', 
                              foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        start_date.set_date(self.app._normalize_date(leave.get("start_date")))
        start_date.grid(row=1, column=1, padx=20, pady=10)
        
        tk.Label(dialog, text="To Date:", font=("Arial", 11)).grid(row=2, column=0, padx=20, pady=10, sticky="w")
        end_date = DateEntry(dialog, font=("Arial", 11), width=24, background='darkblue', 
                            foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        end_date.set_date(self.app._normalize_date(leave.get("end_date")))
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

        def on_dialog_escape(event=None):
            closed_calendar = False
            for de in (start_date, end_date):
                try:
                    if hasattr(de, "_calendar") and de._calendar.winfo_ismapped():
                        de.drop_down()
                        closed_calendar = True
                except Exception:
                    pass
            if not closed_calendar:
                dialog.destroy()

        dialog.bind("<Escape>", on_dialog_escape)
        
        def update_leave():
            if start_date.get_date() > end_date.get_date():
                messagebox.showerror("Error", "From date cannot be after To date!")
                return
            
            self.app.leave_repo.update_leave(
                leave_id,
                {
                    "leave_type": leave_type.get(),
                    "start_date": start_date.get_date().strftime("%Y-%m-%d"),
                    "end_date": end_date.get_date().strftime("%Y-%m-%d"),
                    "reason": reason.get("1.0", "end-1c"),
                    "duration_type": duration_combo.get(),
                },
            )
            self.app.refresh_leaves()
            messagebox.showinfo("Success", "Leave application updated successfully!")
            dialog.destroy()
            self.show_my_leaves()
        
        tk.Button(dialog, text="Update", command=update_leave, bg="#FF9800", fg="white", 
                 font=("Arial", 12), width=15).grid(row=5, column=0, columnspan=2, pady=20)
    
    def view_my_leave_details(self):
        """View details of a leave application."""
        selected = self.app.my_leave_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a leave application!")
            return
        
        leave_id = self.app.my_leave_tree.item(selected[0])["values"][0]
        leave = self.app.leave_repo.get_leave(leave_id)
        
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
