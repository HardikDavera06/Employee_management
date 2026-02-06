from database_manager import DatabaseManager
from repositories import SalaryAssignmentRepository

if __name__ == '__main__':
    db = DatabaseManager()
    repo = SalaryAssignmentRepository(db)
    rows = repo.list_assignments()
    print(f"Found {len(rows)} assignments")
    for r in rows:
        print(r)
    db.close()
