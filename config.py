# Central config for the project

DEFAULT_OVERTIME_RATE = 100.0
# Email / SMTP configuration used for notifications (leave host blank to disable SMTP)
SMTP = {
	"host": "",
	"port": 587,
	"username": "",
	"password": "",
	"use_tls": True,
	"from_email": "no-reply@company.com",
	"admin_emails": [],
}

# Database configuration (MySQL only)
DB = {
	"engine": "mysql",
	# MySQL connection (used when engine == 'mysql')
	"mysql": {
		"host": "localhost",
		"user": "root",
		"password": "",
		"database": "employee_db",
		"port": 3306,
	},
}
