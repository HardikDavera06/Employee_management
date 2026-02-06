from database_manager import DatabaseManager
from repositories import SalaryAssignmentRepository
from datetime import datetime

if __name__ == '__main__':
    db = DatabaseManager()
    ass_repo = SalaryAssignmentRepository(db)

    emp_id = 'EMP002'
    month = datetime.now().strftime('%Y-%m')

    asg1_id = ass_repo.generate_assignment_id()
    asg1 = {
        'id': asg1_id,
        'emp_id': emp_id,
        'month': month,
        'assigned_salary': 20000.0,
        'assigned_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'assigned_by': 'EMP001'
    }
    ass_repo.add_assignment(asg1)
    print('Added assignment', asg1_id)

    # Attempt to add duplicate assignment for the same month
    asg2_id = ass_repo.generate_assignment_id()
    asg2 = {
        'id': asg2_id,
        'emp_id': emp_id,
        'month': month,
        'assigned_salary': 25000.0,
        'assigned_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'assigned_by': 'EMP001'
    }
    try:
        ass_repo.add_assignment(asg2)
        print('Unexpected: Second assignment for same month was allowed')
    except Exception as e:
        print('As expected, adding second assignment for same month failed:', e)

    # Clean up: delete created assignment(s)
    for r in ass_repo.list_assignments(emp_id):
        ass_repo.delete_assignment(r['id'])

    db.close()
