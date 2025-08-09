import cv2
import face_recognition
import numpy as np
import os
import threading
from datetime import datetime, timedelta
from database import AttendanceDatabase

class FaceRecognitionSystemImproved:
    def __init__(self):
        self.db = AttendanceDatabase()
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.attendance_running = False
        self.attendance_thread = None
        self.video_capture = None
        
        # Enhanced settings for better control
        self.minimum_work_hours = 1.0  # Minimum hours before checkout is allowed
        self.face_detection_cooldown = 30  # Seconds between face detections for same person
        self.last_detection_times = {}  # Track last detection time for each user
        self.pending_checkouts = {}  # Track users pending checkout confirmation
        self.instant_mode = True  # If True, automatically check in/out like original system
        
        self.load_known_faces()
        
    def load_known_faces(self):
        """Load all known faces from the database"""
        encodings, user_ids, names = self.db.get_user_encodings()
        self.known_face_encodings = encodings
        self.known_face_ids = user_ids
        self.known_face_names = names
        print(f"Loaded {len(self.known_face_names)} known faces")
    
    def add_new_face(self, name, image_path):
        """Add a new face to the system"""
        # Check for duplicate names first
        existing_users = self.db.get_all_users()
        for user in existing_users:
            if user[1].lower().strip() == name.lower().strip():
                return False, f"User '{name}' already exists in the system"
        
        # Load the image
        image = face_recognition.load_image_file(image_path)
        face_encodings = face_recognition.face_encodings(image)
        
        if len(face_encodings) == 0:
            return False, "No face detected in the image"
        
        if len(face_encodings) > 1:
            return False, "Multiple faces detected. Please use an image with only one face"
        
        # Get the first face encoding
        face_encoding = face_encodings[0]
        
        # Add to database
        user_id = self.db.add_user(name, face_encoding)
        
        # Update local lists
        self.known_face_encodings.append(face_encoding)
        self.known_face_names.append(name)
        self.known_face_ids.append(user_id)
        
        return True, f"User '{name}' added successfully"
    
    def update_face_encoding(self, user_id, name, image_path):
        """Update face encoding for existing user"""
        try:
            # Load the image
            image = face_recognition.load_image_file(image_path)
            face_encodings = face_recognition.face_encodings(image)
            
            if len(face_encodings) == 0:
                return False, "No face detected in the image"
            
            if len(face_encodings) > 1:
                return False, "Multiple faces detected. Please use an image with only one face"
            
            # Get the first face encoding
            face_encoding = face_encodings[0]
            
            # Update in database
            success = self.db.update_user_face_encoding(user_id, face_encoding)
            
            if success:
                # Reload known faces to update the system
                self.load_known_faces()
                return True, f"Face encoding updated successfully for '{name}'"
            else:
                return False, "Failed to update face encoding in database"
                
        except Exception as e:
            return False, f"Error updating face encoding: {str(e)}"
    
    def recognize_faces(self, frame):
        """Recognize faces in a frame"""
        try:
            # Resize frame for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Find face locations and encodings
            face_locations = face_recognition.face_locations(rgb_small_frame)
            
            try:
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            except Exception as e:
                print(f"Error in face encoding: {e}")
                face_encodings = [None] * len(face_locations)
            
            face_names = []
            face_ids = []
            
            for face_encoding in face_encodings:
                if face_encoding is not None and len(self.known_face_encodings) > 0:
                    try:
                        # Compare with known faces
                        matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
                        name = "Unknown"
                        user_id = None
                        
                        if True in matches:
                            first_match_index = matches.index(True)
                            name = self.known_face_names[first_match_index]
                            user_id = self.known_face_ids[first_match_index]
                        
                        face_names.append(name)
                        face_ids.append(user_id)
                    except Exception as e:
                        print(f"Error comparing faces: {e}")
                        face_names.append("Unknown")
                        face_ids.append(None)
                else:
                    face_names.append("Unknown")
                    face_ids.append(None)
            
            return face_locations, face_names, face_ids
            
        except Exception as e:
            print(f"Error in face recognition: {e}")
            return [], [], []
    
    def can_detect_user(self, user_id):
        """Check if enough time has passed since last detection for this user"""
        if user_id not in self.last_detection_times:
            return True
        
        time_since_last = (datetime.now() - self.last_detection_times[user_id]).total_seconds()
        return time_since_last >= self.face_detection_cooldown
    
    def can_checkout_user(self, user_id, user_name):
        """Check if user has worked minimum hours before allowing checkout"""
        today = datetime.now().date()
        records = self.db.get_attendance_records(today)
        
        for record in records:
            if record[1] == user_name and record[2] and not record[3]:  # Has check-in but no check-out
                check_in_time = datetime.fromisoformat(record[2])
                hours_worked = (datetime.now() - check_in_time).total_seconds() / 3600
                
                if hours_worked >= self.minimum_work_hours:
                    return True, hours_worked
                else:
                    remaining_minutes = int((self.minimum_work_hours - hours_worked) * 60)
                    return False, f"Minimum work time not reached. Please work {remaining_minutes} more minutes."
        
        return False, "No active check-in found"
    
    def process_attendance_frame_improved(self, image_path, force_action=None, confirm_checkout=False):
        """
        Improved attendance processing with better controls
        
        Args:
            image_path: Path to the image file
            force_action: 'check_in' or 'check_out' to force specific action
            confirm_checkout: True if user confirmed they want to checkout
        """
        try:
            # Load the image
            image = face_recognition.load_image_file(image_path)
            face_encodings = face_recognition.face_encodings(image)
            
            print(f"Found {len(face_encodings)} faces in frame")
            
            if len(face_encodings) == 0:
                return False, None, None, "No face detected in image"
            
            # Get the first face encoding
            face_encoding = face_encodings[0]
            
            # Compare with known faces
            if len(self.known_face_encodings) > 0:
                print(f"Comparing with {len(self.known_face_encodings)} known faces")
                
                # Try different tolerance levels
                tolerances = [0.6, 0.5, 0.4]
                for tolerance in tolerances:
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=tolerance)
                    
                    if True in matches:
                        first_match_index = matches.index(True)
                        user_name = self.known_face_names[first_match_index]
                        user_id = self.known_face_ids[first_match_index]
                        
                        print(f"Face recognized as {user_name} with tolerance {tolerance}")
                        
                        # Check cooldown period (skip in instant mode)
                        if not self.instant_mode and not self.can_detect_user(user_id) and not force_action:
                            return False, None, None, f"Please wait before next detection for {user_name}"
                        
                        # Update last detection time
                        self.last_detection_times[user_id] = datetime.now()
                        
                        # Check current attendance status
                        today = datetime.now().date()
                        records = self.db.get_attendance_records(today)
                        
                        user_record = None
                        for record in records:
                            if record[1] == user_name:  # record[1] is the user name
                                user_record = record
                                break
                        
                        if force_action == 'check_in':
                            # Force check-in
                            if user_record and user_record[2] and not user_record[3]:
                                return False, user_name, None, f"{user_name} is already checked in"
                            
                            self.db.mark_attendance(user_id, check_in=True)
                            print(f"Forced check-in for {user_name}")
                            return True, user_name, 'check_in', f"Checked in {user_name}"
                        
                        elif force_action == 'check_out':
                            # Force check-out with confirmation
                            if not user_record or not user_record[2] or user_record[3]:
                                return False, user_name, None, f"{user_name} is not currently checked in"
                            
                            if confirm_checkout:
                                # Check minimum work time
                                can_checkout, message = self.can_checkout_user(user_id, user_name)
                                if not can_checkout:
                                    return False, user_name, None, str(message)
                                
                                self.db.mark_attendance(user_id, check_in=False)
                                print(f"Confirmed check-out for {user_name}")
                                hours_worked = message  # message contains hours worked
                                return True, user_name, 'check_out', f"Checked out {user_name}. Worked: {hours_worked:.1f} hours"
                            else:
                                # Require confirmation for checkout
                                can_checkout, message = self.can_checkout_user(user_id, user_name)
                                if not can_checkout:
                                    return False, user_name, 'checkout_blocked', str(message)
                                
                                # Store pending checkout
                                self.pending_checkouts[user_id] = datetime.now()
                                hours_worked = message
                                return False, user_name, 'checkout_confirmation', f"Confirm checkout for {user_name}? Worked: {hours_worked:.1f} hours"
                        
                        else:
                            # Automatic detection (default behavior)
                            if self.instant_mode:
                                # Instant check-in, but controlled checkout
                                if user_record:
                                    if user_record[2] and not user_record[3]:  # Has check-in but no check-out
                                        # User is checked in, check minimum work time for checkout
                                        can_checkout, message = self.can_checkout_user(user_id, user_name)
                                        if not can_checkout:
                                            return False, user_name, 'checkout_blocked', str(message)
                                        
                                        # Require confirmation for checkout with work time info
                                        hours_worked = message
                                        return False, user_name, 'checkout_confirmation', f"{user_name} detected! You've worked {hours_worked:.1f} hours. Confirm checkout?"
                                    else:
                                        # Already checked out, check in for new session
                                        self.db.mark_attendance(user_id, check_in=True)
                                        print(f"Auto checked in {user_name}")
                                        return True, user_name, 'check_in', f"Checked in {user_name}"
                                else:
                                    # No record today, check in
                                    self.db.mark_attendance(user_id, check_in=True)
                                    print(f"Auto checked in {user_name}")
                                    return True, user_name, 'check_in', f"Checked in {user_name}"
                            else:
                                # Improved behavior with confirmations
                                if user_record:
                                    if user_record[2] and not user_record[3]:  # Has check-in but no check-out
                                        # User is checked in, suggest checkout with confirmation
                                        can_checkout, message = self.can_checkout_user(user_id, user_name)
                                        if not can_checkout:
                                            return False, user_name, 'checkout_blocked', str(message)
                                        
                                        hours_worked = message
                                        return False, user_name, 'checkout_suggestion', f"{user_name} detected. Checkout? Worked: {hours_worked:.1f} hours"
                                    else:
                                        # Already checked out, suggest new check-in
                                        return False, user_name, 'checkin_suggestion', f"{user_name} detected. Check in for new session?"
                                else:
                                    # No record today, suggest check-in
                                    return False, user_name, 'checkin_suggestion', f"{user_name} detected. Check in?"
                
                print("No face matches found with any tolerance level")
            else:
                print("No known faces loaded")
            
            return False, None, None, "No recognized face found"
            
        except Exception as e:
            print(f"Error processing attendance frame: {e}")
            return False, None, None, f"Error: {str(e)}"
    
    def get_pending_checkout_users(self):
        """Get users with pending checkout confirmations"""
        # Clean up old pending checkouts (older than 5 minutes)
        current_time = datetime.now()
        expired_checkouts = []
        
        for user_id, pending_time in self.pending_checkouts.items():
            if (current_time - pending_time).total_seconds() > 300:  # 5 minutes
                expired_checkouts.append(user_id)
        
        for user_id in expired_checkouts:
            del self.pending_checkouts[user_id]
        
        return list(self.pending_checkouts.keys())
    
    def clear_pending_checkout(self, user_id):
        """Clear pending checkout for user"""
        if user_id in self.pending_checkouts:
            del self.pending_checkouts[user_id]
    
    def run_attendance_system(self):
        """Run the real-time attendance system"""
        self.video_capture = cv2.VideoCapture(0)
        
        if not self.video_capture.isOpened():
            print("Error: Could not open video capture")
            return
        
        print("Attendance system running. Press 'q' to quit, 'r' to reload faces.")
        print("Face detection will suggest actions. Use web interface for confirmations.")
        
        while True:
            ret, frame = self.video_capture.read()
            
            if not ret:
                print("Failed to grab frame")
                break
            
            # Process frame for attendance (just detection, no automatic action)
            face_locations, face_names, face_ids = self.recognize_faces(frame)
            
            # Scale back up face locations
            face_locations = [(top * 4, right * 4, bottom * 4, left * 4) for top, right, bottom, left in face_locations]
            
            # Draw rectangles and names
            for (top, right, bottom, left), name, user_id in zip(face_locations, face_names, face_ids):
                if name != "Unknown":
                    color = (0, 255, 0)  # Green for known faces
                    
                    # Check if user can be detected (cooldown)
                    if user_id and self.can_detect_user(user_id):
                        # Check status and show suggestion
                        today = datetime.now().date()
                        records = self.db.get_attendance_records(today)
                        
                        user_record = None
                        for record in records:
                            if record[1] == name:
                                user_record = record
                                break
                        
                        if user_record and user_record[2] and not user_record[3]:
                            status_text = "CHECKED IN"
                            color = (0, 165, 255)  # Orange
                        elif user_record and user_record[3]:
                            status_text = "CHECKED OUT"
                            color = (128, 128, 128)  # Gray
                        else:
                            status_text = "NOT CHECKED IN"
                            color = (0, 0, 255)  # Red
                    else:
                        status_text = "COOLDOWN"
                        color = (255, 255, 0)  # Yellow
                else:
                    color = (0, 0, 255)  # Red for unknown faces
                    status_text = "UNKNOWN"
                
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                
                # Draw name and status
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, f"{name}", (left + 6, bottom - 20), font, 0.5, (255, 255, 255), 1)
                cv2.putText(frame, status_text, (left + 6, bottom - 6), font, 0.4, (255, 255, 255), 1)
            
            cv2.imshow('Attendance System', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.load_known_faces()
                print("Reloaded known faces")
        
        self.video_capture.release()
        cv2.destroyAllWindows()