from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from database import AttendanceDatabase
from face_recognition_system_improved import FaceRecognitionSystemImproved
from face_recognition_network import NetworkFaceRecognitionSystem
from settings_manager import SettingsManager
from datetime import datetime, date
import os
import sys
import json
import shutil
import platform
# import psutil  # Comment out for now
import sqlite3
import numpy as np
from PIL import Image

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Initialize systems
db = AttendanceDatabase()
settings = SettingsManager()

# Use network-enabled face recognition system for multi-terminal support
network_face_system = NetworkFaceRecognitionSystem()

# Keep legacy system for backward compatibility
face_system = FaceRecognitionSystemImproved()

# Apply settings to both systems
for system in [face_system, network_face_system]:
    system.face_recognition_tolerance = settings.get('face_tolerance', 0.6)
    system.face_detection_cooldown = settings.get('face_detection_cooldown', 30)
    system.minimum_work_hours = settings.get('minimum_work_hours', 1.0)
    system.instant_mode = settings.get('instant_mode', True)

@app.route('/')
def index():
    """Main dashboard"""
    users = db.get_all_users()
    today_records = db.get_attendance_records(date.today())
    recent_records = db.get_attendance_records(date.today())
    
    # Get number of known faces
    known_faces_count = len(face_system.known_face_names)
    
    return render_template('index.html',
                         users=users,
                         today_records=today_records,
                         recent_records=recent_records,
                         known_faces_count=known_faces_count)

@app.route('/register', methods=['GET', 'POST'])
def register_user():
    """Register a new user"""
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            # Check if user already exists
            existing_users = db.get_all_users()
            if any(user[1].lower() == name.lower() for user in existing_users):
                if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                    return jsonify({'success': False, 'message': 'User already exists'})
                else:
                    flash('User already exists', 'error')
                    return redirect(url_for('register_user'))
            
            # Add user to database
            user_id = db.add_user(name, None)  # No face encoding yet
            
            if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                return jsonify({'success': True, 'user_id': user_id, 'message': f'User {name} registered successfully! Please capture their face using the camera button.'})
            else:
                flash(f"User {name} registered successfully! Please capture their face using the camera button.", 'success')
                return redirect(url_for('users'))
    
    return render_template('register.html')

@app.route('/capture_face_web', methods=['POST'])
def capture_face_web():
    """Capture face for user registration via web interface"""
    try:
        if 'face_image' not in request.files:
            return jsonify({'success': False, 'message': 'No face image provided'})
        
        face_file = request.files['face_image']
        user_id = request.form.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'No user ID provided'})
        
        # Get user name
        users = db.get_all_users()
        user_name = None
        for user in users:
            if user[0] == int(user_id):
                user_name = user[1]
                break
        
        if not user_name:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Save temporary file
        temp_path = f"temp_face_{user_id}.jpg"
        face_file.save(temp_path)
        
        # Check if user already has face encoding
        users = db.get_all_users()
        user_has_face = False
        for user in users:
            if user[0] == int(user_id) and user[2] is not None:
                user_has_face = True
                break
        
        # Update face encoding for existing user
        success, message = face_system.update_face_encoding(int(user_id), user_name, temp_path)
        
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        if success:
            # Reload face system to update known faces
            face_system.load_known_faces()
            return jsonify({'success': True, 'message': f'Face captured successfully for {user_name}'})
        else:
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error capturing face: {str(e)}'})

@app.route('/register_network_face', methods=['GET', 'POST'])
def register_network_face():
    """Register face to restaurant database (network-enabled)"""
    if request.method == 'GET':
        return render_template('register_network_face.html')
    
    try:
        employee_id = request.form['employee_id']
        full_name = request.form['full_name']
        
        if 'face_image' not in request.files:
            return jsonify({'success': False, 'message': 'No face image provided'})
        
        face_file = request.files['face_image']
        
        # Save temporary image
        temp_path = f'temp_network_face_{employee_id}.jpg'
        face_file.save(temp_path)
        
        # Register face to restaurant database
        success, message = network_face_system.register_face_to_restaurant(
            employee_id, full_name, temp_path
        )
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        if success:
            flash(f'Face registered successfully for {full_name}!', 'success')
            return jsonify({'success': True, 'message': message})
        else:
            flash(f'Failed to register face: {message}', 'error')
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        error_msg = f'Error registering face: {str(e)}'
        flash(error_msg, 'error')
        return jsonify({'success': False, 'message': error_msg})

@app.route('/sync_faces_from_restaurant', methods=['POST'])
def sync_faces_from_restaurant():
    """Manually sync face data from restaurant database"""
    try:
        success = network_face_system.sync_face_data_from_restaurant()
        
        if success:
            message = f"Successfully synced {len(network_face_system.known_face_encodings)} faces from restaurant database"
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': 'Failed to sync face data'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/network_status')
def network_status():
    """Get network face recognition system status"""
    try:
        status = network_face_system.get_system_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/capture_face/<name>')
def capture_face(name):
    """Capture face for user registration"""
    success, message = face_system.capture_face_for_registration(name)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    return redirect(url_for('index'))

@app.route('/attendance')
def attendance():
    """View attendance records"""
    selected_date = request.args.get('date')
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()
    
    records = db.get_attendance_records(selected_date)
    return render_template('attendance.html', records=records, selected_date=selected_date)

@app.route('/users')
def users():
    """Manage users"""
    users = db.get_all_users()
    return render_template('users.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Delete a user"""
    db.delete_user(user_id)
    # Reload face system to update known faces
    face_system.load_known_faces()
    flash('User deleted successfully', 'success')
    return redirect(url_for('users'))

@app.route('/start_attendance')
def start_attendance():
    """Start the attendance system"""
    try:
        # Start the face recognition system
        success, message = face_system.start_attendance_system()
        if success:
            flash('Attendance system started successfully! Face recognition is now active.', 'success')
        else:
            flash(f'Failed to start attendance system: {message}', 'error')
    except Exception as e:
        flash(f'Error starting attendance system: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/stop_attendance')
def stop_attendance():
    """Stop the attendance system"""
    try:
        # Stop the face recognition system
        success, message = face_system.stop_attendance_system()
        if success:
            flash('Attendance system stopped successfully!', 'success')
        else:
            flash(f'Failed to stop attendance system: {message}', 'error')
    except Exception as e:
        flash(f'Error stopping attendance system: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/manual_checkout/<int:user_id>', methods=['POST'])
def manual_checkout(user_id):
    """Manually check out a user"""
    try:
        # Find the user's attendance record for today
        today = date.today()
        records = db.get_attendance_records(today)
        
        # Find the record for this user
        user_record = None
        for record in records:
            if record[0] == user_id:  # record[0] is the attendance ID
                user_record = record
                break
        
        if user_record and user_record[2] and not user_record[3]:  # Has check-in but no check-out
            # Mark checkout
            db.mark_attendance(user_id, check_in=False)
            return jsonify({'success': True, 'message': 'Checkout successful'})
        else:
            return jsonify({'success': False, 'message': 'User not found or already checked out'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/auto_checkout_all')
def auto_checkout_all():
    """Automatically check out all present users"""
    try:
        today = date.today()
        records = db.get_attendance_records(today)
        
        checked_out_count = 0
        for record in records:
            if record[2] and not record[3]:  # Has check-in but no check-out
                db.mark_attendance(record[0], check_in=False)
                checked_out_count += 1
        
        flash(f'Automatically checked out {checked_out_count} users.', 'success')
        return redirect(url_for('attendance'))
    
    except Exception as e:
        flash(f'Error during auto checkout: {str(e)}', 'error')
        return redirect(url_for('attendance'))

@app.route('/api/attendance_today')
def api_attendance_today():
    """API endpoint for today's attendance"""
    today = date.today()
    records = db.get_attendance_records(today)
    
    attendance_data = []
    for record in records:
        record_id, name, check_in, check_out, record_date = record
        attendance_data.append({
            'id': record_id,
            'name': name,
            'check_in': str(check_in) if check_in else None,
            'check_out': str(check_out) if check_out else None,
            'date': str(record_date)
        })
    
    return jsonify(attendance_data)

@app.route('/process_attendance_frame', methods=['POST'])
def process_attendance_frame():
    """Process a frame for real-time attendance"""
    try:
        if 'frame' not in request.files:
            return jsonify({'success': False, 'message': 'No frame provided'})
        
        frame_file = request.files['frame']
        
        # Save temporary file
        temp_path = f"temp_attendance_frame.jpg"
        frame_file.save(temp_path)
        
        # Process frame with improved face recognition
        success, user_name, action, message = face_system.process_attendance_frame_improved(temp_path)
        
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return jsonify({
            'success': success,
            'user_name': user_name,
            'action': action,
            'message': message
        })
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error processing frame: {str(e)}'})

@app.route('/force_checkout', methods=['POST'])
def force_checkout():
    """Force checkout with confirmation"""
    try:
        data = request.get_json()
        user_name = data.get('user_name')
        confirm = data.get('confirm', False)
        
        if not user_name or not confirm:
            return jsonify({'success': False, 'message': 'Invalid request'})
        
        # Get user ID from name
        users = db.get_all_users()
        user_id = None
        for user in users:
            if user[1] == user_name:
                user_id = user[0]
                break
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Create a temporary image file for forced checkout
        temp_path = f"temp_force_checkout.jpg"
        # Create a 1x1 pixel image
        import numpy as np
        from PIL import Image
        img = Image.fromarray(np.zeros((1, 1, 3), dtype=np.uint8))
        img.save(temp_path)
        
        try:
            # Force checkout with confirmation
            success, user_name, action, message = face_system.process_attendance_frame_improved(
                temp_path, force_action='check_out', confirm_checkout=True
            )
            
            return jsonify({
                'success': success,
                'user_name': user_name,
                'action': action,
                'message': message
            })
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error processing checkout: {str(e)}'})

# ===============================================
# ADMIN PANEL ROUTES
# ===============================================

def get_system_stats():
    """Get system statistics"""
    users = db.get_all_users()
    today_records = db.get_attendance_records(date.today())
    
    users_with_faces = sum(1 for user in users if user[2] is not None)
    # uptime_seconds = psutil.boot_time()
    # uptime_hours = int((datetime.now().timestamp() - uptime_seconds) / 3600)
    uptime_hours = 24  # Placeholder for now
    
    return {
        'total_users': len(users),
        'users_with_faces': users_with_faces,
        'today_checkins': len(today_records),
        'system_uptime': f"{uptime_hours}h"
    }

def get_system_info():
    """Get detailed system information"""
    try:
        # Get database size
        db_size = os.path.getsize('attendance.db') / 1024 / 1024  # MB
        
        # Get face encodings count
        users = db.get_all_users()
        face_encodings_count = sum(1 for user in users if user[2] is not None)
        
        # Get last backup info
        backup_dir = 'backups'
        last_backup = None
        if os.path.exists(backup_dir):
            backups = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
            if backups:
                latest_backup = max(backups, key=lambda x: os.path.getctime(os.path.join(backup_dir, x)))
                last_backup = datetime.fromtimestamp(os.path.getctime(os.path.join(backup_dir, latest_backup))).strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            'version': '1.0.0',
            'python_version': platform.python_version(),
            'db_size': f"{db_size:.2f} MB",
            'face_encodings_count': face_encodings_count,
            'uptime': get_system_stats()['system_uptime'],
            'last_backup': last_backup
        }
    except Exception as e:
        return {
            'version': '1.0.0',
            'python_version': platform.python_version(),
            'db_size': 'Unknown',
            'face_encodings_count': 0,
            'uptime': 'Unknown',
            'last_backup': None
        }

@app.route('/admin')
def admin_panel():
    """Admin panel main page"""
    stats = get_system_stats()
    system_info = get_system_info()
    current_settings = settings.get_all()
    
    # Determine system status
    system_status = 'online'
    if stats['total_users'] == 0:
        system_status = 'warning'
    elif stats['users_with_faces'] < stats['total_users'] / 2:
        system_status = 'warning'
    
    return render_template('admin.html',
                         stats=stats,
                         system_info=system_info,
                         settings=current_settings,
                         system_status=system_status)

@app.route('/admin/stats')
def admin_stats():
    """Get system stats via API"""
    try:
        stats = get_system_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/update_settings', methods=['POST'])
def admin_update_settings():
    """Update system settings"""
    try:
        new_settings = {}
        
        # Face Recognition Settings
        if 'face_tolerance' in request.form:
            new_settings['face_tolerance'] = float(request.form['face_tolerance'])
        if 'face_detection_cooldown' in request.form:
            new_settings['face_detection_cooldown'] = int(request.form['face_detection_cooldown'])
        if 'instant_mode' in request.form:
            new_settings['instant_mode'] = True
        else:
            new_settings['instant_mode'] = False
            
        # Attendance Rules
        if 'minimum_work_hours' in request.form:
            new_settings['minimum_work_hours'] = float(request.form['minimum_work_hours'])
        if 'overtime_threshold' in request.form:
            new_settings['overtime_threshold'] = float(request.form['overtime_threshold'])
        if 'late_arrival_threshold' in request.form:
            new_settings['late_arrival_threshold'] = int(request.form['late_arrival_threshold'])
        if 'grace_period' in request.form:
            new_settings['grace_period'] = int(request.form['grace_period'])
            
        # System Settings
        if 'system_name' in request.form:
            new_settings['system_name'] = request.form['system_name']
        if 'company_name' in request.form:
            new_settings['company_name'] = request.form['company_name']
        if 'debug_mode' in request.form:
            new_settings['debug_mode'] = True
        else:
            new_settings['debug_mode'] = False
        
        # Validate settings
        for key, value in new_settings.items():
            if not settings.validate_setting(key, value):
                flash(f'Invalid value for {key}: {value}', 'error')
                return redirect(url_for('admin_panel'))
        
        # Update settings
        if settings.update(new_settings):
            # Apply settings to face system
            face_system.face_recognition_tolerance = settings.get('face_tolerance', 0.6)
            face_system.face_detection_cooldown = settings.get('face_detection_cooldown', 30)
            face_system.minimum_work_hours = settings.get('minimum_work_hours', 1.0)
            face_system.instant_mode = settings.get('instant_mode', True)
            
            flash('Settings updated successfully!', 'success')
        else:
            flash('Error updating settings!', 'error')
            
    except Exception as e:
        flash(f'Error updating settings: {str(e)}', 'error')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/reset_settings', methods=['POST'])
def admin_reset_settings():
    """Reset settings to defaults"""
    try:
        if settings.reset_to_defaults():
            # Apply default settings to face system
            face_system.face_recognition_tolerance = settings.get('face_tolerance', 0.6)
            face_system.face_detection_cooldown = settings.get('face_detection_cooldown', 30)
            face_system.minimum_work_hours = settings.get('minimum_work_hours', 1.0)
            face_system.instant_mode = settings.get('instant_mode', True)
            
            return jsonify({'success': True, 'message': 'Settings reset to defaults'})
        else:
            return jsonify({'success': False, 'message': 'Failed to reset settings'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/export_settings')
def admin_export_settings():
    """Export settings to JSON file"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'settings_backup_{timestamp}.json'
        
        # Create temporary file
        temp_path = f'/tmp/{filename}'
        if settings.export_settings(temp_path):
            return send_file(temp_path, as_attachment=True, download_name=filename)
        else:
            flash('Error exporting settings!', 'error')
            return redirect(url_for('admin_panel'))
    except Exception as e:
        flash(f'Error exporting settings: {str(e)}', 'error')
        return redirect(url_for('admin_panel'))

@app.route('/admin/import_settings', methods=['POST'])
def admin_import_settings():
    """Import settings from JSON file"""
    try:
        if 'settings_file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'})
        
        file = request.files['settings_file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'})
        
        if file and file.filename.endswith('.json'):
            # Save uploaded file temporarily
            temp_path = f'/tmp/imported_settings.json'
            file.save(temp_path)
            
            if settings.import_settings(temp_path):
                # Apply imported settings to face system
                face_system.face_recognition_tolerance = settings.get('face_tolerance', 0.6)
                face_system.face_detection_cooldown = settings.get('face_detection_cooldown', 30)
                face_system.minimum_work_hours = settings.get('minimum_work_hours', 1.0)
                face_system.instant_mode = settings.get('instant_mode', True)
                
                os.remove(temp_path)
                return jsonify({'success': True, 'message': 'Settings imported successfully'})
            else:
                os.remove(temp_path)
                return jsonify({'success': False, 'message': 'Failed to import settings'})
        else:
            return jsonify({'success': False, 'message': 'Invalid file type'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/create_backup', methods=['POST'])
def admin_create_backup():
    """Create database backup"""
    try:
        # Create backups directory
        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'attendance_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy database file
        shutil.copy2('attendance.db', backup_path)
        
        # Also backup settings
        settings_backup = f'settings_backup_{timestamp}.json'
        settings_path = os.path.join(backup_dir, settings_backup)
        settings.export_settings(settings_path)
        
        return jsonify({'success': True, 'message': f'Backup created: {backup_filename}'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/logs')
def admin_logs():
    """Get system logs"""
    try:
        logs = []
        
        # Get recent app logs (you would implement proper logging)
        logs.append(f"[{datetime.now()}] System started")
        logs.append(f"[{datetime.now()}] Face system initialized with {len(face_system.known_face_names)} faces")
        logs.append(f"[{datetime.now()}] Settings loaded successfully")
        
        # Add some recent activity logs
        today_records = db.get_attendance_records(date.today())
        for record in today_records[-10:]:  # Last 10 records
            if record[2]:  # Check-in time
                logs.append(f"[{record[2]}] User {record[1]} checked in")
            if record[3]:  # Check-out time  
                logs.append(f"[{record[3]}] User {record[1]} checked out")
        
        log_text = '\n'.join(logs)
        return jsonify({'success': True, 'logs': log_text})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/bulk_operations')
def admin_bulk_operations():
    """Handle bulk operations"""
    # This would be expanded for bulk user operations
    return jsonify({'success': True, 'message': 'Bulk operations endpoint'})

# ===============================================
# RESTAURANT INTEGRATION ROUTES
# ===============================================

@app.route('/integration')
def integration_dashboard():
    """Restaurant integration dashboard"""
    try:
        from restaurant_integration import get_integration_dashboard
        
        # Get integration status
        integration_status = get_integration_dashboard()
        
        return render_template('integration.html',
                             integration_status=integration_status,
                             page_title="Restaurant Integration")
    except Exception as e:
        flash(f'Error loading integration dashboard: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/integration/sync_staff', methods=['POST'])
def sync_staff():
    """Sync staff from restaurant system"""
    try:
        from restaurant_integration import quick_sync_staff
        
        result = quick_sync_staff()
        
        if result['success']:
            flash(f"Successfully synced {result['synced_count']} staff members", 'success')
        else:
            flash(f"Sync failed: {result.get('error', 'Unknown error')}", 'error')
            
        return redirect(url_for('integration_dashboard'))
        
    except Exception as e:
        flash(f'Error syncing staff: {str(e)}', 'error')
        return redirect(url_for('integration_dashboard'))

@app.route('/integration/process_attendance', methods=['POST'])
def process_attendance():
    """Process and sync today's attendance"""
    try:
        from restaurant_integration import quick_process_attendance
        from datetime import date
        
        target_date = request.form.get('date')
        if target_date:
            target_date = date.fromisoformat(target_date)
        else:
            target_date = date.today()
        
        result = quick_process_attendance(target_date)
        
        if result['success']:
            process_count = result['process_result']['processed_count']
            sync_count = result['sync_result']['synced_count']
            flash(f"Processed {process_count} attendance records, synced {sync_count} to restaurant system", 'success')
        else:
            flash(f"Processing failed: {result.get('error', 'Unknown error')}", 'error')
            
        return redirect(url_for('integration_dashboard'))
        
    except Exception as e:
        flash(f'Error processing attendance: {str(e)}', 'error')
        return redirect(url_for('integration_dashboard'))

@app.route('/integration/status_api')
def integration_status_api():
    """Get integration status via API"""
    try:
        from restaurant_integration import get_integration_dashboard
        
        status = get_integration_dashboard()
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/integration/staff_summary')
def staff_work_summary():
    """Get staff work summary"""
    try:
        from restaurant_integration import RestaurantFaceIntegration
        from datetime import date, timedelta
        
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = date.fromisoformat(start_date)
        else:
            start_date = date.today() - timedelta(days=7)
            
        if end_date:
            end_date = date.fromisoformat(end_date)
        else:
            end_date = date.today()
        
        integration = RestaurantFaceIntegration()
        try:
            summary = integration.get_staff_work_summary(
                start_date=start_date,
                end_date=end_date
            )
            return jsonify(summary)
        finally:
            integration.close()
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/integration/test_connection', methods=['POST'])
def test_restaurant_connection():
    """Test connection to restaurant system"""
    try:
        try:
            import requests
            REQUESTS_AVAILABLE = True
        except ImportError:
            return jsonify({
                'success': False,
                'message': 'requests module not installed - please run: pip install requests',
                'status': 'error'
            })
        
        # Test connection to Frappe restaurant system
        response = requests.get('http://site1.local:8000/api/method/restaurant_management.api.get_positions', timeout=5)
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'Restaurant system connection successful',
                'status': 'online'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Restaurant system returned status {response.status_code}',
                'status': 'error'
            })
            
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'message': 'Cannot connect to restaurant system',
            'status': 'offline'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Connection test failed: {str(e)}',
            'status': 'error'
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 