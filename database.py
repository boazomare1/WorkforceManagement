import sqlite3
import os
import numpy as np
from datetime import datetime

class AttendanceDatabase:
    def __init__(self, db_path="attendance.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                face_encoding TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create attendance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                check_in TIMESTAMP,
                check_out TIMESTAMP,
                date DATE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Migrate existing database if needed
        self.migrate_database(cursor)
        
        conn.commit()
        conn.close()
    
    def migrate_database(self, cursor):
        """Migrate existing database schema if needed"""
        try:
            # Check if face_encoding column has NOT NULL constraint
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            
            for column in columns:
                if column[1] == 'face_encoding' and column[3] == 1:  # NOT NULL constraint
                    # Create new table with NULL allowed
                    cursor.execute('''
                        CREATE TABLE users_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            face_encoding TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    # Copy data from old table
                    cursor.execute('''
                        INSERT INTO users_new (id, name, face_encoding, created_at)
                        SELECT id, name, face_encoding, created_at FROM users
                    ''')
                    
                    # Drop old table and rename new one
                    cursor.execute('DROP TABLE users')
                    cursor.execute('ALTER TABLE users_new RENAME TO users')
                    break
        except Exception as e:
            print(f"Migration error (this is normal for new databases): {e}")
    
    def add_user(self, name, face_encoding):
        """Add a new user to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Handle None face encoding
        if face_encoding is None:
            encoding_str = None
        else:
            # Convert numpy array to string for storage
            encoding_str = ','.join(map(str, face_encoding))
        
        cursor.execute('''
            INSERT INTO users (name, face_encoding)
            VALUES (?, ?)
        ''', (name, encoding_str))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    
    def get_all_users(self):
        """Get all users from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, face_encoding FROM users')
        users = cursor.fetchall()
        
        conn.close()
        return users
    
    def get_user_encodings(self):
        """Get all user face encodings"""
        users = self.get_all_users()
        encodings = []
        user_ids = []
        names = []
        
        for user in users:
            user_id, name, encoding_str = user
            # Handle None encoding
            if encoding_str is None:
                continue  # Skip users without face encodings
            # Convert string back to numpy array
            encoding = np.array([float(x) for x in encoding_str.split(',')])
            encodings.append(encoding)
            user_ids.append(user_id)
            names.append(name)
        
        return encodings, user_ids, names
    
    def mark_attendance(self, user_id, check_in=True):
        """Mark attendance for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().date()
        current_time = datetime.now()
        
        if check_in:
            # Check if user already has attendance for today
            cursor.execute('''
                SELECT id FROM attendance 
                WHERE user_id = ? AND date = ?
            ''', (user_id, today))
            
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO attendance (user_id, check_in, date)
                    VALUES (?, ?, ?)
                ''', (user_id, current_time, today))
        else:
            # Mark check out
            cursor.execute('''
                UPDATE attendance 
                SET check_out = ?
                WHERE user_id = ? AND date = ? AND check_out IS NULL
            ''', (current_time, user_id, today))
        
        conn.commit()
        conn.close()
    
    def get_attendance_records(self, date=None):
        """Get attendance records for a specific date or all records"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if date:
            cursor.execute('''
                SELECT a.id, u.name, a.check_in, a.check_out, a.date
                FROM attendance a
                JOIN users u ON a.user_id = u.id
                WHERE a.date = ?
                ORDER BY a.check_in
            ''', (date,))
        else:
            cursor.execute('''
                SELECT a.id, u.name, a.check_in, a.check_out, a.date
                FROM attendance a
                JOIN users u ON a.user_id = u.id
                ORDER BY a.date DESC, a.check_in DESC
            ''')
        
        records = cursor.fetchall()
        conn.close()
        return records
    
    def delete_user(self, user_id):
        """Delete a user and their attendance records"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM attendance WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        conn.commit()
        conn.close() 