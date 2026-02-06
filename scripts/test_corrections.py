from database_manager import DatabaseManager
from repositories import CorrectionRepository
from datetime import datetime

if __name__ == '__main__':
    db = DatabaseManager()
    repo = CorrectionRepository(db)
    req = {
        'id': repo.generate_correction_id(),
        'emp_id': 'EMP002',
        'month': '2025-11',
        'description': 'Fix incorrect bonus',
        'submitted_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'Pending'
    }
    repo.add_correction(req)
    print('Inserted request', req['id'])
    rows = repo.list_corrections('EMP002')
    print('Requests for EMP002:', rows)
    db.close()
