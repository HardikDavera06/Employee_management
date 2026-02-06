from database_manager import DatabaseManager
from repositories import CorrectionRepository

if __name__ == '__main__':
    db = DatabaseManager()
    repo = CorrectionRepository(db)
    requests = repo.list_corrections()
    print(f"Found {len(requests)} requests")
    for r in requests[:20]:
        print(r)
    db.close()
