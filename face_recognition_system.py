import cv2
import face_recognition
import numpy as np
import os
import threading
from datetime import datetime
from database import AttendanceDatabase

class FaceRecognitionSystem:
    def __init__(self):
        self.db = AttendanceDatabase()
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.attendance_running = False
        self.attendance_thread = None
        self.video_capture = None
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
        
        return True, f"Successfully added {name} to the system"
    
    def recognize_faces(self, frame):
        """Recognize faces in a frame and return results"""
        try:
            # Resize frame for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = small_frame[:, :, ::-1]
            
            # Find faces in the frame
            face_locations = face_recognition.face_locations(rgb_small_frame)
            
            # Handle face encodings with error handling
            face_encodings = []
            try:
                # Use a more compatible approach - encode each face individually
                for face_location in face_locations:
                    try:
                        top, right, bottom, left = face_location
                        # Extract face image
                        face_image = rgb_small_frame[top:bottom, left:right]
                        if face_image.size > 0:
                            # Encode the face image
                            encoding = face_recognition.face_encodings(face_image)
                            if encoding:
                                face_encodings.append(encoding[0])
                            else:
                                face_encodings.append(None)
                        else:
                            face_encodings.append(None)
                    except Exception as e:
                        print(f"Error encoding individual face: {e}")
                        face_encodings.append(None)
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
    
    def mark_attendance_for_frame(self, frame):
        """Process a frame and mark attendance for recognized faces"""
        try:
            face_locations, face_names, face_ids = self.recognize_faces(frame)
            
            # Scale back up face locations
            face_locations = [(top * 4, right * 4, bottom * 4, left * 4) for top, right, bottom, left in face_locations]
            
            attendance_marked = []
            
            for (top, right, bottom, left), name, user_id in zip(face_locations, face_names, face_ids):
                # Draw rectangle around face
                if name != "Unknown":
                    color = (0, 255, 0)  # Green for known faces
                    # Mark attendance
                    if user_id:
                        try:
                            self.db.mark_attendance(user_id, check_in=True)
                            attendance_marked.append(name)
                        except Exception as e:
                            print(f"Error marking attendance for {name}: {e}")
                else:
                    color = (0, 0, 255)  # Red for unknown faces
                
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                
                # Draw name label
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)
            
            return frame, attendance_marked
            
        except Exception as e:
            print(f"Error in mark_attendance_for_frame: {e}")
            return frame, []
    
    def start_attendance_system(self):
        """Start the attendance system in a separate thread"""
        if self.attendance_running:
            return False, "Attendance system is already running"
        
        try:
            self.attendance_running = True
            self.attendance_thread = threading.Thread(target=self._run_attendance_system)
            self.attendance_thread.daemon = True
            self.attendance_thread.start()
            return True, "Attendance system started successfully"
        except Exception as e:
            self.attendance_running = False
            return False, f"Failed to start attendance system: {str(e)}"
    
    def stop_attendance_system(self):
        """Stop the attendance system"""
        if not self.attendance_running:
            return False, "Attendance system is not running"
        
        try:
            self.attendance_running = False
            if self.video_capture:
                self.video_capture.release()
            cv2.destroyAllWindows()
            return True, "Attendance system stopped successfully"
        except Exception as e:
            return False, f"Failed to stop attendance system: {str(e)}"
    
    def _run_attendance_system(self):
        """Internal method to run the attendance system"""
        self.video_capture = cv2.VideoCapture(0)
        
        if not self.video_capture.isOpened():
            print("Error: Could not open camera")
            self.attendance_running = False
            return
        
        print("Attendance system started...")
        
        try:
            while self.attendance_running:
                ret, frame = self.video_capture.read()
                if not ret:
                    print("Error: Could not read frame from camera")
                    break
                
                try:
                    # Process frame and mark attendance
                    processed_frame, attendance_marked = self.mark_attendance_for_frame(frame)
                    
                    # Display attendance status
                    if attendance_marked:
                        for name in attendance_marked:
                            print(f"Attendance marked for: {name} at {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Display the frame
                    cv2.imshow('Attendance System', processed_frame)
                    
                except Exception as e:
                    print(f"Error processing frame: {e}")
                    # Still show the original frame even if processing fails
                    cv2.imshow('Attendance System', frame)
                
                # Break on 'q' press or if window is closed
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except Exception as e:
            print(f"Error in attendance system: {e}")
        finally:
            if self.video_capture:
                self.video_capture.release()
            cv2.destroyAllWindows()
            self.attendance_running = False
            print("Attendance system stopped")
    
    def capture_face_for_registration(self, name):
        """Capture a face image for user registration"""
        video_capture = cv2.VideoCapture(0)
        
        if not video_capture.isOpened():
            return False, "Could not open camera"
        
        print(f"Capturing face for {name}...")
        print("Press 'c' to capture or 'q' to quit")
        
        while True:
            ret, frame = video_capture.read()
            if not ret:
                break
            
            # Display the frame
            cv2.imshow('Capture Face', frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('c'):
                # Save the captured image
                image_path = f"temp_{name}.jpg"
                cv2.imwrite(image_path, frame)
                video_capture.release()
                cv2.destroyAllWindows()
                
                # Try to add the face
                success, message = self.add_new_face(name, image_path)
                
                # Clean up temporary file
                if os.path.exists(image_path):
                    os.remove(image_path)
                
                return success, message
            
            elif key == ord('q'):
                break
        
        video_capture.release()
        cv2.destroyAllWindows()
        return False, "Face capture cancelled" 

    def process_attendance_frame(self, image_path):
        """Process a frame for real-time attendance"""
        try:
            # Load the image
            image = face_recognition.load_image_file(image_path)
            face_encodings = face_recognition.face_encodings(image)
            
            print(f"Found {len(face_encodings)} faces in frame")
            
            if len(face_encodings) == 0:
                return False, None, None
            
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
                        
                        # Check if user is already checked in today
                        today = datetime.now().date()
                        records = self.db.get_attendance_records(today)
                        
                        user_record = None
                        for record in records:
                            if record[1] == user_name:  # record[1] is the user name
                                user_record = record
                                break
                        
                        if user_record:
                            if user_record[2] and not user_record[3]:  # Has check-in but no check-out
                                # Mark check-out
                                self.db.mark_attendance(user_id, check_in=False)
                                print(f"Checked out {user_name}")
                                return True, user_name, 'check_out'
                            else:
                                # Already checked out, do nothing
                                print(f"{user_name} already checked out")
                                return False, None, None
                        else:
                            # Mark check-in
                            self.db.mark_attendance(user_id, check_in=True)
                            print(f"Checked in {user_name}")
                            return True, user_name, 'check_in'
                
                print("No face matches found with any tolerance level")
            else:
                print("No known faces loaded")
            
            return False, None, None
            
        except Exception as e:
            print(f"Error processing attendance frame: {e}")
            return False, None, None 