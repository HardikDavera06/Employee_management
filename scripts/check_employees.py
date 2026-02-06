from database_manager import DatabaseManager
from repositories import EmployeeRepository

if __name__ == '__main__':
    db = DatabaseManager()
    repo = EmployeeRepository(db)
    employees = repo.list_employees()
    print(f"Found {len(employees)} employees")
    for e in employees:
        monthly = e.get('salary', 0)
        yearly = monthly * 12
        print(f"{e['id']}: {e['name']}, Monthly: {monthly}, Yearly: {yearly:,.2f}")
    db.close()
