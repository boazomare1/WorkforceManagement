#!/usr/bin/env python3
"""
Utility script to fix duplicate users in the attendance database
"""

from database import AttendanceDatabase
from datetime import datetime

def fix_duplicate_users():
    """Remove duplicate users and merge their attendance records"""
    db = AttendanceDatabase()
    
    print("Fixing duplicate users...")
    
    # Get all users
    users = db.get_all_users()
    
    # Group users by name (case-insensitive)
    user_groups = {}
    for user in users:
        user_id, name, face_encoding = user
        name_key = name.lower().strip()
        
        if name_key not in user_groups:
            user_groups[name_key] = []
        user_groups[name_key].append(user)
    
    # Find and fix duplicates
    duplicates_found = 0
    for name_key, user_list in user_groups.items():
        if len(user_list) > 1:
            duplicates_found += 1
            print(f"\nFound {len(user_list)} duplicates for '{user_list[0][1]}':")
            
            # Keep the user with face encoding, or the first one if none have encoding
            primary_user = None
            users_to_remove = []
            
            # First, try to find a user with face encoding
            for user in user_list:
                user_id, name, face_encoding = user
                print(f"  - ID: {user_id}, Name: '{name}', Has Face: {face_encoding is not None}")
                
                if face_encoding is not None and primary_user is None:
                    primary_user = user
                else:
                    users_to_remove.append(user)
            
            # If no user has face encoding, keep the first one
            if primary_user is None:
                primary_user = user_list[0]
                users_to_remove = user_list[1:]
            
            print(f"  → Keeping user ID {primary_user[0]} as primary")
            
            # Merge attendance records from duplicate users to primary user
            for user_to_remove in users_to_remove:
                merge_attendance_records(db, user_to_remove[0], primary_user[0])
                
            # Remove duplicate users
            for user_to_remove in users_to_remove:
                print(f"  → Removing duplicate user ID {user_to_remove[0]}")
                db.delete_user(user_to_remove[0])
    
    if duplicates_found == 0:
        print("No duplicate users found!")
    else:
        print(f"\nFixed {duplicates_found} duplicate user groups.")
    
    # Show final user list
    print("\nFinal user list:")
    final_users = db.get_all_users()
    for user in final_users:
        user_id, name, face_encoding = user
        print(f"  - ID: {user_id}, Name: '{name}', Has Face: {face_encoding is not None}")

def merge_attendance_records(db, from_user_id, to_user_id):
    """Merge attendance records from one user to another"""
    import sqlite3
    
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # Update attendance records to point to the primary user
        cursor.execute('''
            UPDATE attendance 
            SET user_id = ? 
            WHERE user_id = ?
        ''', (to_user_id, from_user_id))
        
        records_updated = cursor.rowcount
        if records_updated > 0:
            print(f"    → Merged {records_updated} attendance records")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"    → Error merging attendance records: {e}")

if __name__ == "__main__":
    fix_duplicate_users()