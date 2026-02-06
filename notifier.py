import smtplib
from email.message import EmailMessage
from typing import List, Optional
from pathlib import Path
import json
from config import SMTP

LOG_FILE = Path("salary_notifications.log")


def send_email(subject: str, body: str, to_addresses: List[str]) -> bool:
    """Send an email using SMTP configuration in config.SMTP.

    If SMTP['host'] is empty, write the message to log and return False (no SMTP)
    """
    if not SMTP.get("host"):
        # Fallback: append to log
        LOG_FILE.write_text(LOG_FILE.read_text() + f"\n---\nTo: {to_addresses}\nSubject: {subject}\n\n{body}\n") if LOG_FILE.exists() else LOG_FILE.write_text(f"To: {to_addresses}\nSubject: {subject}\n\n{body}\n")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP.get("from_email", "no-reply@company.com")
    msg["To"] = ", ".join(to_addresses)
    msg.set_content(body)

    host = SMTP.get("host")
    port = SMTP.get("port", 587)
    username = SMTP.get("username")
    password = SMTP.get("password")
    use_tls = SMTP.get("use_tls", True)

    try:
        if use_tls:
            server = smtplib.SMTP(host=host, port=port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(host=host, port=port, timeout=10)
        if username and password:
            server.login(username, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as exc:
        # Log failure as fallback
        LOG_FILE.write_text(LOG_FILE.read_text() + f"\n---\nSEND FAILED: {exc}\nTo: {to_addresses}\nSubject: {subject}\n\n{body}\n") if LOG_FILE.exists() else LOG_FILE.write_text(f"SEND FAILED: {exc}\nTo: {to_addresses}\nSubject: {subject}\n\n{body}\n")
        return False


def notify_request_submitted(emp_email: Optional[str], emp_name: str, req_id: str, month: str, description: str):
    subject = f"Payslip Correction Request Submitted: {req_id}"
    body = (
        f"Hello Admin,\n\nA new payslip correction request has been submitted by {emp_name} ({emp_email}) for {month}.\n\n"
        f"Request ID: {req_id}\nDescription:\n{description}\n\nPlease review the request in the admin panel.\n\nThanks,\nHR System"
    )
    to_addrs = SMTP.get("admin_emails", []) or []
    # Also try to include employee email so they receive a confirmation
    if emp_email:
        to_addrs.append(emp_email)
    return send_email(subject, body, to_addrs)


def notify_request_updated(emp_email: Optional[str], emp_name: str, req_id: str, status: str):
    subject = f"Payslip Correction Request Updated: {req_id}"
    body = (
        f"Hello {emp_name},\n\nYour payslip correction request {req_id} status has changed to '{status}'.\n\n"
        f"If you have further questions, please contact HR.\n\nThanks,\nHR System"
    )
    to_addrs = [emp_email] if emp_email else SMTP.get("admin_emails", [])
    return send_email(subject, body, to_addrs)


def notify_request_rejected(emp_email: Optional[str], emp_name: str, req_id: str, rejection_reason: str):
    """Notify employee that their correction request has been rejected with a reason"""
    subject = f"Payslip Correction Request Rejected: {req_id}"
    body = (
        f"Hello {emp_name},\n\nYour payslip correction request {req_id} has been reviewed and rejected.\n\n"
        f"Reason for Rejection:\n{rejection_reason}\n\n"
        f"Please contact HR if you believe this is an error or would like to discuss further.\n\nThanks,\nHR System"
    )
    to_addrs = [emp_email] if emp_email else SMTP.get("admin_emails", [])
    return send_email(subject, body, to_addrs)


def notify_request_approved(emp_email: Optional[str], emp_name: str, req_id: str, admin_notes: str, new_salary: Optional[float] = None):
    """Notify employee that their correction request has been approved"""
    subject = f"Payslip Correction Request Approved: {req_id}"
    salary_update = f"Your salary has been updated to Rs. {new_salary}.\n\n" if new_salary else ""
    body = (
        f"Hello {emp_name},\n\nYour payslip correction request {req_id} has been reviewed and approved.\n\n"
        f"{salary_update}"
        f"Admin Notes:\n{admin_notes}\n\n"
        f"Thank you for your patience.\n\nThanks,\nHR System"
    )
    to_addrs = [emp_email] if emp_email else SMTP.get("admin_emails", [])
    return send_email(subject, body, to_addrs)

def notify_correction_approved_with_assignment(emp_email: Optional[str], emp_name: str, req_id: str, admin_notes: str, month: str, assigned_salary: float, bonus: float = 0):
    """Notify employee that their correction request has been approved with monthly salary assignment"""
    subject = f"Payslip Correction Request Approved: {req_id}"
    bonus_line = f"Bonus: Rs. {bonus}\n" if bonus > 0 else ""
    body = (
        f"Hello {emp_name},\n\nYour payslip correction request {req_id} has been reviewed and approved.\n\n"
        f"Monthly Salary Assignment for {month}:\n"
        f"Assigned Salary: Rs. {assigned_salary}\n"
        f"{bonus_line}"
        f"\nAdmin Notes:\n{admin_notes}\n\n"
        f"Note: This updates your salary for the specified month only. Your base salary remains unchanged.\n\n"
        f"Thank you for your patience.\n\nThanks,\nHR System"
    )
    to_addrs = [emp_email] if emp_email else SMTP.get("admin_emails", [])
    return send_email(subject, body, to_addrs)