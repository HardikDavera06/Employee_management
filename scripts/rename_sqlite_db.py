import os
p = os.path.join(os.path.dirname(__file__), '..', 'employee_system.db')
p = os.path.abspath(p)
if os.path.exists(p):
    try:
        os.rename(p, p + '.bak')
        print('Renamed:', p, '->', p + '.bak')
    except Exception as e:
        print('Failed rename:', e)
else:
    print('employee_system.db not found at', p)
