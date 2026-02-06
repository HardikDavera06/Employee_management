# Employee Management System

A refactored, modular employee management system with integrated payroll and leave management capabilities.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Email Notifications](#email-notifications)

## Features

### Employee Features

- **My Salary Dashboard**: Centralized view of salary information
  - View complete salary history including payroll records
  - Track base salary, deductions, overtime, bonus, and net pay
  - Download payslip PDFs
  - Export salary history to CSV format

- **Payslip Correction Requests**: 
  - Employees can request corrections on payslips through the system
  - View and withdraw correction requests from the My Salary page
  - Correction requests stored in `salary_corrections` table for admin review

- **Pay Estimation Tool**: 
  - Estimate next pay with custom overtime/bonus/deductions inputs
  - Uses existing leave deduction logic
  - Fixed overtime rate: Rs. 100 per hour

### Admin Features

- **Correction Request Management**: 
  - Review pending payslip correction requests
  - Export correction data to CSV
  - Mark requests as Resolved
  - Access through Payroll page

- **Salary Assignment**:
  - Assign salaries to employees monthly from Payroll page
  - Month-aware storage ensuring one assignment per employee per month
  - View complete assignment history
  - Delete assignments with automatic salary reversion to previous assignment
  - Employee salary displayed as yearly amount in Manage Employees list

## Installation

### Prerequisites

- Python 3.7+
- MySQL Server
- pip (Python package manager)

### Setup Steps

1. **Install Python Dependencies**:

```powershell
pip install -r requirements.txt
```

2. **Install MySQL Connector**:

```powershell
pip install mysql-connector-python
```

3. **Configure Database** (see [Database Setup](#database-setup) section)

## Usage

### Running the Application

```powershell
python employee.py
```

**Requirements**:
- GUI requires a desktop environment (Tkinter)
- PDF generation requires `fpdf2` package

## Configuration

Configure the application by editing `config.py` in the project root directory.

## Database Setup

This project uses **MySQL** as the default database backend.

### Initial MySQL Setup

1. **Create Database and User**:

```sql
CREATE DATABASE employee_db;
CREATE USER 'erp_user'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON employee_db.* TO 'erp_user'@'localhost';
FLUSH PRIVILEGES;
```

2. **Configure in `config.py`**:

```python
DB = {
    "engine": "mysql",
    "mysql": {
        "host": "localhost",
        "port": 3306,
        "user": "erp_user",
        "password": "password",
        "database": "employee_db",
    },
}
```

3. **Automatic Table Creation**:

The application will create all required tables automatically on first run.

### SQLite Fallback (Optional)

For local development without MySQL, enable SQLite fallback in `config.py`:

```python
DB = {
    "engine": "mysql",
    "allow_sqlite_fallback": True,
}
```

## Email Notifications

Email notifications are optional and configurable through `config.py`.

### Configuration

- Notifications use Python's built-in `smtplib`
- Configure SMTP settings in `config.py` under the `SMTP` dictionary
- If `SMTP['host']` is empty, notifications are logged to `salary_notifications.log` (for local testing)

### Notification Types

| Event | Recipients |
|-------|-----------|
| New correction request | Admin emails + Submitter |
| Request status change (Resolved/Withdrawn) | Submitter |

