#!/usr/bin/env python3
"""
Facial Recognition Attendance System
A simple attendance system using facial recognition technology.
"""

import sys
import argparse
from face_recognition_system import FaceRecognitionSystem
from database import AttendanceDatabase
from web_interface import app

def main():
    parser = argparse.ArgumentParser(description='Facial Recognition Attendance System')
    parser.add_argument('--mode', choices=['web', 'cli', 'attendance'], 
                       default='web', help='Run mode: web interface, CLI, or attendance system')
    parser.add_argument('--host', default='0.0.0.0', help='Host for web interface')
    parser.add_argument('--port', type=int, default=5000, help='Port for web interface')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    if args.mode == 'web':
        print("Starting web interface...")
        print(f"Access the system at: http://{args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=args.debug)
    
    elif args.mode == 'cli':
        run_cli()
    
    elif args.mode == 'attendance':
        face_system = FaceRecognitionSystem()
        face_system.run_attendance_system()

def run_cli():
    """Run the command-line interface"""
    face_system = FaceRecognitionSystem()
    db = AttendanceDatabase()
    
    print("=== Facial Recognition Attendance System ===")
    print("1. Register new user")
    print("2. Start attendance system")
    print("3. View attendance records")
    print("4. View all users")
    print("5. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                register_user_cli(face_system)
            elif choice == '2':
                print("Starting attendance system... Press 'q' to quit.")
                face_system.run_attendance_system()
            elif choice == '3':
                view_attendance_cli(db)
            elif choice == '4':
                view_users_cli(db)
            elif choice == '5':
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1-5.")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

def register_user_cli(face_system):
    """Register a new user via CLI"""
    name = input("Enter user name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return
    
    print(f"Capturing face for {name}...")
    print("Position your face in front of the camera and press 'c' to capture.")
    print("Press 'q' to cancel.")
    
    success, message = face_system.capture_face_for_registration(name)
    print(message)

def view_attendance_cli(db):
    """View attendance records via CLI"""
    from datetime import date
    
    print("\n=== Attendance Records ===")
    today = date.today()
    records = db.get_attendance_records(today)
    
    if records:
        print(f"Today's attendance ({today}):")
        print("-" * 60)
        print(f"{'Name':<20} {'Check In':<12} {'Check Out':<12} {'Status':<10}")
        print("-" * 60)
        
        for record in records:
            record_id, name, check_in, check_out, record_date = record
            check_in_str = check_in.strftime('%H:%M:%S') if check_in else '-'
            check_out_str = check_out.strftime('%H:%M:%S') if check_out else '-'
            status = "Present" if check_in else "Absent"
            
            print(f"{name:<20} {check_in_str:<12} {check_out_str:<12} {status:<10}")
    else:
        print("No attendance records for today.")

def view_users_cli(db):
    """View all users via CLI"""
    print("\n=== Registered Users ===")
    users = db.get_all_users()
    
    if users:
        print("-" * 50)
        print(f"{'ID':<5} {'Name':<20} {'Face Registered':<15} {'Created':<20}")
        print("-" * 50)
        
        for user in users:
            user_id, name, face_encoding = user[:3]
            created_at = user[3] if len(user) > 3 else "N/A"
            face_registered = "Yes" if face_encoding else "No"
            print(f"{user_id:<5} {name:<20} {face_registered:<15} {created_at}")
    else:
        print("No users registered yet.")

if __name__ == '__main__':
    main() 