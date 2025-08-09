#!/usr/bin/env python3
"""
Improved Facial Recognition Attendance System
Enhanced with better controls for check-in/check-out, confirmation dialogs, and minimum work time validation.
"""

import sys
import argparse
from face_recognition_system_improved import FaceRecognitionSystemImproved
from database import AttendanceDatabase
from web_interface_improved import app

def main():
    parser = argparse.ArgumentParser(description='Improved Facial Recognition Attendance System')
    parser.add_argument('--mode', choices=['web', 'cli', 'attendance'], 
                       default='web', help='Run mode: web interface, CLI, or attendance system')
    parser.add_argument('--host', default='0.0.0.0', help='Host for web interface')
    parser.add_argument('--port', type=int, default=5000, help='Port for web interface')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--min-hours', type=float, default=1.0, help='Minimum work hours before checkout')
    parser.add_argument('--cooldown', type=int, default=30, help='Cooldown seconds between detections')
    
    args = parser.parse_args()
    
    if args.mode == 'web':
        print("Starting improved web interface...")
        print(f"Access the system at: http://{args.host}:{args.port}")
        print(f"Minimum work hours: {args.min_hours}")
        print(f"Detection cooldown: {args.cooldown} seconds")
        app.run(host=args.host, port=args.port, debug=args.debug)
    
    elif args.mode == 'cli':
        run_cli(args)
    
    elif args.mode == 'attendance':
        face_system = FaceRecognitionSystemImproved()
        face_system.minimum_work_hours = args.min_hours
        face_system.face_detection_cooldown = args.cooldown
        face_system.run_attendance_system()

def run_cli(args):
    """Run the command-line interface"""
    face_system = FaceRecognitionSystemImproved()
    face_system.minimum_work_hours = args.min_hours
    face_system.face_detection_cooldown = args.cooldown
    db = AttendanceDatabase()
    
    print("=== Improved Facial Recognition Attendance System ===")
    print(f"Settings: Min hours: {args.min_hours}, Cooldown: {args.cooldown}s")
    print("1. Register new user")
    print("2. Start attendance system")
    print("3. View attendance records")
    print("4. View all users")
    print("5. Fix duplicate users")
    print("6. Test face recognition")
    print("7. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-7): ").strip()
            
            if choice == '1':
                name = input("Enter user name: ").strip()
                if name:
                    success, message = face_system.add_new_face(name, None)
                    print(f"Result: {message}")
                else:
                    print("Name cannot be empty")
            
            elif choice == '2':
                print("\nStarting attendance system...")
                print("Use web interface for confirmations and forced actions.")
                face_system.run_attendance_system()
            
            elif choice == '3':
                from datetime import date
                records = db.get_attendance_records(date.today())
                print(f"\nAttendance records for {date.today()}:")
                for record in records:
                    record_id, name, check_in, check_out, record_date = record
                    status = "Checked out" if check_out else "Checked in"
                    print(f"  {name}: {check_in} - {check_out or 'Still working'} ({status})")
            
            elif choice == '4':
                users = db.get_all_users()
                print(f"\nAll users ({len(users)}):")
                for user in users:
                    user_id, name, face_encoding = user
                    has_face = "Yes" if face_encoding else "No"
                    print(f"  ID: {user_id}, Name: {name}, Face: {has_face}")
            
            elif choice == '5':
                from fix_duplicate_users import fix_duplicate_users
                fix_duplicate_users()
                face_system.load_known_faces()  # Reload after fixing
            
            elif choice == '6':
                image_path = input("Enter path to test image: ").strip()
                if image_path:
                    success, user_name, action, message = face_system.process_attendance_frame_improved(image_path)
                    print(f"Result: {message}")
                    if success:
                        print(f"  User: {user_name}, Action: {action}")
                else:
                    print("Image path cannot be empty")
            
            elif choice == '7':
                print("Goodbye!")
                break
            
            else:
                print("Invalid choice. Please enter 1-7.")
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()