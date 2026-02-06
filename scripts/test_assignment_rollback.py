from database_manager import DatabaseManager
from repositories import SalaryAssignmentRepository, EmployeeRepository
from datetime import datetime

if __name__ == '__main__':
    db = DatabaseManager()
    ass_repo = SalaryAssignmentRepository(db)
    emp_repo = EmployeeRepository(db)

    emp_id = 'EMP002'
    emp = emp_repo.get_employee(emp_id)
    print('Before assignments employee salary:', emp.get('salary'))

    # Assign salary 20000
    asg1_id = ass_repo.generate_assignment_id()
    asg1 = {
        'id': asg1_id,
        'emp_id': emp_id,
        'month': datetime.now().strftime('%Y-%m'),
        'assigned_salary': 20000.0,
        'assigned_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'assigned_by': 'EMP001'
    }
    ass_repo.add_assignment(asg1)
    emp_repo.update_employee(emp_id, {"name": emp['name'], "email": emp['email'], "phone": emp['phone'], "department": emp['department'], "role": emp['role'], "salary": asg1['assigned_salary']})

    print('After first assignment, employee salary:', emp_repo.get_employee(emp_id).get('salary'))

    # Assign salary 25000
    asg2_id = ass_repo.generate_assignment_id()
    asg2 = {
        'id': asg2_id,
        'emp_id': emp_id,
        'month': datetime.now().strftime('%Y-%m'),
        'assigned_salary': 25000.0,
        'assigned_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'assigned_by': 'EMP001'
    }
    ass_repo.add_assignment(asg2)
    emp_repo.update_employee(emp_id, {"name": emp['name'], "email": emp['email'], "phone": emp['phone'], "department": emp['department'], "role": emp['role'], "salary": asg2['assigned_salary']})

    print('After second assignment, employee salary:', emp_repo.get_employee(emp_id).get('salary'))

    # Delete second assignment
    ass_repo.delete_assignment(asg2_id)
    # After deletion, revert salary to latest remaining
    remaining = ass_repo.list_assignments(emp_id)
    if remaining:
        emp_repo.update_employee(emp_id, {"name": emp['name'], "email": emp['email'], "phone": emp['phone'], "department": emp['department'], "role": emp['role'], "salary": remaining[0]['assigned_salary']})
    else:
        emp_repo.update_employee(emp_id, {"name": emp['name'], "email": emp['email'], "phone": emp['phone'], "department": emp['department'], "role": emp['role'], "salary": 0.0})

    print('After deleting latest assignment, employee salary:', emp_repo.get_employee(emp_id).get('salary'))

    # Delete remaining assignments
    for r in ass_repo.list_assignments(emp_id):
        ass_repo.delete_assignment(r['id'])
    print('All assignments deleted for', emp_id)

    db.close()
