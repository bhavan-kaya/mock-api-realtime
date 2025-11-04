import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import os


class PostgresClient:
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.database = os.getenv("DB_NAME", "voice-demo")
        self.user = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "Lahiru1997")
        self.port = os.getenv("DB_PORT", "5432")
        self.conn = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            return self.conn
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def create(self, table: str, data: Dict[str, Any]) -> Optional[int]:
        """Insert a record"""
        cols = ', '.join(data.keys())
        vals = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({cols}) VALUES ({vals}) RETURNING id"
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, list(data.values()))
                self.conn.commit()
                return cur.fetchone()[0]
        except Exception as e:
            self.conn.rollback()
            print(f"Error creating record: {e}")
            return None
    
    def read(self, table: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Read records with optional filters"""
        query = f"SELECT * FROM {table}"
        params = []
        
        if filters:
            conditions = ' AND '.join([f"{k} = %s" for k in filters.keys()])
            query += f" WHERE {conditions}"
            params = list(filters.values())
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error reading records: {e}")
            return []
    
    def update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Update records"""
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        where_clause = ' AND '.join([f"{k} = %s" for k in filters.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, list(data.values()) + list(filters.values()))
                self.conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"Error updating record: {e}")
            return False
    
    def delete(self, table: str, filters: Dict[str, Any]) -> bool:
        """Delete records"""
        where_clause = ' AND '.join([f"{k} = %s" for k in filters.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, list(filters.values()))
                self.conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting record: {e}")
            return False