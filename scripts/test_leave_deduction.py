from employee import EmployeeManagementSystem
from config import DEFAULT_OVERTIME_RATE

app = EmployeeManagementSystem()
# Provide an emp id that exists
emp = app.employees[1] if len(app.employees) > 1 else app.employees[0]

# Add a leave with datetime.date values and ensure calculation handles it
from datetime import date, datetime

leave = {
    'id': app.generate_new_leave_id(),
    'emp_id': emp['id'],
    'emp_name': emp['name'],
    'leave_type': 'Sick',
    'start_date': date(2025, 11, 10),
    'end_date': date(2025, 11, 12),
    'reason': 'Testing leave',
    'status': 'Approved',
    'applied_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'duration_type': 'Full Day'
}

# Insert leave via repo
app.leave_repo.add_leave(leave)

month = '2025-11'
base_salary = emp.get('salary', 0) or 10000
ldays, deduction = app.calculate_leave_deduction(emp['id'], month, base_salary)
print('Leave days:', ldays)
print('Leave deduction:', deduction)

# Clean up
app.leave_repo.update_status(leave['id'], 'Cancelled')
app.db.close()
