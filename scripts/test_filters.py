from database_manager import DatabaseManager
from repositories import CorrectionRepository

if __name__ == '__main__':
    db = DatabaseManager()
    repo = CorrectionRepository(db)
    print('All corrections:')
    for r in repo.list_corrections():
        print(r)
    print('\nFiltered (emp_id=EMP002, status=Pending):')
    for r in repo.list_corrections_filtered(emp_id='EMP002', status='Pending'):
        print(r)
    print('\nFiltered (start_date 2025-11-28):')
    for r in repo.list_corrections_filtered(start_date='2025-11-28'):
        print(r)
    db.close()
