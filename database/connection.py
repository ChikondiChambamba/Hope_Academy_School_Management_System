"""
Database connection manager
"""
import mysql.connector
from mysql.connector import Error, pooling
import config
from typing import Optional, Tuple, List, Dict, Any

class DatabaseConnection:
    _instance = None
    _connection_pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance
    
    def _initialize_pool(self):
        """Initialize database connection pool"""
        try:
            self._connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="school_pool",
                pool_size=5,
                **config.DB_CONFIG
            )
            print("Database connection pool created successfully")
        except Error as e:
            print(f"Error creating connection pool: {e}")
            raise
    
    def get_connection(self):
        """Get a connection from the pool"""
        try:
            if self._connection_pool:
                return self._connection_pool.get_connection()
            else:
                return mysql.connector.connect(**config.DB_CONFIG)
        except Error as e:
            print(f"Error getting connection: {e}")
            raise
    
    def execute_query(self, query: str, params: Tuple = None, 
                     fetch: bool = False) -> Optional[List[Dict]]:
        """Execute a SQL query"""
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
                return result
            else:
                connection.commit()
                return cursor.lastrowid
                
        except Error as e:
            if connection:
                connection.rollback()
            print(f"Error executing query: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> None:
        """Execute multiple insert/update operations"""
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            cursor.executemany(query, params_list)
            connection.commit()
            
        except Error as e:
            if connection:
                connection.rollback()
            print(f"Error executing multiple queries: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def close_all(self):
        """Close all connections in pool"""
        if self._connection_pool:
            self._connection_pool.closeall()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = self.get_connection()
            conn.close()
            return True
        except Error:
            return False

# Singleton instance
db = DatabaseConnection()