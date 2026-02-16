# Hope Academy School Management System - Installation & Deployment Guide

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Pre-Installation Checklist](#pre-installation-checklist)
3. [Development Installation](#development-installation)
4. [Production Installation](#production-installation)
5. [Database Setup](#database-setup)
6. [Configuration](#configuration)
7. [First-Time Setup](#first-time-setup)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)
10. [Backup & Recovery](#backup--recovery)

---

## System Requirements

### Hardware Requirements

**Minimum**:
- Processor: Intel Core i5 or equivalent
- RAM: 4GB
- Storage: 2GB free space
- Network: Ethernet or WiFi for database connection

**Recommended**:
- Processor: Intel Core i7 or equivalent
- RAM: 8GB
- Storage: 5GB free space
- Network: Dedicated Ethernet connection

### Software Requirements

**Operating System**:
- Windows 7 SP1 or higher (XP/2003 not supported)
- Windows Server 2012 or higher
- Linux (Ubuntu 18.04+, CentOS 7+)
- macOS 10.12 or higher

**Database**:
- MySQL 5.7 or higher
- MariaDB 10.1 or higher (compatible)
- MySQL 8.0+ (recommended)

**Python**:
- Python 3.8 or higher
- Python 3.11+ (recommended for Windows 11)

**Network**:
- TCP/IP support for MySQL communication
- Port 3306 accessible for database server

### Browser (Optional)
- For future web interface: Chrome, Firefox, Edge (latest)

---

## Pre-Installation Checklist

Before beginning installation, ensure:

- [ ] MySQL Server is installed and running
- [ ] MySQL root password is known
- [ ] Python 3.8+ is installed and in PATH
- [ ] 2GB+ disk space available
- [ ] Administrator rights available (Windows)
- [ ] Network connectivity to database server confirmed
- [ ] Firewall rules allow port 3306 (if remote MySQL)
- [ ] Backup of existing data (if upgrading)

### Verify Requirements

**Check Python Installation**:
```bash
python --version
# Output should be 3.8 or higher

pip --version
# Verify pip is working
```

**Check MySQL Installation**:
```bash
mysql --version
# Output should show MySQL version

# Test connection
mysql -h localhost -u root -p
# Enter password when prompted
```

---

## Development Installation

### Step 1: Clone Repository

```bash
# Using HTTPS
git clone https://github.com/ChikondiChambamba/Hope_Academy_School_Management_System.git

# Or using SSH (if SSH keys configured)
git clone git@github.com:ChikondiChambamba/Hope_Academy_School_Management_System.git

# Navigate to project
cd Hope_Academy_School_Management_System
```

### Step 2: Create Virtual Environment

**Windows**:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# If PowerShell execution policy prevents execution, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**macOS/Linux**:
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installation
pip list
```

**Expected Packages**:
- mysql-connector-python 9.5.0
- pandas 2.0.3
- reportlab 4.4.7
- openpyxl 3.1.2
- Pillow 10.0.0
- python-dateutil 2.8.2

### Step 4: Configure Database Connection

Edit `config.py`:

```python
DB_CONFIG = {
    'host': 'localhost',          # MySQL server address
    'user': 'root',               # MySQL username
    'password': 'your_password',  # MySQL password
    'database': 'school_management',
    'port': 3306,                 # MySQL port (default 3306)
    'autocommit': True
}
```

### Step 5: Initialize Database

Run setup script:

```bash
python setup_database.py
```

**Expected Output**:
```
1. Checking database connection...
2. Creating database...
3. Creating tables...
4. Verifying table creation...
Created XX tables:
  - students
  - teachers
  - fee_types
  - ... (other tables)

Database setup completed successfully!
```

### Step 6: Verify Setup

```bash
# Check if database was created
python scripts/check_classes.py

# Run application
python main.py
```

---

## Production Installation

### Step 1: Create Application Directory

**Windows**:
```bash
mkdir C:\School_Management_System
cd C:\School_Management_System
```

**Linux/macOS**:
```bash
sudo mkdir /opt/school_management
sudo chown $USER:$USER /opt/school_management
cd /opt/school_management
```

### Step 2: Download Application

```bash
# Copy files to production directory
# Option 1: Git clone (recommended)
git clone https://github.com/ChikondiChambamba/Hope_Academy_School_Management_System.git .

# Option 2: Extract from release package
unzip Hope_Academy_School_Management_System.zip -d .

# Set permissions (Linux/macOS)
chmod 755 *.py
chmod 755 scripts/*.py
```

### Step 3: Set Up Production Environment

**Windows**:
```bash
# Create virtual environment
python -m venv venv

# Activate
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

**Linux/macOS**:
```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Configure for Production

**Database Configuration**:

Edit `config.py`:
```python
# Use centralized database server (not localhost)
DB_CONFIG = {
    'host': 'database.server.ip',      # Database server IP
    'user': 'school_app',              # App-specific user
    'password': 'secure_password',     # Strong password
    'database': 'school_management',
    'port': 3306,
    'autocommit': True,
    'pool_name': 'production_pool',
    'pool_size': 10                    # Increase for production
}

# Set production mode
THEME_MODE = 'light'
APP_CONFIG = {
    'name': 'Hope Academy School Management System',
    'version': '1.0.0',
    'academic_year': '2025-2026'
}
```

**Security Settings**:
```python
# Use environment variables for sensitive data
import os

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'school_management'),
    'port': int(os.getenv('DB_PORT', 3306))
}
```

### Step 5: Initialize Production Database

```bash
# Create production database
python setup_database.py

# Verify tables created
mysql -h database.server.ip -u school_app -p school_management < database/schema.sql
```

### Step 6: Create Automated Backups

**Windows Task Scheduler**:

Create batch file `backup.bat`:
```batch
@echo off
cd C:\School_Management_System
venv\Scripts\python.exe scripts/backup_database.py
```

Schedule daily:
```
taskscheduler.msc
> Create Basic Task
> Name: School Management Backup
> Trigger: Daily at 2:00 AM
> Action: Run backup.bat
```

**Linux Cron**:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /opt/school_management && ./venv/bin/python scripts/backup_database.py
```

---

## Database Setup

### Remote Database Setup

**Step 1: Create MySQL User**

On database server:
```sql
-- Create application user
CREATE USER 'school_app'@'192.168.1.%' IDENTIFIED BY 'secure_password_123';

-- Grant permissions
GRANT ALL PRIVILEGES ON school_management.* TO 'school_app'@'192.168.1.%';
FLUSH PRIVILEGES;

-- Verify user
SELECT User, Host FROM mysql.user WHERE User='school_app';
```

**Step 2: Enable Remote Connections**

Edit MySQL configuration (`my.cnf` or `my.ini`):
```ini
[mysqld]
# Allow remote connections
bind-address = 0.0.0.0
port = 3306
```

Restart MySQL:
```bash
# Windows
net restart MySQL80

# Linux
sudo systemctl restart mysql

# macOS
sudo /usr/local/mysql/support-files/mysql.server restart
```

**Step 3: Verify Remote Connection**

From application server:
```bash
mysql -h database.server.ip -u school_app -p -D school_management

# Test query
mysql> SELECT @@version;
```

### Initialize Database with Sample Data

```bash
# Run database setup
python setup_database.py

# Load sample data (optional)
python scripts/add_sample_classes.py

# Verify data
python scripts/check_classes.py
```

---

## Configuration

### Application Settings

Edit `config.py`:

```python
# Academic Settings
APP_CONFIG = {
    'name': 'Hope Academy Primary School',
    'version': '1.0.0',
    'academic_year': '2025-2026',
    'default_term': 'Term 1',
    'address': 'Zomba, Chinamwali, Malawi',
    'phone': '0885159301',
    'email': 'HopeAcademy@org.com'
}

# UI Settings
UI = {
    'theme': 'clam',                    # clam, alt, default, classic
    'primary_color': '#2E86C1',
    'secondary_color': '#28B463',
    'font_family': 'Segoe UI',
    'font_size_title': 16,
    'font_size_large': 12,
    'font_size_small': 10
}

# Financial Settings
CURRENCY_SYMBOL = 'MK '
CURRENCY_CODE = 'MWK'
PHONE_COUNTRY_CODE = '+265'

# Validation Rules
VALIDATION = {
    'min_student_age': 3,
    'max_student_age': 18
}

# User Roles & Permissions
PERMISSIONS = {
    'Administrator': {
        'dashboard', 'students', 'teachers', 'attendance',
        'finance', 'inventory', 'reports'
    },
    'Headteacher': {
        'dashboard', 'students', 'teachers', 'attendance', 'reports'
    },
    'Finance': {
        'dashboard', 'finance', 'inventory', 'reports'
    },
    'Teacher': {
        'dashboard', 'attendance'
    }
}
```

### Environment Variables

Create `.env` file:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=school_management
DB_PORT=3306

APP_DEBUG=False
APP_LOG_LEVEL=INFO
```

Load in Python:
```python
from dotenv import load_dotenv
import os

load_dotenv()
DB_HOST = os.getenv('DB_HOST')
```

---

## First-Time Setup

### Initial Login

1. **Start Application**
   ```bash
   python main.py
   ```

2. **First-Time User Creation**
   - File > Manage Users
   - Click "Add User"
   - Create administrator account
   - Set password

3. **Configure Academic Year**
   - Edit > Preferences
   - Set current academic year
   - Set term dates

4. **Setup Fee Types**
   - Finance tab
   - Add fee types:
     - Tuition
     - Uniform
     - Registration
     - etc.

5. **Add Classes**
   ```bash
   python scripts/add_sample_classes.py
   ```

6. **Add Sample Data** (Optional)
   - Students tab > Add Students
   - Teachers tab > Add Teachers

---

## Troubleshooting

### Database Connection Issues

**Problem**: "Failed to connect to database"

**Solutions**:
1. Verify MySQL is running
   ```bash
   # Windows
   Get-Service | where {$_.Name -like "*MySQL*"}
   
   # Linux
   sudo systemctl status mysql
   ```

2. Check credentials in `config.py`
   ```bash
   mysql -h localhost -u root -p
   ```

3. Verify database exists
   ```sql
   SHOW DATABASES;
   SHOW TABLES;
   ```

4. Check firewall rules
   ```bash
   # Windows: Allow port 3306
   netsh advfirewall firewall add rule name="MySQL" dir=in action=allow protocol=tcp localport=3306
   ```

---

### Python Import Errors

**Problem**: "No module named 'mysql.connector'"

**Solution**:
```bash
# Verify virtual environment is activated
which python  # Linux/macOS
where python  # Windows

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

### Application Won't Start

**Problem**: "AttributeError" or "ModuleNotFoundError"

**Solutions**:
1. Verify Python version
   ```bash
   python --version  # Should be 3.8+
   ```

2. Check all dependencies installed
   ```bash
   pip list
   ```

3. Clear cache and rebuild
   ```bash
   rm -r __pycache__  # Linux/macOS
   rmdir /s __pycache__  # Windows
   
   python main.py
   ```

---

### Performance Issues

**Problem**: "Application is slow / freezes"

**Solutions**:
1. Check database indexes
   ```sql
   SHOW INDEX FROM students;
   ```

2. Optimize database tables
   ```sql
   OPTIMIZE TABLE students;
   OPTIMIZE TABLE student_fees;
   ```

3. Increase connection pool size in `config.py`
   ```python
   'pool_size': 10  # Increase from 5
   ```

4. Monitor disk space
   ```bash
   # Windows
   dir C:\
   
   # Linux
   df -h
   ```

---

## Maintenance

### Regular Tasks

**Daily**:
- Monitor application logs
- Check data entry
- Verify backups completed

**Weekly**:
- Run database optimization
  ```bash
  python scripts/optimize_database.py
  ```
- Review error logs
- Test backup restoration

**Monthly**:
- Full database backup
- Performance analysis
- Security review

**Quarterly**:
- Database maintenance
- Security patches
- Software updates

### Monitoring

Check application logs:
```bash
# Windows
type data\logs\app.log

# Linux
cat data/logs/app.log
```

Monitor database:
```sql
-- Check database size
SELECT table_schema AS "Database", 
       SUM(data_length + index_length) / 1024 / 1024 AS "Size in MB" 
FROM information_schema.TABLES 
GROUP BY table_schema;

-- Check slow queries
SHOW VARIABLES LIKE 'slow_query_log';
SHOW PROCESSLIST;
```

---

## Backup & Recovery

### Manual Backup

**Full Database Backup**:
```bash
python scripts/backup_database.py
```

**Export Data to Excel**:
```bash
python -c "from utils.export_import import export_all_data; export_all_data()"
```

### Automatic Backups

**Windows Scheduled Task**:
```batch
@echo off
cd C:\School_Management_System
venv\Scripts\python.exe -c "from utils.export_import import backup_database; backup_database()"
```

**Linux Cron**:
```bash
0 2 * * * /opt/school_management/venv/bin/python -c "from utils.export_import import backup_database; backup_database()"
```

### Recovery Procedure

**From Backup**:
```bash
# 1. Stop application
# 2. Restore database
python scripts/restore_database.py backup_file.sql

# 3. Verify restoration
python scripts/check_classes.py

# 4. Restart application
python main.py
```

**From Fresh Installation**:
```bash
# If all else fails, reinstall
python setup_database.py
# Then restore from backup if available
```

---

## Deployment Checklist

Before going live:

- [ ] Database backed up
- [ ] All users created
- [ ] Academic year configured
- [ ] Fee types configured
- [ ] Classes created
- [ ] Sample data loaded (optional)
- [ ] Backup schedule configured
- [ ] Firewall rules configured
- [ ] SSL/TLS configured (if applicable)
- [ ] User manual provided
- [ ] Support contact established
- [ ] Disaster recovery plan in place

---

## Support & Updates

### Getting Help

1. Check documentation
   - README.md
   - DEVELOPER_GUIDE.md
   - user_manual_full.md

2. Review troubleshooting
   - docs/TROUBLESHOOTING.md
   - Application logs (data/logs/app.log)

3. Contact support
   - GitHub Issues: https://github.com/ChikondiChambamba/...
   - Email: support@hopeacademy.org

### Updating Application

**To Latest Version**:
```bash
# Backup current version
cp -r . ../Hope_Academy_Backup

# Pull latest code
git pull origin main

# Verify no conflicts
git status

# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Database migration if needed
python scripts/migrate_latest.py

# Restart application
python main.py
```

---

**Document Version**: 1.0  
**Last Updated**: January 2026  
**Maintained By**: Development & Operations Team

