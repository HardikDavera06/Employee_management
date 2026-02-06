from config import DB
from database_manager import DatabaseManager

if __name__ == '__main__':
    # Simulate forcing fallback
    old_mysql = DB.get('mysql')
    DB['mysql'] = None
    DB['allow_sqlite_fallback'] = True
    try:
        db = DatabaseManager(db_path=':memory:')
        print('Engine used for fallback test:', db.engine)
        db.close()
    except Exception as e:
        print('Fallback test failed:', e)
    finally:
        DB['mysql'] = old_mysql
