import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
from config import DEFAULT_OVERTIME_RATE
from pathlib import Path

# This module provides employee-side salary features, imported by employee.py

EXPORT_DIR = Path("salary_exports")
EXPORT_DIR.mkdir(exist_ok=True)


class SalaryUI:
    def __init__(self, app):
        """
        app is an instance of EmployeeManagementSystem (or an object exposing:
          - root (tk root)
          - content_frame (where to place UI)
          - payroll_repo (repo for payroll records)
          - employee_repo (optional)
          - current_user (employee dict)
        """
        self.app = app

    # Correction requests are now stored in the database via CorrectionRepository

    def show_my_salary(self):
        # Clear content and render salary UI for current user
        for widget in list(self.app.content_frame.winfo_children()):
            widget.destroy()

        tk.Label(self.app.content_frame, text="My Salary", font=("Arial", 18, "bold"), bg="white").pack(pady=20)

        # Buttons: Export CSV, Request Correction, Estimate
        btn_frame = tk.Frame(self.app.content_frame, bg="white")
        btn_frame.pack(anchor="w", padx=20, pady=10)

        export_btn = tk.Button(btn_frame, text="Export Salary History (CSV)", bg="#2196F3", fg="white",
                               command=self.export_csv, font=("Arial", 11))
        export_btn.pack(side="left", padx=6)

        estimator_btn = tk.Button(btn_frame, text="Estimate Next Pay", bg="#4CAF50", fg="white",
                                  command=self.show_estimator_dialog, font=("Arial", 11))
        estimator_btn.pack(side="left", padx=6)

        requests_btn = tk.Button(btn_frame, text="My Correction Requests", bg="#FF9800", fg="white",
                     command=self.show_my_requests, font=("Arial", 11))
        requests_btn.pack(side="left", padx=6)

        # Assigned Salary history (show assignments rather than payroll records)
        history_frame = tk.Frame(self.app.content_frame, bg="white")
        history_frame.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(history_frame, text="Assigned Salary History", font=("Arial", 14, "bold"), bg="white").pack(anchor="w")

        cols = ("ID", "Month", "Assigned Salary (Monthly)", "Assigned On", "Assigned By")
        tf, tree, vscroll, xscroll = self.app._create_table_with_scroll(history_frame, cols, height=10, enable_xscroll=True)

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=160)

        emp_id = self.app.current_user["id"]
        assignments = self.app.assignment_repo.list_assignments(emp_id)

        for rec in assignments:
            tree.insert("", "end", values=(rec["id"], rec.get('month'), f"Rs. {rec.get('assigned_salary',0):,.2f}", rec.get('assigned_on'), rec.get('assigned_by')))

        # packed by helper

        action_frame = tk.Frame(history_frame, bg="white")
        action_frame.pack(pady=10)

        def request_correction_from_assignment():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select an assignment to request correction.")
                return
            asg_id = tree.item(selected[0])["values"][0]
            # Show correction dialog
            dialog = tk.Toplevel(self.app.root)
            dialog.title("Request Payslip Correction for Assignment")
            dialog.geometry("420x320")
            dialog.transient(self.app.root)
            dialog.grab_set()

            tk.Label(dialog, text="Request Payslip Correction", font=("Arial", 14, "bold")).pack(pady=10)
            frame = tk.Frame(dialog)
            frame.pack(fill="x", padx=15, pady=5)

            tk.Label(frame, text="Month (YYYY-MM):", font=("Arial", 11)).grid(row=0, column=0, sticky="w", pady=5)
            month_entry = tk.Entry(frame, font=("Arial", 11), width=18)
            # extract month from assigned_on
            assigned = self.app.assignment_repo.get_assignment(asg_id)
            assigned_on = assigned.get('assigned_on')
            assigned_month = assigned.get('month')
            try:
                month_entry.insert(0, assigned_month or assigned_on[:7])
            except Exception:
                month_entry.insert(0, datetime.now().strftime("%Y-%m"))
            month_entry.grid(row=0, column=1, pady=5)

            tk.Label(frame, text="Description:", font=("Arial", 11)).grid(row=1, column=0, sticky="nw", pady=5)
            desc_text = tk.Text(frame, width=40, height=8)
            desc_text.grid(row=1, column=1, pady=5)

            def submit_corr():
                month = month_entry.get().strip()
                desc = desc_text.get("1.0", "end").strip()
                if not month or not desc:
                    messagebox.showerror("Error", "Please provide both month and description.")
                    return
                # create correction record linking assignment
                repo = getattr(self.app, "correction_repo", None)
                if repo is None:
                    messagebox.showerror("Error", "Correction repository not available.")
                    dialog.destroy()
                    return
                req_id = repo.generate_correction_id()
                new_req = {
                    "id": req_id,
                    "emp_id": self.app.current_user["id"],
                    "month": month,
                    "assignment_id": asg_id,
                    "description": desc,
                    "submitted_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "Pending",
                }
                try:
                    repo.add_correction(new_req)
                except Exception as exc:
                    messagebox.showerror("Error", f"Failed to submit request: {exc}")
                    return
                # notify admin
                try:
                    from notifier import notify_request_submitted
                except Exception:
                    notify_request_submitted = None
                if notify_request_submitted:
                    emp_email = self.app.current_user.get("email")
                    notify_request_submitted(emp_email, self.app.current_user.get("name", ""), req_id, month, desc)
                messagebox.showinfo("Submitted", f"Correction request submitted (ID: {req_id}). HR/Admin will review it.")
                dialog.destroy()

            tk.Button(dialog, text="Submit Request", bg="#4CAF50", fg="white", command=submit_corr, font=("Arial", 11), width=16).pack(pady=10)

        def export_assignments_csv():
            emp_id = self.app.current_user["id"]
            assignments = self.app.assignment_repo.list_assignments(emp_id)
            if not assignments:
                messagebox.showinfo("No Data", "No assignments found to export.")
                return
            filename = EXPORT_DIR / f"{emp_id}_assignments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            try:
                with open(filename, "w", newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["ID", "Assigned Salary", "Assigned On", "Assigned By"])
                    for r in assignments:
                        writer.writerow([r.get('id'), r.get('month'), r.get('assigned_salary'), r.get('assigned_on'), r.get('assigned_by')])
                messagebox.showinfo("Exported", f"Assignment history exported to {filename}")
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to export CSV: {exc}")

        tk.Button(action_frame, text="Request Correction", command=request_correction_from_assignment, bg="#FF9800", fg="white", font=("Arial", 11), width=18).pack(side="left", padx=6)
        tk.Button(action_frame, text="Export Assignments (CSV)", command=export_assignments_csv, bg="#2196F3", fg="white", font=("Arial", 11), width=20).pack(side="left", padx=6)

    def request_correction_on_assignment(self):
        """Allow employee to request correction for a specific assigned salary"""
        for widget in list(self.app.content_frame.winfo_children()):
            widget.destroy()

        tk.Label(self.app.content_frame, text="Request Salary Correction", font=("Arial", 18, "bold"), bg="white").pack(pady=20)

        # Assigned Salary history table
        history_frame = tk.Frame(self.app.content_frame, bg="white")
        history_frame.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(history_frame, text="Your Assigned Salaries", font=("Arial", 14, "bold"), bg="white").pack(anchor="w", pady=(0, 10))

        cols = ("ID", "Month", "Assigned Salary", "Bonus", "Assigned On")
        tf, tree, vscroll, xscroll = self.app._create_table_with_scroll(history_frame, cols, height=12, enable_xscroll=True)

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150)

        emp_id = self.app.current_user["id"]
        assignments = self.app.assignment_repo.list_assignments(emp_id)

        if not assignments:
            tk.Label(history_frame, text="No assigned salaries found.", font=("Arial", 11), bg="white", fg="#999").pack(pady=20)
            tk.Button(self.app.content_frame, text="← Back", command=self.app.show_employee_dashboard, bg="#607D8B", fg="white", font=("Arial", 11)).pack(pady=10)
            return

        for rec in assignments:
            tree.insert("", "end", values=(
                rec["id"],
                rec.get('month'),
                f"Rs. {rec.get('assigned_salary', 0):,.2f}",
                f"Rs. {rec.get('bonus', 0):,.2f}",
                rec.get('assigned_on')
            ))

        # Action buttons
        btn_frame = tk.Frame(history_frame, bg="white")
        btn_frame.pack(pady=12)

        def request_correction():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select an assigned salary to request correction.")
                return

            asg_id = tree.item(selected[0])["values"][0]
            assignment = self.app.assignment_repo.get_assignment(asg_id)
            if not assignment:
                messagebox.showerror("Error", "Assignment not found.")
                return

            # Open correction request dialog
            dialog = tk.Toplevel(self.app.root)
            dialog.title(f"Request Correction - {assignment.get('month')}")
            dialog.geometry("500x420")
            dialog.transient(self.app.root)
            dialog.grab_set()

            # Display assignment details
            details_frame = tk.Frame(dialog, bg="#f5f5f5")
            details_frame.pack(fill="x", padx=15, pady=10)

            tk.Label(details_frame, text="Assignment Details", font=("Arial", 12, "bold"), bg="#f5f5f5").pack(anchor="w", pady=5)
            tk.Label(details_frame, text=f"Month: {assignment.get('month')}", font=("Arial", 10), bg="#f5f5f5").pack(anchor="w", pady=2)
            tk.Label(details_frame, text=f"Assigned Salary: Rs. {assignment.get('assigned_salary', 0):,.2f}", font=("Arial", 10), bg="#f5f5f5").pack(anchor="w", pady=2)
            tk.Label(details_frame, text=f"Bonus/Incentives: Rs. {assignment.get('bonus', 0):,.2f}", font=("Arial", 10), bg="#f5f5f5").pack(anchor="w", pady=2)
            tk.Label(details_frame, text=f"Assigned On: {assignment.get('assigned_on')}", font=("Arial", 10), bg="#f5f5f5").pack(anchor="w", pady=2)

            # Correction description
            tk.Label(dialog, text="What's the issue?", font=("Arial", 11)).pack(anchor="w", padx=15, pady=(10, 5))
            desc_text = tk.Text(dialog, height=10, width=60, font=("Arial", 10), wrap=tk.WORD)
            desc_text.pack(padx=15, pady=5, fill="both", expand=True)

            # Submit button
            def submit_correction():
                description = desc_text.get("1.0", "end").strip()
                if not description:
                    messagebox.showerror("Error", "Please describe the issue.")
                    return

                repo = getattr(self.app, "correction_repo", None)
                if repo is None:
                    messagebox.showerror("Error", "Correction repository not available.")
                    return

                req_id = repo.generate_correction_id()
                new_req = {
                    "id": req_id,
                    "emp_id": self.app.current_user["id"],
                    "month": assignment.get("month"),
                    "assignment_id": asg_id,
                    "description": description,
                    "submitted_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "Pending",
                }

                try:
                    repo.add_correction(new_req)
                except Exception as exc:
                    messagebox.showerror("Error", f"Failed to submit correction: {exc}")
                    return

                # Notify admin
                try:
                    from notifier import notify_request_submitted
                except Exception:
                    notify_request_submitted = None

                if notify_request_submitted:
                    emp_email = self.app.current_user.get("email")
                    emp_name = self.app.current_user.get("name", "")
                    notify_request_submitted(emp_email, emp_name, req_id, assignment.get("month"), description)

                messagebox.showinfo("Success", f"Correction request submitted (ID: {req_id}). HR will review and respond.")
                dialog.destroy()
                self.request_correction_on_assignment()  # Refresh list

            tk.Button(dialog, text="Submit Correction Request", command=submit_correction, bg="#4CAF50", fg="white", font=("Arial", 11), width=20).pack(pady=10)

        tk.Button(btn_frame, text="Request Correction for Selected", command=request_correction, bg="#FF9800", fg="white", font=("Arial", 11), width=28).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Back to Dashboard", command=self.app.show_employee_dashboard, bg="#607D8B", fg="white", font=("Arial", 11), width=18).pack(side="left", padx=6)

    def export_csv(self):
        """Export current employee's assigned salary history to CSV"""
        emp_id = self.app.current_user.get("id")
        if not emp_id:
            messagebox.showerror("Error", "Could not determine employee ID.")
            return
        
        # Get assigned salaries for this employee
        records = self.app.assignment_repo.list_assignments(emp_id)
        if not records:
            messagebox.showinfo("No Data", "No salary assignments found to export.")
            return
        
        filename = EXPORT_DIR / f"{emp_id}_salary_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(filename, "w", newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["ID", "Month", "Assigned Salary", "Bonus", "NET Salary", "Assigned On", "Assigned By"])
                for r in records:
                    assigned_sal = float(r.get('assigned_salary', 0))
                    bonus = float(r.get('bonus', 0))
                    net_sal = assigned_sal + bonus
                    writer.writerow([
                        r.get('id'), 
                        r.get('month'), 
                        f"{assigned_sal:,.2f}",
                        f"{bonus:,.2f}",
                        f"{net_sal:,.2f}",
                        r.get('assigned_on'), 
                        r.get('assigned_by', 'N/A')
                    ])
            messagebox.showinfo("Exported", f"Salary history exported to {filename}")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to export CSV: {exc}")

    def request_correction_dialog(self):
        # Dialog to request a correction for a specific payslip month
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Request Payslip Correction")
        dialog.geometry("420x320")
        dialog.resizable(True, True)
        dialog.transient(self.app.root)
        dialog.grab_set()

        tk.Label(dialog, text="Request Payslip Correction", font=("Arial", 14, "bold")).pack(pady=10)

        frame = tk.Frame(dialog)
        frame.pack(fill="x", padx=15, pady=5)
        frame.grid_columnconfigure(1, weight=1)

        tk.Label(frame, text="Month (YYYY-MM):", font=("Arial", 11)).grid(row=0, column=0, sticky="w", pady=5)
        month_entry = tk.Entry(frame, font=("Arial", 11), width=30)
        month_entry.insert(0, datetime.now().strftime("%Y-%m"))
        month_entry.grid(row=0, column=1, pady=5)

        tk.Label(frame, text="Description:", font=("Arial", 11)).grid(row=1, column=0, sticky="nw", pady=5)
        desc_text = tk.Text(frame, width=40, height=8)
        desc_text.grid(row=1, column=1, pady=5)

        def submit_request():
            month = month_entry.get().strip()
            desc = desc_text.get("1.0", "end").strip()
            if not month or not desc:
                messagebox.showerror("Error", "Please provide both month and description.")
                return
            # Create correction record using repository
            repo = getattr(self.app, "correction_repo", None)
            if repo is None:
                messagebox.showerror("Error", "Correction repository not available.")
                dialog.destroy()
                return
            req_id = repo.generate_correction_id()
            new_req = {
                "id": req_id,
                "emp_id": self.app.current_user["id"],
                "month": month,
                "description": desc,
                "submitted_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Pending",
            }
            try:
                repo.add_correction(new_req)
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to submit request: {exc}")
                return
            # Notify admin and employee about the new request (if notifier is configured)
            try:
                from notifier import notify_request_submitted
            except Exception:
                notify_request_submitted = None
            if notify_request_submitted:
                emp_email = self.app.current_user.get("email")
                notify_request_submitted(emp_email, self.app.current_user.get("name", ""), req_id, month, desc)
            messagebox.showinfo("Submitted", f"Correction request submitted (ID: {req_id}). HR/Admin will review it.")
            dialog.destroy()

        tk.Button(dialog, text="Submit Request", bg="#4CAF50", fg="white", command=submit_request, font=("Arial", 11), width=16).pack(pady=10)

    def show_estimator_dialog(self):
        # Small form that allows employee to calculate a projected pay for a given month
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Estimate Pay")
        dialog.geometry("800x520")
        dialog.resizable(True, True)
        dialog.transient(self.app.root)
        dialog.grab_set()

        tk.Label(dialog, text="Estimate Next Pay", font=("Arial", 14, "bold")).pack(pady=10)
        frame = tk.Frame(dialog)
        frame.pack(fill="x", padx=15, pady=5)

        tk.Label(frame, text="Month (YYYY-MM):", font=("Arial", 11)).grid(row=0, column=0, sticky="w", pady=5)
        month_entry = tk.Entry(frame, font=("Arial", 11), width=18)
        month_entry.insert(0, datetime.now().strftime("%Y-%m"))
        month_entry.grid(row=0, column=1, pady=5)

        tk.Label(frame, text="Overtime Hours:", font=("Arial", 11)).grid(row=1, column=0, sticky="w", pady=5)
        ot_hours_entry = tk.Entry(frame, font=("Arial", 11), width=30)
        ot_hours_entry.insert(0, "0")
        ot_hours_entry.grid(row=1, column=1, pady=5)

        tk.Label(frame, text="Overtime Rate (per hr) — Fixed Rs.100:", font=("Arial", 11)).grid(row=2, column=0, sticky="w", pady=5)
        ot_rate_entry = tk.Entry(frame, font=("Arial", 11), width=30)
        ot_rate_entry.insert(0, str(DEFAULT_OVERTIME_RATE))
        ot_rate_entry.configure(state="readonly")
        ot_rate_entry.grid(row=2, column=1, pady=5)

        tk.Label(frame, text="Bonus:", font=("Arial", 11)).grid(row=3, column=0, sticky="w", pady=5)
        bonus_entry = tk.Entry(frame, font=("Arial", 11), width=30)
        bonus_entry.insert(0, "0")
        bonus_entry.grid(row=3, column=1, pady=5)

        tk.Label(frame, text="Other Deductions:", font=("Arial", 11)).grid(row=4, column=0, sticky="w", pady=5)
        deductions_entry = tk.Entry(frame, font=("Arial", 11), width=30)
        deductions_entry.insert(0, "0")
        deductions_entry.grid(row=4, column=1, pady=5)

        # Use a read-only scrolled text control to visibly show long estimates
        # Place the result area in its own frame so it expands properly
        result_container = tk.Frame(dialog)
        result_container.pack(fill="both", expand=True, padx=12, pady=(8, 12))
        result_container.grid_rowconfigure(0, weight=1)
        result_container.grid_columnconfigure(0, weight=1)

        result_text = scrolledtext.ScrolledText(result_container, wrap=tk.WORD, height=12, width=80, font=("Arial", 11))
        result_text.grid(row=0, column=0, sticky="nsew")
        result_text.insert("1.0", "Enter values and click Estimate")
        result_text.configure(state=tk.DISABLED)

        def estimate_pay():
            try:
                ot_hours = float(ot_hours_entry.get())
                # Overtime rate is fixed at Rs.100; enforce programmatically
                ot_rate = DEFAULT_OVERTIME_RATE
                bonus = float(bonus_entry.get())
                deductions = float(deductions_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numeric values")
                return

            emp = self.app.current_user
            base_salary = float(emp.get("salary", 0))
            overtime_pay = ot_hours * ot_rate
            # Try to resolve leave deduction using same logic from app if present
            try:
                leave_days, leave_deduction = self.app.calculate_leave_deduction(emp["id"], month_entry.get().strip(), base_salary)
            except Exception:
                leave_days, leave_deduction = (0.0, 0.0)

            net = base_salary + overtime_pay + bonus - leave_deduction - deductions
            net = max(net, 0.0)

            summary = (
                f"Base Salary: {base_salary:,.2f}\n"
                f"Overtime: {overtime_pay:,.2f}\n"
                f"Bonus: {bonus:,.2f}\n"
                f"Leave Deduction ({leave_days} days): {leave_deduction:,.2f}\n"
                f"Other Deductions: {deductions:,.2f}\n\n"
                f"Estimated Net Pay: {net:,.2f}"
            )
            # Display the summary in the read-only ScrolledText control
            result_text.configure(state=tk.NORMAL)
            result_text.delete("1.0", tk.END)
            result_text.insert(tk.END, summary)
            result_text.configure(state=tk.DISABLED)

        tk.Button(dialog, text="Estimate", command=estimate_pay, bg="#4CAF50", fg="white", font=("Arial", 11), width=16).pack(pady=10)

    def show_my_requests(self):
        """Display employee's correction requests in the main content area."""
        # Clear content frame
        for widget in list(self.app.content_frame.winfo_children()):
            widget.destroy()

        # Title
        tk.Label(self.app.content_frame, text="My Correction Requests", font=("Arial", 18, "bold"), bg="white").pack(pady=20)

        repo = getattr(self.app, "correction_repo", None)
        if repo is None:
            messagebox.showerror("Error", "Correction repository not available.")
            return

        emp_id = self.app.current_user["id"]
        data = repo.list_corrections_filtered(emp_id=emp_id)
        
        # Filter out withdrawn requests
        active_requests = [r for r in data if r.get("status") != "Withdrawn"]
        
        if not active_requests:
            tk.Label(self.app.content_frame, text="You have not submitted any correction requests yet.", 
                    font=("Arial", 11), bg="white", fg="#999").pack(pady=20)
            tk.Button(self.app.content_frame, text="← Back to Dashboard", command=self.app.show_employee_dashboard, 
                     bg="#607D8B", fg="white", font=("Arial", 11)).pack(pady=10)
            return

        # Main container
        main_container = tk.Frame(self.app.content_frame, bg="white")
        main_container.pack(fill="both", expand=True, padx=20, pady=10)

        # Table with requests
        cols = ("ID", "Assignment ID", "Month", "Description", "Submitted On", "Status")
        tf, tree, vscroll, xscroll = self.app._create_table_with_scroll(main_container, cols, height=12, enable_xscroll=True)
        
        for c in cols:
            tree.heading(c, text=c)
            if c == "Description":
                tree.column(c, width=200)
            elif c == "Submitted On":
                tree.column(c, width=160)
            else:
                tree.column(c, width=120)

        # Insert requests with status-based coloring
        for r in active_requests:
            status = r.get("status", "Unknown")
            tree.insert("", "end", values=(
                r.get("id"), 
                r.get("assignment_id", "N/A"), 
                r.get("month"), 
                r.get("description", ""), 
                r.get("submitted_on"), 
                status
            ))

        # Double-click a row to view full request details (including admin notes or rejection reason)
        def view_request_details(event=None):
            sel = tree.selection()
            if not sel:
                return
            req_id = tree.item(sel[0])["values"][0]
            full = repo.get_correction(req_id)
            if not full:
                messagebox.showerror("Error", "Selected request not found.")
                return

            dlg = tk.Toplevel(self.app.root)
            dlg.title(f"Request Details - {req_id}")
            dlg.geometry("640x480")
            dlg.resizable(True, True)
            dlg.transient(self.app.root)
            dlg.grab_set()

            header = tk.Frame(dlg, bg="#f5f5f5")
            header.pack(fill="x", padx=12, pady=8)
            tk.Label(header, text=f"Request ID: {req_id}", font=("Arial", 12, "bold"), bg="#f5f5f5").pack(anchor="w")
            tk.Label(header, text=f"Status: {full.get('status','Unknown')}", font=("Arial", 10), bg="#f5f5f5", fg="#333").pack(anchor="w")

            body = tk.Frame(dlg)
            body.pack(fill="both", expand=True, padx=12, pady=6)

            tk.Label(body, text=f"Month: {full.get('month', 'N/A')}", font=("Arial", 11)).pack(anchor="w", pady=2)
            tk.Label(body, text=f"Assignment ID: {full.get('assignment_id','N/A')}", font=("Arial", 11)).pack(anchor="w", pady=2)
            tk.Label(body, text=f"Payroll ID: {full.get('payroll_id','N/A')}", font=("Arial", 11)).pack(anchor="w", pady=2)
            tk.Label(body, text=f"Submitted On: {full.get('submitted_on','N/A')}", font=("Arial", 11)).pack(anchor="w", pady=2)

            tk.Label(body, text="Description:", font=("Arial", 11)).pack(anchor="w", pady=(8, 2))
            desc = scrolledtext.ScrolledText(body, height=8, wrap=tk.WORD)
            desc.insert("1.0", full.get('description', ''))
            desc.configure(state=tk.DISABLED)
            desc.pack(fill="both", expand=True, pady=(0, 8))

            status = (full.get('status') or '').lower()
            if status == 'resolved':
                tk.Label(body, text="Admin Note:", font=("Arial", 11)).pack(anchor="w", pady=(4, 2))
                note = scrolledtext.ScrolledText(body, height=6, wrap=tk.WORD)
                note.insert("1.0", full.get('admin_notes', '(No notes provided)'))
                note.configure(state=tk.DISABLED)
                note.pack(fill="both", expand=True, pady=(0, 8))
            elif status == 'rejected':
                tk.Label(body, text="Rejection Reason:", font=("Arial", 11)).pack(anchor="w", pady=(4, 2))
                note = scrolledtext.ScrolledText(body, height=6, wrap=tk.WORD)
                note.insert("1.0", full.get('rejection_reason', '(No reason provided)'))
                note.configure(state=tk.DISABLED)
                note.pack(fill="both", expand=True, pady=(0, 8))

            btnf = tk.Frame(dlg)
            btnf.pack(fill="x", pady=8)
            tk.Button(btnf, text="Close", command=dlg.destroy, bg="#607D8B", fg="white", font=("Arial", 11), width=12).pack(side="right", padx=12)

        tree.bind('<Double-1>', lambda e: view_request_details())

        def withdraw_request():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Warning", "Please select a request to withdraw.")
                return
            req_id = tree.item(sel[0])["values"][0]
            # Allow withdrawal only if Pending
            req = repo.get_correction(req_id)
            if not req:
                messagebox.showerror("Error", "Selected request not found.")
                return
            if req.get("status") != "Pending":
                messagebox.showinfo("Info", "Only Pending requests can be withdrawn.")
                return
            
            if not messagebox.askyesno("Confirm", f"Are you sure you want to withdraw request {req_id}?"):
                return
            
            repo.update_status(req_id, "Withdrawn")
            messagebox.showinfo("Success", f"Request {req_id} has been withdrawn.")
            # Refresh the view
            self.show_my_requests()
            
            # Notify admin and employee about withdrawal
            try:
                emp = self.app.current_user
                from notifier import notify_request_updated
                notify_request_updated(emp.get("email"), emp.get("name"), req_id, "Withdrawn")
            except Exception:
                pass

        def edit_request():
            """Edit a pending correction request."""
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Warning", "Please select a request to edit.")
                return
            
            req_id = tree.item(sel[0])["values"][0]
            req = repo.get_correction(req_id)
            if not req:
                messagebox.showerror("Error", "Selected request not found.")
                return
            
            # Only allow editing pending requests
            if req.get("status") != "Pending":
                messagebox.showinfo("Info", "Only Pending requests can be edited.")
                return
            
            # Open edit dialog
            edit_dialog = tk.Toplevel(self.app.root)
            edit_dialog.title(f"Edit Correction Request - {req_id}")
            # Increase default size and allow resizing so buttons remain visible
            edit_dialog.geometry("650x520")
            edit_dialog.resizable(True, True)
            try:
                edit_dialog.minsize(600, 380)
            except Exception:
                pass
            edit_dialog.transient(self.app.root)
            edit_dialog.grab_set()
            
            # Header
            header_frame = tk.Frame(edit_dialog, bg="#f5f5f5")
            header_frame.pack(fill="x", padx=15, pady=10)
            tk.Label(header_frame, text="Edit Correction Request", font=("Arial", 14, "bold"), bg="#f5f5f5").pack(anchor="w", pady=5)
            tk.Label(header_frame, text=f"Request ID: {req_id} | Status: {req.get('status')}", 
                    font=("Arial", 10), bg="#f5f5f5", fg="#555").pack(anchor="w", pady=2)
            
            # Form
            form_frame = tk.Frame(edit_dialog)
            form_frame.pack(fill="both", expand=True, padx=15, pady=10)
            
            tk.Label(form_frame, text="Month:", font=("Arial", 11)).pack(anchor="w", pady=(8, 2))
            month_var = tk.StringVar(value=req.get("month", ""))
            tk.Label(form_frame, text=month_var.get(), font=("Arial", 11, "bold"), fg="#1565C0").pack(anchor="w", pady=(0, 8))
            
            tk.Label(form_frame, text="Assignment ID:", font=("Arial", 11)).pack(anchor="w", pady=(8, 2))
            tk.Label(form_frame, text=req.get("assignment_id", "N/A"), font=("Arial", 11, "bold"), fg="#1565C0").pack(anchor="w", pady=(0, 8))
            
            tk.Label(form_frame, text="Description:", font=("Arial", 11)).pack(anchor="w", pady=(8, 2))
            desc_text = tk.Text(form_frame, height=10, width=60, font=("Arial", 10), wrap=tk.WORD)
            desc_text.insert("1.0", req.get("description", ""))
            desc_text.pack(fill="both", expand=True, pady=(0, 8))
            
            def save_changes():
                new_description = desc_text.get("1.0", "end").strip()
                if not new_description:
                    messagebox.showerror("Error", "Description cannot be empty.")
                    return
                
                try:
                    # Update the correction request with new description
                    repo.update_correction(req_id, {"description": new_description})
                    messagebox.showinfo("Success", f"Correction request {req_id} has been updated.")
                    edit_dialog.destroy()
                    # Refresh the requests list
                    self.show_my_requests()
                except Exception as exc:
                    messagebox.showerror("Error", f"Failed to update request: {exc}")
            
            # Buttons anchored to bottom so they remain visible even when the text expands
            btn_frame = tk.Frame(edit_dialog)
            btn_frame.pack(side="bottom", fill="x", pady=10)

            tk.Button(btn_frame, text="Save Changes", command=save_changes, bg="#4CAF50", fg="white", 
                     font=("Arial", 11), padx=12, pady=8, relief="flat", cursor="hand2").pack(side="left", padx=6)
            tk.Button(btn_frame, text="Cancel", command=edit_dialog.destroy, bg="#607D8B", fg="white", 
                     font=("Arial", 11), padx=12, pady=8, relief="flat", cursor="hand2").pack(side="left", padx=6)

        # Action buttons
        btn_frame = tk.Frame(self.app.content_frame, bg="white")
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="✏️ Edit Request", command=edit_request, 
                 bg="#2196F3", fg="white", font=("Arial", 11), padx=12, pady=8, relief="flat", cursor="hand2").pack(side="left", padx=6)
        
        tk.Button(btn_frame, text="Withdraw Selected Request", command=withdraw_request, 
                 bg="#f44336", fg="white", font=("Arial", 11), padx=12, pady=8, relief="flat", cursor="hand2").pack(side="left", padx=6)


# End of employee_salary.py
