from database_manager import DatabaseManager

if __name__ == '__main__':
    try:
        db = DatabaseManager()
        print("Connected!", db.engine)
        if db.engine == 'mysql':
            cur = db._get_cursor()
            cur.execute('SELECT VERSION()')
            v = cur.fetchone()
            print('MySQL version:', v)
        db.close()
    except Exception as e:
        print('Failed to connect to MySQL:', e)
