# 🎯 Facial Recognition Attendance System

A modern, web-based facial recognition attendance system built with Python Flask and OpenCV. This system provides real-time face detection and attendance tracking through a beautiful web interface, making it perfect for businesses, schools, or any organization that needs automated attendance management.

## ✨ Features

### 🔐 **Facial Recognition**
- **Real-time face detection** using OpenCV and face_recognition library
- **High-accuracy recognition** with multiple tolerance levels for better matching
- **Privacy-focused** - stores only face encodings, not actual images
- **Automatic face encoding** during user registration

### 🌐 **Web-Based Interface**
- **Modern Bootstrap 5 UI** with responsive design
- **Real-time camera integration** for face capture and attendance
- **Live attendance tracking** with instant check-in/check-out
- **User-friendly dashboard** with attendance overview and statistics

### 📊 **Attendance Management**
- **Automatic check-in/check-out** based on face recognition
- **Manual attendance controls** for administrators
- **Daily attendance records** with timestamps
- **Attendance history** with detailed reports
- **Auto checkout functionality** for end-of-day processing

### 👥 **User Management**
- **Easy user registration** through web interface
- **Face capture integration** during registration
- **User database management** with SQLite
- **User listing and management** interface

## 🏗️ System Architecture

### **Backend Components**
- **Flask Web Server** - Handles HTTP requests and serves web pages
- **Face Recognition Engine** - Processes images and matches faces
- **SQLite Database** - Stores users and attendance records
- **OpenCV Integration** - Camera access and image processing

### **Frontend Components**
- **Bootstrap 5** - Modern, responsive UI framework
- **JavaScript** - Real-time camera integration and AJAX requests
- **HTML Templates** - Jinja2 templating for dynamic content
- **Font Awesome** - Beautiful icons throughout the interface

## 🚀 Quick Start

### **Prerequisites**
- Python 3.8 or higher
- Webcam/camera access
- Linux/Windows/macOS

### **Installation**

1. **Clone the repository**
   ```bash
   git clone https://github.com/boazomare1/WorkforceManagement.git
   cd WorkforceManagement
   ```

2. **Run the installation script**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Start the system**
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

4. **Access the web interface**
   Open your browser and go to: `http://localhost:5000`

## 📖 How It Works

### **1. User Registration Process**
```
User visits /register → Enters name → Clicks "Capture Face" → 
Camera opens in modal → User positions face → System captures image → 
Face encoding generated → User saved to database → Registration complete
```

### **2. Attendance Tracking Process**
```
User clicks "Start Attendance" → Camera modal opens → 
System captures frames every 2 seconds → Face recognition processes each frame → 
If face recognized → Check attendance status → 
Mark check-in (if first time today) or check-out (if already checked in) → 
Update dashboard in real-time
```

### **3. Database Structure**
- **Users Table**: Stores user information and face encodings
- **Attendance Table**: Records check-in/check-out times with dates
- **Automatic Creation**: Database and tables created on first run

## 🎮 Usage Guide

### **For Administrators**

#### **Dashboard Overview**
- **Today's Attendance**: View current day's attendance status
- **Quick Stats**: Total users and present count
- **Recent Activity**: Latest attendance events
- **Quick Actions**: Start attendance, register users, view records

#### **User Management**
1. **Register New Users**
   - Go to "Register" page
   - Enter user's name
   - Click "Capture Face" to take photo
   - System automatically encodes and saves face

2. **View All Users**
   - Navigate to "Users" page
   - See all registered users
   - Access registration for new users

#### **Attendance Control**
1. **Start Attendance System**
   - Click "Start Attendance System" on dashboard
   - Camera modal opens for face recognition
   - System automatically processes faces

2. **Manual Controls**
   - **Auto Checkout All**: Check out all present users
   - **Individual Checkout**: Check out specific users from attendance page

### **For Users**

#### **Check-in Process**
1. Look at the camera when attendance system is running
2. System recognizes your face automatically
3. Check-in is marked with timestamp
4. Dashboard updates in real-time

#### **Check-out Process**
1. Look at the camera again during attendance
2. System recognizes you and checks your status
3. If already checked in, marks check-out
4. If already checked out, no action taken

## 🔧 Technical Details

### **Face Recognition Algorithm**
- Uses `face_recognition` library (dlib-based)
- Multiple tolerance levels (0.6, 0.5, 0.4) for better accuracy
- Face encoding stored as numpy arrays in database
- Real-time processing with 2-second intervals

### **Web Interface Features**
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Real-time Updates**: AJAX requests for live data
- **Camera Integration**: WebRTC for browser camera access
- **Modal Dialogs**: Bootstrap modals for camera interactions

### **Database Operations**
- **Automatic Migration**: Handles schema changes gracefully
- **NULL Support**: Users can be registered without face encodings
- **Transaction Safety**: SQLite transactions for data integrity
- **Date-based Queries**: Efficient attendance record retrieval

## 🛠️ File Structure

```
WorkforceManagement/
├── main.py                    # Application entry point
├── web_interface.py           # Flask routes and web logic
├── database.py                # Database operations and schema
├── face_recognition_system.py # Face recognition engine
├── requirements.txt           # Python dependencies
├── install.sh                 # Installation script
├── run.sh                     # Startup script
├── README.md                  # This file
├── .gitignore                 # Git ignore rules
└── templates/                 # HTML templates
    ├── base.html             # Base template with navigation
    ├── index.html            # Dashboard page
    ├── register.html         # User registration page
    ├── attendance.html       # Attendance records page
    ├── users.html            # User management page
    └── attendance_view.html  # Detailed attendance view
```

## 🔒 Privacy & Security

### **Data Protection**
- **No Image Storage**: Only face encodings (mathematical representations) are stored
- **Local Database**: All data stays on your local machine
- **No Cloud Dependencies**: System works completely offline
- **User Control**: Users can be deleted along with their data

### **Camera Access**
- **Browser Permissions**: Camera access requires user consent
- **Local Processing**: All face recognition happens locally
- **Temporary Files**: Captured images are deleted after processing

## 🐛 Troubleshooting

### **Common Issues**

1. **Camera Not Working**
   - Ensure camera permissions are granted in browser
   - Check if camera is being used by another application
   - Try refreshing the page

2. **Face Recognition Not Working**
   - Ensure good lighting conditions
   - Position face clearly in camera view
   - Check if user is properly registered with face encoding

3. **Installation Issues**
   - Ensure Python 3.8+ is installed
   - Run `pip install -r requirements.txt` manually if needed
   - Check system dependencies for OpenCV

### **Performance Tips**
- **Good Lighting**: Better lighting improves recognition accuracy
- **Clear Face View**: Ensure face is clearly visible and centered
- **Stable Camera**: Minimize movement during face capture
- **Regular Updates**: Keep face encodings updated for better accuracy

## 🚀 Future Enhancements

### **Planned Features**
- **Multi-face Detection**: Handle multiple faces simultaneously
- **Attendance Reports**: Export attendance data to CSV/PDF
- **Email Notifications**: Alert administrators of attendance events
- **Mobile App**: Native mobile application
- **Cloud Integration**: Optional cloud backup and sync

### **Integration Possibilities**
- **ERP Systems**: Integration with existing business systems
- **Payroll Systems**: Automatic wage calculation based on attendance
- **Access Control**: Door access based on attendance status
- **Analytics**: Attendance patterns and insights

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 📞 Support

For support or questions, please open an issue in the GitHub repository.

## 🔗 Repository Information

- **GitHub Repository**: https://github.com/boazomare1/WorkforceManagement
- **Clone URL**: `https://github.com/boazomare1/WorkforceManagement.git`
- **License**: MIT License
- **Language**: Python
- **Framework**: Flask

---

**Built with ❤️ using Python, Flask, OpenCV, and modern web technologies** 