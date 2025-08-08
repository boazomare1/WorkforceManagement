from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database import AttendanceDatabase
from face_recognition_system import FaceRecognitionSystem
from datetime import datetime, date
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Initialize systems
db = AttendanceDatabase()
face_system = FaceRecognitionSystem()

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
                return jsonify({'success': True, 'user_id': user_id, 'message': f'User {name} registered successfully!'})
            else:
                flash(f"User {name} registered successfully! Please use the face capture feature.", 'success')
                return redirect(url_for('index'))
    
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
        
        # Process face with face recognition system
        success, message = face_system.add_new_face(user_name, temp_path)
        
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
        
        # Process frame with face recognition
        success, user_name, action = face_system.process_attendance_frame(temp_path)
        
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        if success:
            return jsonify({
                'success': True, 
                'user_name': user_name, 
                'action': action
            })
        else:
            return jsonify({'success': False, 'message': 'No face recognized'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error processing frame: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 