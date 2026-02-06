from database_manager import DatabaseManager
from repositories import SalaryAssignmentRepository, EmployeeRepository
from datetime import datetime

if __name__ == '__main__':
    db = DatabaseManager()
    ass_repo = SalaryAssignmentRepository(db)
    emp_repo = EmployeeRepository(db)

    emp_id = 'EMP002'
    # create a new assignment
    asg_id = ass_repo.generate_assignment_id()
    asg = {
        'id': asg_id,
        'emp_id': emp_id,
        'month': datetime.now().strftime('%Y-%m'),
        'assigned_salary': 15000.0,
        'assigned_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'assigned_by': 'EMP001'
    }
    ass_repo.add_assignment(asg)
    print('Added assignment', asg_id)
    # Check employee salary
    emp = emp_repo.get_employee(emp_id)
    print('Employee salary now:', emp.get('salary'))
    # List assignments
    print('Assignments for', emp_id)
    for a in ass_repo.list_assignments(emp_id):
        print(a)
    # Delete the assignment we just added
    ass_repo.delete_assignment(asg_id)
    print('Deleted assignment', asg_id)
    # Check employee salary after deletion
    emp = emp_repo.get_employee(emp_id)
    print('Employee salary now after deletion:', emp.get('salary'))
    db.close()
