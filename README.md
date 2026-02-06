# Employee Management System

A refactored, modular employee management system with integrated payroll and leave management capabilities. Built with Python and Tkinter, featuring multi-user support (Admin and Employee roles), MySQL database integration, and email notification capabilities.

## Table of Contents

- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Setup Instructions](#setup-instructions)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Email Notifications](#email-notifications)
- [Troubleshooting](#troubleshooting)
- [Scripts and Testing](#scripts-and-testing)

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

- **Python 3.7+** (Python 3.8+ recommended)
- **MySQL Server 5.7+** (or newer)
- **pip** (Python package manager)
- A desktop environment with graphical support (for Tkinter)

### Required Packages

The following packages are **mandatory** for this application to work:

| Package | Version | Purpose |
|---------|---------|---------|
| `mysql-connector-python` | Latest | MySQL database connectivity |
| `tkcalendar` | Latest | Calendar widget for date selection in GUI |
| `fpdf2` | Latest | PDF generation for salary slips |
| `openpyxl` | Latest | Excel file handling for data exports |

### Optional Packages

- **tkinter**: Usually comes pre-installed with Python on Windows and macOS

*** ## Downloading and Installing Packages ***

### What is pip?

`pip` is the Python package installer that allows you to download and install Python packages from the Python Package Index (PyPI). It comes automatically with Python 3.4+ installations.

### Verify pip Installation

Before installing packages, verify that `pip` is installed on your system:

```powershell
# On Windows
pip --version


You should see an output like: `pip 23.x.x from C:\...\site-packages\pip (python 3.x.x)`

### Method 1: Install All Packages Using requirements.txt (Recommended)

This is the easiest and most reliable method to install all required packages at once.

#### On Windows (PowerShell):

```powershell
# Navigate to the project directory
cd "d:\python project"

# Install all packages from requirements.txt
pip install -r requirements.txt
```

#### On Linux/macOS (Terminal):

```bash
# Navigate to the project directory
cd python\ project

# Install all packages from requirements.txt
pip3 install -r requirements.txt
```

**What this does**:
- Reads the `requirements.txt` file
- Downloads all specified packages automatically
- Installs them in the correct order
- Resolves any dependencies

### Method 2: Install Individual Packages Manually

If you prefer to install packages one by one or need to install additional packages later:

#### Install MySQL Connector

The package that allows Python to connect to MySQL databases:

```powershell
# Windows
pip install mysql-connector-python
```

**Latest version**: Usually `mysql-connector-python` (version 8.0+)

#### Install tkcalendar

Calendar widget for date selection in the GUI:

```powershell
# Windows
pip install tkcalendar

**Latest version**: `tkcalendar` (version 1.6+)

#### Install fpdf2

PDF generation library for creating salary slips:

```powershell
# Windows
pip install fpdf2`

**Latest version**: `fpdf2` (version 2.7+)

#### Install openpyxl

Excel file handling for data exports:

```powershell
# Windows
pip install openpyxl

**Latest version**: `openpyxl` (version 3.0+)

#### Install All at Once (Alternative)

Install all packages in a single command:

```powershell
# Windows
pip install mysql-connector-python tkcalendar fpdf2 openpyxl


### Method 3: Using a Virtual Environment (Recommended for Development)

Virtual environments isolate project dependencies from your system Python installation.

#### On Windows (PowerShell):

```powershell
# Navigate to project directory
cd "d:\python project"

# Create a virtual environment named 'venv'
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Now install packages (they'll be isolated to this environment)
pip install -r requirements.txt

# To deactivate the virtual environment later
deactivate
```

#### On Linux/macOS (Terminal):

```bash
# Navigate to project directory
cd python\ project

# Create a virtual environment named 'venv'
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Now install packages (they'll be isolated to this environment)
pip3 install -r requirements.txt

# To deactivate the virtual environment later
deactivate
```

**Benefits of Virtual Environments**:
- Isolates project dependencies
- Prevents version conflicts with other projects
- Easy to recreate the exact environment on another system
- Easier to manage multiple Python projects

### Verify Package Installation

After installing packages, verify that all required packages are installed:

```powershell
# On Windows
pip list

# On Linux/macOS
pip3 list
```

You should see output listing all installed packages including:
- `mysql-connector-python`
- `tkcalendar`
- `fpdf2`
- `openpyxl`

Or use this command to check specific packages:

```powershell
# Windows
pip show mysql-connector-python
pip show tkcalendar
pip show fpdf2
pip show openpyxl

# Linux/macOS
pip3 show mysql-connector-python
pip3 show tkcalendar
pip3 show fpdf2
pip3 show openpyxl
```

### Upgrade Packages to Latest Version

To upgrade packages to their latest versions:

```powershell
# Windows
pip install --upgrade mysql-connector-python
pip install --upgrade tkcalendar
pip install --upgrade fpdf2
pip install --upgrade openpyxl

# Or all at once
pip install --upgrade mysql-connector-python tkcalendar fpdf2 openpyxl

# Linux/macOS
pip3 install --upgrade mysql-connector-python tkcalendar fpdf2 openpyxl
```

### Troubleshooting Package Installation

#### Issue 1: "pip is not recognized as an internal or external command"

**Solution**:
- Python is not installed or not in PATH
- Reinstall Python and make sure "Add Python to PATH" is checked during installation
- Or use `python -m pip` instead of `pip`:
  ```powershell
  python -m pip install -r requirements.txt
  ```

#### Issue 2: "Permission denied" error on Linux/macOS

**Solution**: Use `pip3` instead of `pip`, or add `--user` flag:
```bash
pip3 install --user -r requirements.txt
```

#### Issue 3: "Could not find a version that satisfies the requirement"

**Solution**:
- Check internet connection
- Verify package name is correct
- Try upgrading pip: `python -m pip install --upgrade pip`

#### Issue 4: SSL Certificate Error

**Solution**:
```powershell
pip install --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
```

#### Issue 5: Package installed but still getting "ModuleNotFoundError"

**Solution**:
- Make sure you're using the same Python/environment where packages were installed
- Check if virtual environment is activated (if using one)
- Restart your IDE/terminal after installation

### Understanding requirements.txt

The `requirements.txt` file in the project specifies all required packages. Current contents:

```
tkcalendar
fpdf2
mysql-connector-python
openpyxl
```

Each line represents a package to be installed. You can:
- Add new packages by adding a line with the package name
- Specify versions: `package_name==1.2.3`
- Install from a modified requirements file: `pip install -r my_requirements.txt`

### Step 1: Clone or Download the Project

```bash
# If using git
git clone <repository-url>
cd python\ project
```

### Step 2: Install Python Dependencies

```powershell
# On Windows (PowerShell)
pip install -r requirements.txt
```

Or install manually:

```powershell
pip install mysql-connector-python tkcalendar fpdf2 openpyxl
```

### Step 3: Configure Database Connection

Edit `config.py` and set your MySQL credentials:

```python
DB = {
    "engine": "mysql",
    "mysql": {
        "host": "localhost",
        "user": "root",
        "password": "your_password",
        "database": "employee_db",
        "port": 3306,
    },
}
```

### Step 4: Create MySQL Database

```sql
CREATE DATABASE employee_db;
CREATE USER 'erp_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON employee_db.* TO 'erp_user'@'localhost';
FLUSH PRIVILEGES;
```

Or use the default root user with appropriate credentials.

## Setup Instructions

### For Windows Systems

1. **Install Python** from [python.org](https://www.python.org/) (ensure you check "Add Python to PATH")

2. **Install MySQL Server** from [mysql.com](https://dev.mysql.com/downloads/mysql/)
   - During installation, set up a root user with a password
   - Remember the credentials

3. **Clone/Download Project** to a local folder

4. **Open PowerShell** in the project directory

5. **Create a Virtual Environment** (Optional but recommended):
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

6. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

7. **Update `config.py`** with your MySQL credentials

8. **Run the Application**:
   ```powershell
   python employee.py
   ```

### Starting the Application

```powershell
python employee.py
```

The application will launch a GUI window with login functionality.

### Default Access

**Admin Login**:
- Username: `EMP001`
- Password: `admin123` (or as set during initial setup)

**Employee Login**:
- Employees can log in with their assigned employee ID and credentials

**Requirements**:
- GUI requires a desktop environment (Tkinter)
- PDF generation requires `fpdf2` package
- MySQL server must be running and accessible

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|------------|
| Python | 3.7+ (3.9+ recommended) |
| RAM | 2 GB |
| Disk Space | 500 MB (excluding MySQL data) |
| MySQL | 5.7+ |

### Network

- MySQL can be local (localhost) or remote
- Email notifications require internet access (if SMTP enabled)

## Project Structure

```
python project/
├── employee.py                      # Main application entry point
├── admin_dashboard.py               # Admin panel and employee management
├── employee_dashboard.py            # Employee dashboard and leave management
├── employee_salary.py               # Salary corrections and payslip features
├── database_manager.py              # Database abstraction layer
├── repositories.py                  # Data access layer
├── notifier.py                      # Email notification system
├── config.py                        # Configuration file
├── database.py                      # Database initialization
├── requirements.txt                 # Python dependencies
├── employees.json                   # Employee data export
├── leaves.json                      # Leave data export
├── README.md                        # This file
├── DOCUMENTATION_INDEX.md           # Detailed technical documentation
├── scripts/                         # Utility and testing scripts
│   ├── check_assignments.py
│   ├── check_employees.py
│   ├── check_payroll.py
│   ├── check_requests.py
│   ├── migrate_sqlite_to_mysql.py
│   ├── test_*.py                   # Various test scripts
│   └── ...
└── salary_exports/                 # CSV exports of salary data
    └── [exported_files].csv
```

## Configuration

## Configuration

### Main Configuration File: `config.py`

The application uses a centralized configuration file. Edit `config.py` to customize:

#### Database Configuration

```python
DB = {
    "engine": "mysql",  # Always "mysql"
    "allow_sqlite_fallback": False,  # Enable SQLite fallback for development
    "mysql": {
        "host": "localhost",        # MySQL server hostname/IP
        "user": "root",             # MySQL username
        "password": "",             # MySQL password
        "database": "employee_db",  # Database name
        "port": 3306,               # MySQL port (default 3306)
    },
}
```

#### Overtime Rate Configuration

```python
DEFAULT_OVERTIME_RATE = 100.0  # Overtime rate in Rs. per hour
```

#### Email/SMTP Configuration

```python
SMTP = {
    "host": "",                          # SMTP server (leave blank to disable)
    "port": 587,                         # SMTP port
    "username": "",                      # SMTP username
    "password": "",                      # SMTP password
    "use_tls": True,                     # Use TLS encryption
    "from_email": "no-reply@company.com",# Sender email address
    "admin_emails": [],                  # List of admin emails for notifications
}
```

### Configuration Examples

#### Example 1: Remote MySQL Server

```python
DB = {
    "engine": "mysql",
    "mysql": {
        "host": "192.168.1.100",
        "user": "erp_user",
        "password": "secure_password",
        "database": "employee_db",
        "port": 3306,
    },
}
```

#### Example 2: With Email Notifications

```python
SMTP = {
    "host": "smtp.gmail.com",
    "port": 587,
    "username": "your-email@gmail.com",
    "password": "app_specific_password",
    "use_tls": True,
    "from_email": "erp-system@company.com",
    "admin_emails": ["admin1@company.com", "admin2@company.com"],
}
```

## Database Setup

## Database Setup

### MySQL Database Architecture

This project uses **MySQL** as the primary database backend with optional SQLite fallback for development.

### Initial MySQL Setup

#### Method 1: Using MySQL Command Line

1. **Start MySQL Server**:
   ```bash
   # Windows
   # MySQL starts automatically after installation

2. **Connect to MySQL**:
   ```bash
   mysql -u root -p
   ```

3. **Create Database and User**:

```sql
-- Create the database
CREATE DATABASE IF NOT EXISTS employee_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create a dedicated user (recommended for security)
CREATE USER 'erp_user'@'localhost' IDENTIFIED BY 'secure_password_here';

-- Grant all privileges on the database to the user
GRANT ALL PRIVILEGES ON employee_db.* TO 'erp_user'@'localhost';

-- Flush privileges to apply changes
FLUSH PRIVILEGES;

-- Verify
SHOW GRANTS FOR 'erp_user'@'localhost';
```

4. **Configure in `config.py`**:

```python
DB = {
    "engine": "mysql",
    "mysql": {
        "host": "localhost",
        "port": 3306,
        "user": "erp_user",
        "password": "secure_password_here",
        "database": "employee_db",
    },
}
```

5. **Automatic Table Creation**:

The application will automatically create all required tables on first run. Tables include:
- `employees` - Employee master data
- `leaves` - Leave records
- `salary_assignments` - Monthly salary assignments
- `payroll` - Payroll records
- `salary_corrections` - Correction requests
- And other supporting tables

#### Method 2: Using a Database GUI Tool

Popular alternatives:
- **MySQL Workbench** (Official MySQL GUI)
- **DataGrip** (JetBrains)
- **DBeaver** (Free and open-source)
- **phpMyAdmin** (Web-based)

### Verify Database Connection

Run the test script to verify MySQL connection:

```powershell
python scripts/test_mysql_connection.py
```

### SQLite Fallback (Optional - Development Only)

For local development without MySQL, enable SQLite fallback in `config.py`:

```python
DB = {
    "engine": "mysql",
    "allow_sqlite_fallback": True,  # Enable fallback
    "mysql": {
        "host": "localhost",
        "user": "root",
        "password": "",
        "database": "employee_db",
        "port": 3306,
    },
}
```

**Note**: SQLite fallback is not recommended for production. Use MySQL for production deployments.

### Database Migration (SQLite to MySQL)

If you have an existing SQLite database, use the migration script:

```powershell
python scripts/migrate_sqlite_to_mysql.py
```


## Email Notifications

### Overview

Email notifications are **optional** and configurable through `config.py`. The system uses Python's built-in `smtplib` for email delivery.

### Configuration

Configure SMTP settings in `config.py` under the `SMTP` dictionary:

```python
SMTP = {
    "host": "smtp.gmail.com",                    # SMTP server hostname
    "port": 587,                                  # SMTP port (usually 587 or 465)
    "username": "your-email@gmail.com",          # SMTP username
    "password": "your_app_password",             # SMTP password or app password
    "use_tls": True,                             # Use TLS encryption
    "from_email": "erp-system@company.com",      # Sender email address
    "admin_emails": ["admin@company.com"],       # List of admin email addresses
}
```

### Disabling Email Notifications

To disable email notifications (notifications will be logged locally instead):

```python
SMTP = {
    "host": "",  # Leave host empty to disable
    "port": 587,
    "username": "",
    "password": "",
    "use_tls": True,
    "from_email": "no-reply@company.com",
    "admin_emails": [],
}
```

When disabled, notifications are logged to `salary_notifications.log` for testing purposes.

### Notification Types and Recipients

| Event | Recipients | Trigger |
|-------|-----------|---------|
| New correction request submitted | Admin emails + Request submitter | Employee submits salary correction request |
| Request status: Resolved | Request submitter | Admin marks request as Resolved |
| Request status: Withdrawn | Request submitter | Employee withdraws their request |

### SMTP Server Configuration Examples

#### Gmail

```python
SMTP = {
    "host": "smtp.gmail.com",
    "port": 587,
    "username": "your-email@gmail.com",
    "password": "your_16_char_app_password",  # Use App Password, not regular password
    "use_tls": True,
    "from_email": "your-email@gmail.com",
    "admin_emails": ["admin@company.com"],
}
```

**Note**: For Gmail, enable 2-Factor Authentication and create an App Password.

#### Outlook/Office 365

```python
SMTP = {
    "host": "smtp.office365.com",
    "port": 587,
    "username": "your-email@outlook.com",
    "password": "your_password",
    "use_tls": True,
    "from_email": "your-email@outlook.com",
    "admin_emails": ["admin@company.com"],
}
```

#### Corporate SMTP Server

```python
SMTP = {
    "host": "mail.company.com",
    "port": 587,
    "username": "username",
    "password": "password",
    "use_tls": True,
    "from_email": "erp-system@company.com",
    "admin_emails": ["admin@company.com"],
}
```

### Troubleshooting Email Issues

1. **Test Email Configuration**:
   ```powershell
   python scripts/test_notifications.py
   ```

2. **Common Issues**:
   - **Connection timeout**: Check firewall rules, verify host and port
   - **Authentication failed**: Verify username/password, check app-specific passwords
   - **TLS errors**: Try port 465 with TLS, or port 587 with TLS
   - **From address rejected**: Verify from_email matches SMTP user account

3. **Logs**:
   - When SMTP is disabled: Check `salary_notifications.log`
   - Application logs: Check console output

## Troubleshooting

### Common Issues and Solutions

#### 1. "MySQL connection failed"

**Problem**: Application cannot connect to MySQL
```
Error: MySQL Error 2003: Can't connect to MySQL server
```

**Solutions**:
- Verify MySQL server is running
- Check hostname/IP in `config.py`
- Verify port (default 3306)
- Check username and password
- Test with: `python scripts/test_mysql_connection.py`

#### 2. "ModuleNotFoundError: No module named 'mysql'"

**Problem**: MySQL Python connector not installed

**Solution**:
```powershell
pip install mysql-connector-python
```

#### 3. "ModuleNotFoundError: No module named 'tkinter'"

**Problem**: Tkinter not installed

**Solution**:
- **Windows**: Usually included with Python; reinstall Python with tcl/tk option
- **Linux**: `sudo apt install python3-tk`
- **macOS**: `brew install python-tk`

#### 4. "ModuleNotFoundError: No module named 'fpdf2'"

**Problem**: FPDF library not installed

**Solution**:
```powershell
pip install fpdf2
```

#### 5. "No data in tables after starting application"

**Problem**: Tables created but no initial data

**Solution**: Import initial employee data:
```powershell
python scripts/check_employees.py
```

#### 6. Application freezes on startup

**Problem**: Database operations taking too long

**Solutions**:
- Check MySQL server status
- Verify network connectivity (for remote MySQL)
- Try closing and restarting the application
- Check database logs for issues

#### 7. PDF generation fails

**Problem**: Cannot generate payslips

**Solution**: Ensure fpdf2 is installed:
```powershell
pip install --upgrade fpdf2
```

### Getting Help

- Check `DOCUMENTATION_INDEX.md` for technical documentation
- Review application logs in console output
- Check `salary_notifications.log` for email issues
- Run test scripts in `scripts/` folder for diagnostics

## Scripts and Testing

### Available Test Scripts

The `scripts/` folder contains utility and test scripts:

| Script | Purpose |
|--------|---------|
| `test_mysql_connection.py` | Verify MySQL connectivity |
| `test_notifications.py` | Test email notification configuration |
| `test_assignments.py` | Verify salary assignment functionality |
| `test_corrections.py` | Test payslip correction feature |
| `test_filters.py` | Verify data filtering logic |
| `test_leave_deduction.py` | Test leave deduction calculations |
| `test_monthly_uniqueness.py` | Verify monthly salary uniqueness constraints |
| `check_employees.py` | View and manage employee data |
| `check_payroll.py` | Review payroll records |
| `check_requests.py` | Check correction requests |
| `check_assignments.py` | Verify salary assignments |
| `migrate_sqlite_to_mysql.py` | Migrate data from SQLite to MySQL |

### Running Test Scripts

```powershell
# Test MySQL connection
python scripts/test_mysql_connection.py

# Test email notifications
python scripts/test_notifications.py

# Check employee data
python scripts/check_employees.py
```

## User Roles and Permissions

### Admin Role

- Manage employees (add, edit, delete)
- Assign monthly salaries
- Review payslip correction requests
- Export salary data
- View payroll records
- Manage leave types and balances

### Employee Role

- View personal salary information
- Submit payslip correction requests
- Track leave balance
- Apply for leave
- Download payslips as PDF
- Export personal salary history

## Key Features

### For Employees

1. **My Salary Dashboard**: 
   - View complete salary history
   - See payroll records
   - Track deductions, overtime, bonuses

2. **Payslip Correction Requests**:
   - Submit corrections for disputed payslips
   - Track request status
   - Withdraw requests if needed

3. **Pay Estimation Tool**:
   - Estimate next month's pay
   - Simulate different overtime/bonus/deduction scenarios
   - Fixed overtime rate: Rs. 100 per hour

4. **Leave Management**:
   - Apply for leave
   - Track leave balance
   - View leave history

### For Admins

1. **Employee Management**:
   - Add new employees
   - Edit employee information
   - Delete employees
   - View employee database

2. **Salary Management**:
   - Assign monthly salaries
   - View assignment history
   - Delete assignments with automatic reversion

3. **Correction Request Management**:
   - Review pending requests
   - Export corrections as CSV
   - Mark requests as Resolved

4. **Payroll Operations**:
   - Generate payroll records
   - Create salary slips
   - Export salary data

## System Architecture

The application follows a modular architecture:

```
┌─────────────────────────────────────┐
│   employee.py (Main Entry Point)    │
└──────────────┬──────────────────────┘
               │
        ┌──────┴───────┬───────────────┬──────────────┐
        │              │               │              │
   ┌────▼─────┐  ┌─────▼────┐  ┌──────▼─┐  ┌────────▼────┐
   │   Admin   │  │ Employee │  │Salary  │  │  Database   │
   │ Dashboard │  │Dashboard │  │  UI    │  │  Manager    │
   └──────────┘  └────────────┘ └────────┘  └─────┬──────┘
                                                   │
                                            ┌──────┴──────┐
                                            │             │
                                       ┌────▼──┐    ┌────▼────┐
                                       │ MySQL │    │Repositories
                                       └───────┘    └──────────┘
```

## License and Support

This is a comprehensive Employee Management System designed for organizational use. For support or feature requests, contact the development team.

