from database_manager import DatabaseManager
from repositories import CorrectionRepository
from notifier import send_email, notify_request_submitted, notify_request_updated
from datetime import datetime

if __name__ == '__main__':
    db = DatabaseManager()
    repo = CorrectionRepository(db)
    req_id = repo.generate_correction_id()
    req = {
        'id': req_id,
        'emp_id': 'EMP002',
        'month': '2025-11',
        'description': 'Test notification',
        'submitted_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'Pending'
    }
    repo.add_correction(req)
    print('Inserted request', req_id)

    # Send notification (will log to salary_notifications.log if SMTP is not configured)
    notify_request_submitted('emp002@company.com', 'Test Employee', req_id, '2025-11', 'Test notification')
    notify_request_updated('emp002@company.com', 'Test Employee', req_id, 'Resolved')
    print('Notifications attempted; check salary_notifications.log or SMTP delivery')
    db.close()
