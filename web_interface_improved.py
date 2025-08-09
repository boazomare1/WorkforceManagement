from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database import AttendanceDatabase
from face_recognition_system_improved import FaceRecognitionSystemImproved
from datetime import datetime, date
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Initialize systems
db = AttendanceDatabase()
face_system = FaceRecognitionSystemImproved()

@app.route('/')
def index():
    """Main dashboard"""
    users = db.get_all_users()
    today_records = db.get_attendance_records(date.today())
    recent_records = db.get_attendance_records(date.today())
    
    # Get number of known faces
    known_faces_count = len(face_system.known_face_names)
    
    # Get pending checkouts
    pending_checkouts = face_system.get_pending_checkout_users()
    
    return render_template('index.html',
                         users=users,
                         today_records=today_records,
                         recent_records=recent_records,
                         known_faces_count=known_faces_count,
                         pending_checkouts=pending_checkouts)

@app.route('/register', methods=['GET', 'POST'])
def register_user():
    """Register a new user"""
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            # Add user to database (improved version checks for duplicates)
            success, message = face_system.add_new_face(name, None)  # No face encoding yet
            
            if success:
                if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                    return jsonify({'success': True, 'message': message})
                else:
                    flash(message, 'success')
                    return redirect(url_for('users'))
            else:
                if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                    return jsonify({'success': False, 'message': message})
                else:
                    flash(message, 'error')
                    return redirect(url_for('register_user'))
        else:
            error_msg = 'Name is required'
            if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                return jsonify({'success': False, 'message': error_msg})
            else:
                flash(error_msg, 'error')
                return redirect(url_for('register_user'))
    
    return render_template('register.html')

@app.route('/users')
def users():
    """View all users"""
    users = db.get_all_users()
    return render_template('users.html', users=users)

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    """Delete a user"""
    try:
        db.delete_user(user_id)
        face_system.load_known_faces()  # Reload faces after deletion
        flash('User deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('users'))

@app.route('/attendance')
def attendance():
    """View attendance records"""
    selected_date = request.args.get('date', str(date.today()))
    
    try:
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
        records = db.get_attendance_records(selected_date_obj)
    except ValueError:
        flash('Invalid date format', 'error')
        selected_date_obj = date.today()
        records = db.get_attendance_records(selected_date_obj)
        selected_date = str(selected_date_obj)
    
    return render_template('attendance.html', 
                         records=records, 
                         selected_date=selected_date)

@app.route('/attendance_view')
def attendance_view():
    """Real-time attendance view"""
    return render_template('attendance_view.html')

@app.route('/auto_checkout')
def auto_checkout():
    """Automatically check out all users who are still checked in"""
    try:
        today = date.today()
        records = db.get_attendance_records(today)
        
        checked_out_count = 0
        for record in records:
            if record[2] and not record[3]:  # Has check-in but no check-out
                # Use the record ID which should be the user_id in attendance table
                # We need to get the actual user_id from the users table
                user_name = record[1]
                users = db.get_all_users()
                user_id = None
                for user in users:
                    if user[1] == user_name:
                        user_id = user[0]
                        break
                
                if user_id:
                    db.mark_attendance(user_id, check_in=False)
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
    """Process a frame for smart attendance with improved controls"""
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

@app.route('/force_checkin', methods=['POST'])
def force_checkin():
    """Force check-in for detected user"""
    try:
        data = request.get_json()
        user_name = data.get('user_name')
        
        if not user_name:
            return jsonify({'success': False, 'message': 'User name required'})
        
        # Find user ID
        users = db.get_all_users()
        user_id = None
        for user in users:
            if user[1] == user_name:
                user_id = user[0]
                break
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Force check-in
        db.mark_attendance(user_id, check_in=True)
        
        return jsonify({
            'success': True,
            'message': f'Checked in {user_name} successfully',
            'action': 'check_in'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/force_checkout', methods=['POST'])
def force_checkout():
    """Force check-out for detected user with confirmation"""
    try:
        data = request.get_json()
        user_name = data.get('user_name')
        confirm = data.get('confirm', False)
        
        if not user_name:
            return jsonify({'success': False, 'message': 'User name required'})
        
        # Find user ID
        users = db.get_all_users()
        user_id = None
        for user in users:
            if user[1] == user_name:
                user_id = user[0]
                break
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Check minimum work time and force checkout if confirmed
        can_checkout, message = face_system.can_checkout_user(user_id, user_name)
        
        if not can_checkout:
            return jsonify({'success': False, 'message': str(message)})
        
        if confirm:
            # Perform the checkout
            db.mark_attendance(user_id, check_in=False)
            face_system.clear_pending_checkout(user_id)
            
            hours_worked = message  # message contains hours worked
            return jsonify({
                'success': True,
                'message': f'Checked out {user_name}. Worked: {hours_worked:.1f} hours',
                'action': 'check_out'
            })
        else:
            # Return confirmation requirement
            hours_worked = message
            return jsonify({
                'success': False,
                'message': f'Confirm checkout for {user_name}? Worked: {hours_worked:.1f} hours',
                'action': 'checkout_confirmation',
                'requires_confirmation': True
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/update_face_encoding', methods=['POST'])
def update_face_encoding():
    """Update face encoding for a user"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image provided'})
        
        user_id = request.form.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'})
        
        image_file = request.files['image']
        
        # Save temporary file
        temp_path = f"temp_face_image_{user_id}.jpg"
        image_file.save(temp_path)
        
        # Get user name
        users = db.get_all_users()
        user_name = None
        for user in users:
            if str(user[0]) == str(user_id):
                user_name = user[1]
                break
        
        if not user_name:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Update face encoding
        success, message = face_system.add_new_face(user_name, temp_path)
        
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        if success:
            # Reload faces
            face_system.load_known_faces()
            return jsonify({'success': True, 'message': f'Face encoding updated for {user_name}'})
        else:
            return jsonify({'success': False, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating face encoding: {str(e)}'})

@app.route('/get_system_status')
def get_system_status():
    """Get current system status"""
    try:
        pending_checkouts = face_system.get_pending_checkout_users()
        
        # Get user names for pending checkouts
        pending_users = []
        if pending_checkouts:
            users = db.get_all_users()
            for user_id in pending_checkouts:
                for user in users:
                    if user[0] == user_id:
                        pending_users.append(user[1])
                        break
        
        return jsonify({
            'success': True,
            'data': {
                'known_faces': len(face_system.known_face_names),
                'pending_checkouts': pending_users,
                'minimum_work_hours': face_system.minimum_work_hours,
                'detection_cooldown': face_system.face_detection_cooldown
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)