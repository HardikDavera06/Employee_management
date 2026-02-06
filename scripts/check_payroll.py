from database_manager import DatabaseManager
from repositories import PayrollRepository

if __name__ == '__main__':
    db = DatabaseManager()
    payroll_repo = PayrollRepository(db)
    records = payroll_repo.list_records()
    print(f"Found {len(records)} payroll records")
    for r in records[:20]:
        print(r)
    db.close()
