#!/usr/bin/env python3
"""
Database setup script for School Management System
"""
import mysql.connector
from mysql.connector import Error
import os
import sys
import config

def create_database():
    """Create database and tables"""
    
    # Get database config without database name
    db_config = config.DB_CONFIG.copy()
    db_config.pop('database', None)
    
    try:
        print("=" * 60)
        print(f"  {config.APP_CONFIG['name']} - Database Setup")
        print("=" * 60)
        
        # Connect to MySQL server
        print("\n1. Connecting to MySQL server...")
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Create database
        print("2. Creating database...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config.DB_CONFIG['database']}")
        cursor.execute(f"USE {config.DB_CONFIG['database']}")
        
        # Read and execute schema file
        print("3. Creating tables...")
        schema_file = os.path.join('database', 'schema.sql')
        
        if not os.path.exists(schema_file):
            print(f"Error: Schema file not found at {schema_file}")
            return False
        
        with open(schema_file, 'r', encoding='utf-8') as file:
            sql_script = file.read()
        
        # First, prefer to run the schema using the `mysql` CLI if available
        import shutil, subprocess
        mysql_cli = shutil.which('mysql')
        if mysql_cli:
            try:
                with open(schema_file, 'rb') as f:
                    subprocess.run([mysql_cli,
                                    '-h', db_config.get('host', 'localhost'),
                                    '-u', db_config.get('user', ''),
                                    f"-p{db_config.get('password', '')}",
                                    config.DB_CONFIG['database']], stdin=f, check=True)
                print("   Executed schema via mysql client")
            except subprocess.CalledProcessError as e:
                print(f"   mysql client execution failed: {e}")
        else:
            # Fallback: naive split on semicolons (best-effort). This may fail
            # for procedures/triggers that contain semicolons.
            statements = sql_script.split(';')
            for i, statement in enumerate(statements, 1):
                statement = statement.strip()
                if statement:
                    try:
                        cursor.execute(statement)
                        print(f"   Executed statement {i}")
                    except Error as e:
                        print(f"   Warning in statement {i}: {e}")
        
        connection.commit()
        
        # Verify tables were created
        print("\n4. Verifying table creation...")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Count records in key tables
        print("\n5. Checking sample data...")
        check_tables = ['students', 'teachers', 'fee_types', 'inventory_items']
        for table in check_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  - {table}: {count} records")
            except:
                print(f"  - {table}: Table not found or error")
        
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 60)
        print("Database setup completed successfully!")
        print("=" * 60)
        print(f"\nDatabase: {config.DB_CONFIG['database']}")
        print(f"Host: {config.DB_CONFIG['host']}")
        print(f"User: {config.DB_CONFIG['user']}")
        print("\nYou can now run the application:")
        print("  python main.py")
        print("=" * 60)
        
        return True
        
    except Error as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure MySQL server is running")
        print("2. Check your MySQL credentials in config.py")
        print("3. Ensure you have proper permissions")
        return False

def main():
    """Main function"""
    print("\n" + "=" * 60)
    print(f"  {config.APP_CONFIG['name']}")
    print("  Database Setup Utility")
    print("=" * 60)
    
    print("\nThis script will:")
    print("1. Create the database if it doesn't exist")
    print("2. Create all necessary tables")
    print("3. Insert default data (fee types, classes)")
    print("4. Insert sample data for testing")
    
    response = input("\nDo you want to continue? (y/n): ")
    if response.lower() != 'y':
        print("Setup cancelled.")
        sys.exit(0)
    
    # Ask if user wants sample data
    print("\nSample data includes:")
    print("  - 5 sample students")
    print("  - 4 sample teachers")
    print("  - 8 sample inventory items")
    print("  - Sample fees and attendance records")
    
    sample_response = input("\nInclude sample data? (y/n): ")
    
    # Modify schema.sql based on response
    schema_file = os.path.join('database', 'schema.sql')
    if os.path.exists(schema_file):
        with open(schema_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Remove sample data if not wanted
        if sample_response.lower() != 'y':
            # Find and remove sample data section
            lines = content.split('\n')
            new_lines = []
            in_sample_data = False
            
            for line in lines:
                if '-- Insert Sample Data' in line:
                    in_sample_data = True
                elif not in_sample_data:
                    new_lines.append(line)
                elif in_sample_data and line.strip().startswith('--'):
                    # Keep comments after sample data
                    in_sample_data = False
                    new_lines.append(line)
            
            content = '\n'.join(new_lines)
        
        # Write modified content back
        with open(schema_file, 'w', encoding='utf-8') as file:
            file.write(content)
    
    # Run database creation
    if create_database():
        print("\nSetup completed successfully!")
        
        # Test connection
        print("\nTesting database connection...")
        try:
            import database.connection as db_conn
            if db_conn.db.test_connection():
                print("Database connection test: PASSED ✓")
            else:
                print("Database connection test: FAILED ✗")
        except:
            print("Could not test database connection.")
    else:
        print("\nSetup failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()