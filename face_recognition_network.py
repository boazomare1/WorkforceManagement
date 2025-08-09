"""
Network-Enabled Face Recognition System
=====================================

This version of the face recognition system:
1. Syncs face encodings TO the restaurant database (centralized storage)
2. Loads face encodings FROM the restaurant database (for recognition)
3. Works across multiple POS terminals in the restaurant network
4. Maintains local SQLite for attendance records only

The restaurant database becomes the authoritative source for face data.
"""

import sqlite3
import json
import numpy as np
import face_recognition
import cv2
from datetime import datetime, date, timedelta
import logging
import threading
import time

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkFaceRecognitionSystem:
    """Face recognition system with centralized database support"""
    
    def __init__(self, restaurant_api_base='http://site1.local:8000', local_db_path='attendance.db'):
        """Initialize the network-enabled face recognition system"""
        self.restaurant_api_base = restaurant_api_base
        self.local_db_path = local_db_path
        
        # Face recognition settings
        self.face_recognition_tolerance = 0.6
        self.face_detection_cooldown = 30
        self.minimum_work_hours = 1.0
        self.instant_mode = True
        
        # Thread control
        self.sync_thread_running = False
        self.last_face_sync = None
        
        # Initialize local database for attendance records
        self._init_local_database()
        
        # Load face data from restaurant database
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.known_face_employee_ids = []
        
        # Initial sync
        self.sync_face_data_from_restaurant()
        
        # Start background sync thread
        self.start_background_sync()
    
    def _init_local_database(self):
        """Initialize local SQLite database for attendance records only"""
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Create attendance table (no face encodings here)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    restaurant_staff_id TEXT NOT NULL,
                    employee_id TEXT,
                    staff_name TEXT NOT NULL,
                    check_in_time TIMESTAMP,
                    check_out_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create detection cooldown table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detection_cooldown (
                    restaurant_staff_id TEXT PRIMARY KEY,
                    last_detection TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Local database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize local database: {e}")
    
    def _restaurant_api_call(self, endpoint, method='GET', data=None):
        """Make API call to restaurant system"""
        if not REQUESTS_AVAILABLE:
            logger.error("requests module not available for API calls")
            return {'success': False, 'error': 'requests module not available'}
        
        url = f"{self.restaurant_api_base}/api/method/restaurant_management.api.{endpoint}"
        
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
            logger.error(f"Restaurant API call failed: {endpoint} - {e}")
            return {'success': False, 'error': str(e)}
    
    def register_face_to_restaurant(self, employee_id, full_name, image_path):
        """Register a face encoding to the restaurant database"""
        try:
            # Load and encode the face
            image = face_recognition.load_image_file(image_path)
            face_encodings = face_recognition.face_encodings(image)
            
            if len(face_encodings) == 0:
                return False, "No face detected in the image"
            if len(face_encodings) > 1:
                return False, "Multiple faces detected. Please use an image with only one face"
            
            face_encoding = face_encodings[0]
            
            # Convert encoding to string for storage
            encoding_str = ','.join([str(x) for x in face_encoding])
            
            # Send to restaurant database
            response = self._restaurant_api_call('register_staff_face_encoding', 'POST', {
                'employee_id': employee_id,
                'face_encoding': encoding_str,
                'full_name': full_name
            })
            
            if response.get('success'):
                logger.info(f"Face registered for {full_name} in restaurant database")
                # Refresh local face data
                self.sync_face_data_from_restaurant()
                return True, response.get('message', 'Face registered successfully')
            else:
                return False, response.get('error', 'Failed to register face')
                
        except Exception as e:
            logger.error(f"Error registering face: {e}")
            return False, str(e)
    
    def sync_face_data_from_restaurant(self):
        """Load all face encodings from restaurant database"""
        try:
            logger.info("Syncing face data from restaurant database...")
            
            response = self._restaurant_api_call('get_all_staff_face_encodings')
            
            if not response.get('success'):
                logger.error(f"Failed to sync face data: {response.get('error')}")
                return False
            
            face_data = response.get('face_data', [])
            
            # Clear existing data
            self.known_face_encodings = []
            self.known_face_names = []
            self.known_face_ids = []
            self.known_face_employee_ids = []
            
            # Load face data
            for staff in face_data:
                try:
                    # Convert string encoding back to numpy array
                    encoding_str = staff['face_encoding']
                    encoding_values = [float(x) for x in encoding_str.split(',')]
                    face_encoding = np.array(encoding_values)
                    
                    self.known_face_encodings.append(face_encoding)
                    self.known_face_names.append(staff['name'])
                    self.known_face_ids.append(staff['staff_id'])
                    self.known_face_employee_ids.append(staff['employee_id'])
                    
                except Exception as e:
                    logger.error(f"Error loading face data for {staff.get('name')}: {e}")
            
            self.last_face_sync = datetime.now()
            logger.info(f"Loaded {len(self.known_face_encodings)} face encodings from restaurant database")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing face data: {e}")
            return False
    
    def recognize_face(self, image):
        """Recognize face from image using restaurant database encodings"""
        try:
            # Find face locations and encodings in the image
            face_locations = face_recognition.face_locations(image)
            if not face_locations:
                return None, "No face detected"
            
            face_encodings = face_recognition.face_encodings(image, face_locations)
            if not face_encodings:
                return None, "Could not encode face"
            
            # Compare with known faces from restaurant database
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(
                    self.known_face_encodings, 
                    face_encoding, 
                    tolerance=self.face_recognition_tolerance
                )
                
                if True in matches:
                    match_index = matches.index(True)
                    staff_info = {
                        'staff_id': self.known_face_ids[match_index],
                        'employee_id': self.known_face_employee_ids[match_index],
                        'name': self.known_face_names[match_index]
                    }
                    return staff_info, "Face recognized"
            
            return None, "Face not recognized"
            
        except Exception as e:
            logger.error(f"Error in face recognition: {e}")
            return None, str(e)
    
    def record_attendance(self, staff_info, action='auto'):
        """Record attendance in local database"""
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            staff_id = staff_info['staff_id']
            employee_id = staff_info['employee_id']
            staff_name = staff_info['name']
            
            # Get today's attendance record
            today = date.today().isoformat()
            cursor.execute('''
                SELECT * FROM attendance 
                WHERE restaurant_staff_id = ? AND DATE(check_in_time) = ?
                ORDER BY created_at DESC LIMIT 1
            ''', (staff_id, today))
            
            existing_record = cursor.fetchone()
            
            if existing_record and existing_record[4]:  # Has check_out_time
                # Already completed a full cycle, start new one
                cursor.execute('''
                    INSERT INTO attendance (restaurant_staff_id, employee_id, staff_name, check_in_time)
                    VALUES (?, ?, ?, ?)
                ''', (staff_id, employee_id, staff_name, datetime.now().isoformat()))
                
                message = f"Checked in {staff_name}"
                action_taken = "check_in"
                
            elif existing_record and existing_record[3] and not existing_record[4]:  # Has check_in, no check_out
                # Check minimum work time
                check_in_time = datetime.fromisoformat(existing_record[3])
                work_duration = datetime.now() - check_in_time
                hours_worked = work_duration.total_seconds() / 3600
                
                if hours_worked < self.minimum_work_hours and action != 'force_checkout':
                    return {
                        'success': False,
                        'action': 'checkout_confirmation',
                        'message': f"{staff_name}, you've worked {hours_worked:.1f} hours. Confirm checkout?"
                    }
                
                # Update with check_out_time
                cursor.execute('''
                    UPDATE attendance 
                    SET check_out_time = ? 
                    WHERE id = ?
                ''', (datetime.now().isoformat(), existing_record[0]))
                
                message = f"Checked out {staff_name} ({hours_worked:.1f} hours)"
                action_taken = "check_out"
                
            else:
                # No record today, check in
                cursor.execute('''
                    INSERT INTO attendance (restaurant_staff_id, employee_id, staff_name, check_in_time)
                    VALUES (?, ?, ?, ?)
                ''', (staff_id, employee_id, staff_name, datetime.now().isoformat()))
                
                message = f"Checked in {staff_name}"
                action_taken = "check_in"
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'action': action_taken,
                'message': message,
                'staff_info': staff_info
            }
            
        except Exception as e:
            logger.error(f"Error recording attendance: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def can_detect_user(self, staff_id):
        """Check if user can be detected (cooldown period)"""
        if not self.face_detection_cooldown:
            return True
        
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT last_detection FROM detection_cooldown 
                WHERE restaurant_staff_id = ?
            ''', (staff_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return True
            
            last_detection = datetime.fromisoformat(result[0])
            time_since = (datetime.now() - last_detection).total_seconds()
            
            return time_since >= self.face_detection_cooldown
            
        except Exception as e:
            logger.error(f"Error checking detection cooldown: {e}")
            return True
    
    def update_detection_cooldown(self, staff_id):
        """Update the last detection time for a staff member"""
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO detection_cooldown (restaurant_staff_id, last_detection)
                VALUES (?, ?)
            ''', (staff_id, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating detection cooldown: {e}")
    
    def start_background_sync(self, interval=300):  # 5 minutes
        """Start background thread to sync face data periodically"""
        if self.sync_thread_running:
            return
        
        def sync_worker():
            while self.sync_thread_running:
                try:
                    time.sleep(interval)
                    if self.sync_thread_running:
                        self.sync_face_data_from_restaurant()
                except Exception as e:
                    logger.error(f"Error in background sync: {e}")
        
        self.sync_thread_running = True
        sync_thread = threading.Thread(target=sync_worker, daemon=True)
        sync_thread.start()
        logger.info("Background face data sync started")
    
    def stop_background_sync(self):
        """Stop background sync thread"""
        self.sync_thread_running = False
        logger.info("Background face data sync stopped")
    
    def get_attendance_summary(self, start_date=None, end_date=None):
        """Get attendance summary from local database"""
        try:
            if not start_date:
                start_date = (date.today() - timedelta(days=7)).isoformat()
            if not end_date:
                end_date = date.today().isoformat()
            
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT restaurant_staff_id, employee_id, staff_name,
                       COUNT(*) as total_records,
                       COUNT(check_out_time) as completed_sessions,
                       SUM(
                           CASE WHEN check_out_time IS NOT NULL 
                           THEN (julianday(check_out_time) - julianday(check_in_time)) * 24 
                           ELSE 0 END
                       ) as total_hours
                FROM attendance 
                WHERE DATE(check_in_time) BETWEEN ? AND ?
                GROUP BY restaurant_staff_id, employee_id, staff_name
                ORDER BY staff_name
            ''', (start_date, end_date))
            
            results = cursor.fetchall()
            conn.close()
            
            summary = []
            for row in results:
                summary.append({
                    'staff_id': row[0],
                    'employee_id': row[1],
                    'staff_name': row[2],
                    'total_records': row[3],
                    'completed_sessions': row[4],
                    'total_hours': round(row[5] or 0, 2)
                })
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting attendance summary: {e}")
            return []
    
    def force_refresh_faces(self):
        """Manually refresh face data from restaurant database"""
        return self.sync_face_data_from_restaurant()
    
    def get_system_status(self):
        """Get system status including sync information"""
        return {
            'face_count': len(self.known_face_encodings),
            'last_sync': self.last_face_sync.isoformat() if self.last_face_sync else None,
            'sync_running': self.sync_thread_running,
            'restaurant_api': self.restaurant_api_base,
            'requests_available': REQUESTS_AVAILABLE
        }