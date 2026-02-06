from database_manager import DatabaseManager
from repositories import SalaryAssignmentRepository, CorrectionRepository
from datetime import datetime

if __name__ == '__main__':
    db = DatabaseManager()
    ass_repo = SalaryAssignmentRepository(db)
    corr_repo = CorrectionRepository(db)

    emp_id = 'EMP002'
    # create a new assignment
    asg_id = ass_repo.generate_assignment_id()
    asg = {
        'id': asg_id,
        'emp_id': emp_id,
        'month': datetime.now().strftime('%Y-%m'),
        'assigned_salary': 18000.0,
        'assigned_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'assigned_by': 'EMP001'
    }
    ass_repo.add_assignment(asg)
    print('Added assignment', asg_id)

    # request a correction for this assignment
    req_id = corr_repo.generate_correction_id()
    request = {
        'id': req_id,
        'emp_id': emp_id,
        'month': datetime.now().strftime('%Y-%m'),
        'assignment_id': asg_id,
        'description': 'Correction request for assignment test',
        'submitted_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'Pending'
    }
    corr_repo.add_correction(request)
    print('Correction requested for assignment', asg_id, '->', req_id)

    rows = corr_repo.list_corrections(emp_id)
    print('Corrections for', emp_id)
    for r in rows:
        print(r)

    db.close()
