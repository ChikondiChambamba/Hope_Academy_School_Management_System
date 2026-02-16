"""
Database Migration Script: Add Audit Log Table

This script migrates existing databases to include the audit_log table
required for the new audit logging system.

Usage:
    python migrate_audit_log.py

The script will:
1. Backup the existing database
2. Create the audit_log table if it doesn't exist
3. Create necessary indexes
4. Verify the migration was successful
"""

import sys
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from database.connection import DatabaseConnection


def backup_database():
    """Create a backup of the database before migration"""
    print("\n📦 Creating database backup...")
    try:
        from utils.export_import import DatabaseBackup
        
        backup = DatabaseBackup()
        backup_file = backup.backup_database()
        print(f"✓ Backup created: {backup_file}")
        return backup_file
    except Exception as e:
        print(f"⚠ Warning: Failed to create automatic backup: {e}")
        print("  Proceeding anyway, but ensure you have a manual backup!")
        return None


def create_audit_log_table(connection):
    """Create the audit_log table"""
    print("\n📋 Creating audit_log table...")
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS audit_log (
        log_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique audit log ID',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When the action occurred',
        action VARCHAR(50) NOT NULL COMMENT 'Type of action (LOGIN, CREATE, UPDATE, DELETE, etc)',
        user VARCHAR(100) COMMENT 'User who performed the action',
        entity_type VARCHAR(50) COMMENT 'Type of entity affected (student, payment, teacher, etc)',
        entity_id INT COMMENT 'ID of the entity affected',
        status VARCHAR(20) DEFAULT 'SUCCESS' COMMENT 'Status of the action (SUCCESS, FAILED)',
        details JSON COMMENT 'Additional details about the action',
        error_message TEXT COMMENT 'Error message if action failed',
        ip_address VARCHAR(45) COMMENT 'IP address of the user',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
        
        INDEX idx_timestamp (timestamp),
        INDEX idx_user (user),
        INDEX idx_action (action),
        INDEX idx_entity (entity_type, entity_id),
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='Audit trail for all system actions for compliance and security';
    """
    
    try:
        cursor = connection.cursor()
        cursor.execute(create_table_sql)
        connection.commit()
        print("✓ audit_log table created successfully")
        return True
    except Error as e:
        print(f"✗ Error creating audit_log table: {e}")
        return False
    finally:
        cursor.close()


def create_audit_indexes(connection):
    """Ensure all audit log indexes exist"""
    print("\n🔍 Verifying indexes...")
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_user ON audit_log(user)",
        "CREATE INDEX IF NOT EXISTS idx_action ON audit_log(action)",
        "CREATE INDEX IF NOT EXISTS idx_entity ON audit_log(entity_type, entity_id)",
        "CREATE INDEX IF NOT EXISTS idx_created_at ON audit_log(created_at)"
    ]
    
    try:
        cursor = connection.cursor()
        for index_sql in indexes_sql:
            cursor.execute(index_sql)
        connection.commit()
        print("✓ All indexes verified/created")
        return True
    except Error as e:
        print(f"⚠ Warning: Index creation issue: {e}")
        return False
    finally:
        cursor.close()


def verify_migration(connection):
    """Verify that the migration was successful"""
    print("\n✅ Verifying migration...")
    
    try:
        cursor = connection.cursor()
        
        # Check if table exists
        cursor.execute("SHOW TABLES LIKE 'audit_log'")
        if not cursor.fetchone():
            print("✗ audit_log table not found!")
            return False
        
        # Check table structure
        cursor.execute("DESCRIBE audit_log")
        columns = cursor.fetchall()
        
        required_columns = {
            'log_id', 'timestamp', 'action', 'user', 'entity_type',
            'entity_id', 'status', 'details', 'error_message', 'ip_address',
            'created_at'
        }
        
        found_columns = {col[0] for col in columns}
        
        if not required_columns.issubset(found_columns):
            missing = required_columns - found_columns
            print(f"✗ Missing columns: {missing}")
            return False
        
        # Check row count
        cursor.execute("SELECT COUNT(*) FROM audit_log")
        row_count = cursor.fetchone()[0]
        print(f"✓ Audit log table verified ({row_count} existing records)")
        
        return True
    
    except Error as e:
        print(f"✗ Verification error: {e}")
        return False
    finally:
        cursor.close()


def get_db_connection():
    """Get database connection"""
    try:
        db_connection = mysql.connector.connect(
            host=config.DB_CONFIG['host'],
            user=config.DB_CONFIG['user'],
            password=config.DB_CONFIG['password'],
            database=config.DB_CONFIG['database'],
            port=config.DB_CONFIG.get('port', 3306)
        )
        return db_connection
    except Error as e:
        print(f"✗ Database connection error: {e}")
        return None


def log_migration(backup_file, success):
    """Log migration details"""
    log_file = 'data/migration_logs.txt'
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    with open(log_file, 'a') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Migration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Type: Add Audit Log Table\n")
        f.write(f"Backup: {backup_file or 'Manual backup required'}\n")
        f.write(f"Status: {'SUCCESS' if success else 'FAILED'}\n")
        f.write(f"{'='*60}\n")


def main():
    """Execute the migration"""
    print("🔄 Starting Database Migration: Add Audit Log Table")
    print("=" * 60)
    
    # Verify database configuration
    print("\n⚙️  Verifying database configuration...")
    try:
        db_host = config.DB_CONFIG['host']
        db_name = config.DB_CONFIG['database']
        print(f"✓ Database: {db_name}")
        print(f"✓ Host: {db_host}")
    except KeyError as e:
        print(f"✗ Missing database configuration: {e}")
        return False
    
    # Create backup
    backup_file = backup_database()
    
    # Connect to database
    print("\n🔌 Connecting to database...")
    connection = get_db_connection()
    if not connection:
        print("✗ Failed to connect to database")
        return False
    print("✓ Database connection successful")
    
    # Execute migration steps
    success = True
    
    # Create audit log table
    if not create_audit_log_table(connection):
        success = False
    
    # Create indexes
    if not create_audit_indexes(connection):
        success = False
    
    # Verify migration
    if not verify_migration(connection):
        success = False
    
    # Close connection
    connection.close()
    
    # Log the migration
    log_migration(backup_file, success)
    
    # Final status
    print("\n" + "=" * 60)
    if success:
        print("✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart the School Management System")
        print("2. Audit logging will now track all user actions")
        print("3. View audit logs in Tools → View Audit Log")
    else:
        print("❌ Migration encountered errors")
        print("\nTroubleshooting:")
        print("1. Check database connection settings in config.py")
        print("2. Ensure MySQL server is running")
        print("3. Verify user has proper permissions")
        print("4. Review migration_logs.txt for details")
    
    return success


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
