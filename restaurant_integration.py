"""
Restaurant Management - Face Recognition Integration
==================================================

SIMPLIFIED INTEGRATION APPROACH:
- Face Recognition System: Handles ONLY basic check-in/check-out tracking
- Restaurant Management System: Handles ALL business logic (payroll, tips, scheduling, etc.)

This module provides a lightweight bridge that:
1. Maps restaurant staff to face recognition users
2. Sends basic attendance data (who checked in/out when)
3. Let's restaurant system handle all complex calculations

The restaurant system is the "smart" part - this just provides raw attendance data.
"""

import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import logging

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    # Create a mock requests module for basic functionality
    class MockRequests:
        class exceptions:
            class RequestException(Exception):
                pass
            class ConnectionError(RequestException):
                pass
        
        def get(self, url, **kwargs):
            raise self.exceptions.ConnectionError("requests module not available")
        
        def post(self, url, **kwargs):
            raise self.exceptions.ConnectionError("requests module not available")
    
    requests = MockRequests()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RestaurantFaceIntegration:
    """Integrates face recognition attendance with restaurant management system"""
    
    def __init__(self, 
                 sqlite_db_path: str = 'attendance.db',
                 frappe_base_url: str = 'http://site1.local:8000',
                 sync_interval: int = 300):  # 5 minutes
        """
        Initialize the integration system
        
        Args:
            sqlite_db_path: Path to SQLite attendance database
            frappe_base_url: Base URL for Frappe restaurant system
            sync_interval: Sync interval in seconds
        """
        self.sqlite_db_path = sqlite_db_path
        self.frappe_base_url = frappe_base_url
        self.sync_interval = sync_interval
        
        # Initialize connections
        self._init_sqlite_connection()
        self._setup_integration_tables()
        
    def _init_sqlite_connection(self):
        """Initialize SQLite database connection"""
        try:
            self.conn = sqlite3.connect(self.sqlite_db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info("SQLite connection established")
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            raise
    
    def _setup_integration_tables(self):
        """Create integration tables in SQLite if they don't exist"""
        cursor = self.conn.cursor()
        
        # Staff mapping table - links face recognition users with restaurant staff
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS staff_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                face_user_id INTEGER NOT NULL,
                restaurant_staff_id TEXT NOT NULL,
                employee_id TEXT,
                position TEXT,
                department TEXT,
                hourly_rate REAL DEFAULT 0.0,
                sync_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (face_user_id) REFERENCES users(id),
                UNIQUE(face_user_id),
                UNIQUE(restaurant_staff_id)
            )
        ''')
        
        # Shift assignments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shift_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_mapping_id INTEGER NOT NULL,
                shift_date DATE NOT NULL,
                shift_start TIME,
                shift_end TIME,
                shift_type TEXT DEFAULT 'regular',
                expected_hours REAL DEFAULT 8.0,
                status TEXT DEFAULT 'scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (staff_mapping_id) REFERENCES staff_mapping(id)
            )
        ''')
        
        # Attendance summary table - basic attendance data for restaurant system
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_mapping_id INTEGER NOT NULL,
                work_date DATE NOT NULL,
                actual_check_in TIMESTAMP,
                actual_check_out TIMESTAMP,
                total_hours REAL DEFAULT 0.0,
                status TEXT DEFAULT 'present',
                sync_status TEXT DEFAULT 'pending',
                frappe_attendance_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (staff_mapping_id) REFERENCES staff_mapping(id),
                UNIQUE(staff_mapping_id, work_date)
            )
        ''')
        
        # Integration logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS integration_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                operation_data TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        logger.info("Integration tables initialized")
    
    def _frappe_api_call(self, endpoint: str, method: str = 'GET', data: dict = None) -> dict:
        """Make API call to Frappe restaurant system"""
        url = f"{self.frappe_base_url}/api/method/restaurant_management.api.{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, params=data, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Frappe API call failed: {endpoint} - {e}")
            return {'success': False, 'error': str(e)}
    
    def sync_staff_from_restaurant(self) -> Dict:
        """Sync restaurant staff data to face recognition system"""
        try:
            # Get all restaurant staff
            response = self._frappe_api_call('get_restaurant_staff')
            
            if not response.get('success'):
                return {'success': False, 'error': 'Failed to fetch restaurant staff'}
            
            staff_list = response.get('data', [])
            synced_count = 0
            errors = []
            
            cursor = self.conn.cursor()
            
            for staff in staff_list:
                try:
                    staff_id = staff.get('name')
                    full_name = staff.get('full_name')
                    employee_id = staff.get('employee_id')
                    position = staff.get('position')
                    department = staff.get('department')
                    hourly_rate = staff.get('hourly_rate', 0.0)
                    
                    # Check if staff already exists in face system
                    cursor.execute('''
                        SELECT id FROM users WHERE name = ? COLLATE NOCASE
                    ''', (full_name,))
                    
                    face_user = cursor.fetchone()
                    
                    if face_user:
                        face_user_id = face_user['id']
                        
                        # Create or update staff mapping
                        cursor.execute('''
                            INSERT OR REPLACE INTO staff_mapping 
                            (face_user_id, restaurant_staff_id, employee_id, position, department, hourly_rate, sync_status, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, 'synced', CURRENT_TIMESTAMP)
                        ''', (face_user_id, staff_id, employee_id, position, department, hourly_rate))
                        
                        synced_count += 1
                        logger.info(f"Synced staff: {full_name} ({employee_id})")
                    else:
                        logger.warning(f"Face recognition user not found for staff: {full_name}")
                        errors.append(f"Face user not found: {full_name}")
                        
                except Exception as e:
                    error_msg = f"Error syncing staff {staff.get('full_name', 'Unknown')}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            self.conn.commit()
            
            # Log the operation
            self._log_integration_operation(
                'sync_staff_from_restaurant',
                {'synced_count': synced_count, 'total_staff': len(staff_list)},
                'success' if synced_count > 0 else 'partial',
                errors[0] if errors else None
            )
            
            return {
                'success': True,
                'synced_count': synced_count,
                'total_staff': len(staff_list),
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Staff sync failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_daily_attendance(self, target_date: date = None) -> Dict:
        """Process attendance data for a specific date and prepare for restaurant system"""
        if target_date is None:
            target_date = date.today()
        
        try:
            cursor = self.conn.cursor()
            
            # Get all attendance records for the date (simplified - just basic check-in/out)
            cursor.execute('''
                SELECT a.*, sm.id as mapping_id, sm.restaurant_staff_id, sm.employee_id, 
                       u.name as user_name
                FROM attendance a
                JOIN users u ON a.user_id = u.id
                JOIN staff_mapping sm ON u.id = sm.face_user_id
                WHERE DATE(a.check_in_time) = ?
                ORDER BY a.user_id, a.check_in_time
            ''', (target_date.isoformat(),))
            
            attendance_records = cursor.fetchall()
            processed_count = 0
            
            # Group by staff member
            staff_attendance = {}
            for record in attendance_records:
                mapping_id = record['mapping_id']
                if mapping_id not in staff_attendance:
                    staff_attendance[mapping_id] = {
                        'mapping_id': mapping_id,
                        'restaurant_staff_id': record['restaurant_staff_id'],
                        'employee_id': record['employee_id'],
                        'user_name': record['user_name'],
                        'position': record['position'],
                        'hourly_rate': record['hourly_rate'],
                        'records': []
                    }
                staff_attendance[mapping_id]['records'].append(record)
            
            # Process each staff member's attendance
            for mapping_id, staff_data in staff_attendance.items():
                records = staff_data['records']
                
                # Find check-in and check-out times
                check_in_time = None
                check_out_time = None
                
                for record in records:
                    if record['check_in_time'] and not check_in_time:
                        check_in_time = datetime.fromisoformat(record['check_in_time'])
                    if record['check_out_time']:
                        check_out_time = datetime.fromisoformat(record['check_out_time'])
                
                # Just basic time calculation - restaurant system handles the business logic
                total_hours = 0.0
                
                if check_in_time and check_out_time:
                    work_duration = check_out_time - check_in_time
                    total_hours = work_duration.total_seconds() / 3600
                
                # Insert or update attendance summary (minimal data for restaurant system)
                cursor.execute('''
                    INSERT OR REPLACE INTO attendance_summary 
                    (staff_mapping_id, work_date, actual_check_in, actual_check_out, 
                     total_hours, status, sync_status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                ''', (
                    mapping_id, target_date.isoformat(),
                    check_in_time.isoformat() if check_in_time else None,
                    check_out_time.isoformat() if check_out_time else None,
                    total_hours,
                    'present' if check_in_time else 'absent'
                ))
                
                processed_count += 1
                logger.info(f"Processed attendance for {staff_data['user_name']}: {total_hours:.2f} hours")
            
            self.conn.commit()
            
            return {
                'success': True,
                'processed_count': processed_count,
                'date': target_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Daily attendance processing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def sync_attendance_to_restaurant(self, target_date: date = None) -> Dict:
        """Sync processed attendance data to restaurant management system"""
        if target_date is None:
            target_date = date.today()
        
        try:
            cursor = self.conn.cursor()
            
            # Get pending attendance summaries for the date
            cursor.execute('''
                SELECT ats.*, sm.restaurant_staff_id, sm.employee_id
                FROM attendance_summary ats
                JOIN staff_mapping sm ON ats.staff_mapping_id = sm.id
                WHERE ats.work_date = ? AND ats.sync_status = 'pending'
            ''', (target_date.isoformat(),))
            
            pending_records = cursor.fetchall()
            synced_count = 0
            errors = []
            
            for record in pending_records:
                try:
                    # Prepare simple attendance data for restaurant system
                    attendance_data = {
                        'staff_id': record['restaurant_staff_id'],
                        'employee_id': record['employee_id'],
                        'attendance_date': record['work_date'],
                        'check_in_time': record['actual_check_in'],
                        'check_out_time': record['actual_check_out'],
                        'total_hours': record['total_hours'],
                        'status': record['status'],
                        'source': 'face_recognition'
                    }
                    
                    # Send to restaurant system
                    response = self._frappe_api_call('record_staff_attendance', 'POST', attendance_data)
                    
                    if response.get('success'):
                        # Update sync status
                        cursor.execute('''
                            UPDATE attendance_summary 
                            SET sync_status = 'synced', frappe_attendance_id = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (response.get('attendance_id'), record['id']))
                        
                        synced_count += 1
                        logger.info(f"Synced attendance for staff {record['employee_id']}")
                    else:
                        error_msg = response.get('error', 'Unknown error')
                        errors.append(f"Staff {record['employee_id']}: {error_msg}")
                        logger.error(f"Failed to sync attendance for {record['employee_id']}: {error_msg}")
                        
                except Exception as e:
                    error_msg = f"Error syncing attendance for {record.get('employee_id', 'Unknown')}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            self.conn.commit()
            
            return {
                'success': True,
                'synced_count': synced_count,
                'total_pending': len(pending_records),
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Attendance sync failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_staff_work_summary(self, staff_id: str = None, start_date: date = None, end_date: date = None) -> Dict:
        """Get work summary for staff members"""
        if start_date is None:
            start_date = date.today() - timedelta(days=7)
        if end_date is None:
            end_date = date.today()
        
        try:
            cursor = self.conn.cursor()
            
            query = '''
                SELECT sm.employee_id, sm.restaurant_staff_id, u.name as staff_name,
                       sm.position,
                       COUNT(ats.id) as days_worked,
                       SUM(ats.total_hours) as total_hours,
                       SUM(CASE WHEN ats.status = 'present' THEN 1 ELSE 0 END) as present_days,
                       SUM(CASE WHEN ats.status = 'absent' THEN 1 ELSE 0 END) as absent_days
                FROM staff_mapping sm
                JOIN users u ON sm.face_user_id = u.id
                LEFT JOIN attendance_summary ats ON sm.id = ats.staff_mapping_id 
                    AND ats.work_date BETWEEN ? AND ?
            '''
            
            params = [start_date.isoformat(), end_date.isoformat()]
            
            if staff_id:
                query += ' WHERE sm.restaurant_staff_id = ?'
                params.append(staff_id)
            
            query += ' GROUP BY sm.id ORDER BY sm.employee_id'
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            summary_data = []
            for row in results:
                # Basic summary only - restaurant system handles pay calculations
                summary_data.append({
                    'employee_id': row['employee_id'],
                    'staff_name': row['staff_name'],
                    'position': row['position'],
                    'days_worked': row['days_worked'] or 0,
                    'total_hours': round(row['total_hours'] or 0, 2),
                    'present_days': row['present_days'] or 0,
                    'absent_days': row['absent_days'] or 0,
                    'attendance_rate': round((row['present_days'] or 0) / max(row['days_worked'] or 1, 1) * 100, 1)
                })
            
            return {
                'success': True,
                'summary': summary_data,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Work summary generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _log_integration_operation(self, operation_type: str, operation_data: dict, status: str, error_message: str = None):
        """Log integration operations for debugging and monitoring"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO integration_logs (operation_type, operation_data, status, error_message)
                VALUES (?, ?, ?, ?)
            ''', (operation_type, json.dumps(operation_data), status, error_message))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to log integration operation: {e}")
    
    def get_integration_status(self) -> Dict:
        """Get overall integration status and health check"""
        try:
            cursor = self.conn.cursor()
            
            # Count mapped staff
            cursor.execute('SELECT COUNT(*) as count FROM staff_mapping WHERE sync_status = "synced"')
            mapped_staff_count = cursor.fetchone()['count']
            
            # Count pending attendance records
            cursor.execute('SELECT COUNT(*) as count FROM attendance_summary WHERE sync_status = "pending"')
            pending_attendance_count = cursor.fetchone()['count']
            
            # Recent sync operations
            cursor.execute('''
                SELECT operation_type, status, created_at
                FROM integration_logs
                ORDER BY created_at DESC
                LIMIT 10
            ''')
            recent_operations = cursor.fetchall()
            
            # Check Frappe connectivity
            frappe_status = 'offline'
            try:
                response = self._frappe_api_call('get_positions')
                if response.get('success'):
                    frappe_status = 'online'
            except:
                pass
            
            return {
                'success': True,
                'status': {
                    'mapped_staff_count': mapped_staff_count,
                    'pending_attendance_count': pending_attendance_count,
                    'frappe_system_status': frappe_status,
                    'sqlite_status': 'connected',
                    'last_sync': datetime.now().isoformat()
                },
                'recent_operations': [dict(row) for row in recent_operations]
            }
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def close(self):
        """Close database connections"""
        if hasattr(self, 'conn'):
            self.conn.close()
            logger.info("Database connections closed")


# Convenience functions for easy integration
def quick_sync_staff():
    """Quick function to sync staff from restaurant to face system"""
    integration = RestaurantFaceIntegration()
    try:
        result = integration.sync_staff_from_restaurant()
        return result
    finally:
        integration.close()

def quick_process_attendance(target_date: date = None):
    """Quick function to process today's attendance"""
    integration = RestaurantFaceIntegration()
    try:
        # Process attendance
        process_result = integration.process_daily_attendance(target_date)
        if process_result['success']:
            # Sync to restaurant system
            sync_result = integration.sync_attendance_to_restaurant(target_date)
            return {
                'success': True,
                'process_result': process_result,
                'sync_result': sync_result
            }
        return process_result
    finally:
        integration.close()

def get_integration_dashboard():
    """Get integration dashboard data"""
    integration = RestaurantFaceIntegration()
    try:
        return integration.get_integration_status()
    finally:
        integration.close()