import json
import os
from datetime import datetime

class SettingsManager:
    """Manages dynamic system settings"""
    
    def __init__(self, settings_file='system_settings.json'):
        self.settings_file = settings_file
        self.default_settings = {
            # Face Recognition Settings
            'face_tolerance': 0.6,
            'face_detection_cooldown': 30,  # seconds
            'minimum_work_hours': 1.0,
            'instant_mode': True,
            
            # System Settings
            'max_face_encodings': 1000,
            'auto_backup_enabled': True,
            'auto_backup_interval': 24,  # hours
            
            # Attendance Rules
            'allow_early_checkout': False,
            'overtime_threshold': 8.0,  # hours
            'late_arrival_threshold': 15,  # minutes
            'grace_period': 5,  # minutes
            
            # Notifications
            'email_notifications': False,
            'sms_notifications': False,
            'admin_email': '',
            'notification_types': {
                'late_arrival': True,
                'early_departure': True,
                'overtime': True,
                'no_show': True
            },
            
            # Security
            'admin_password_hash': '',  # Will be set separately
            'session_timeout': 30,  # minutes
            'max_login_attempts': 3,
            'lockout_duration': 15,  # minutes
            
            # Performance
            'camera_fps': 30,
            'processing_threads': 2,
            'face_detection_scale': 0.25,  # Scale down for faster processing
            
            # Reporting
            'default_report_period': 30,  # days
            'auto_generate_reports': False,
            'report_formats': ['pdf', 'csv', 'excel'],
            
            # System Info
            'system_name': 'Face Recognition Attendance System',
            'company_name': 'Your Company',
            'timezone': 'UTC',
            'date_format': '%Y-%m-%d',
            'time_format': '%H:%M:%S',
            
            # Advanced
            'debug_mode': False,
            'log_level': 'INFO',
            'backup_retention_days': 30,
            'database_cleanup_days': 90
        }
        self.settings = self.load_settings()
        
    def load_settings(self):
        """Load settings from file or create default"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                settings = self.default_settings.copy()
                settings.update(loaded_settings)
                return settings
            except Exception as e:
                print(f"Error loading settings: {e}")
                return self.default_settings.copy()
        else:
            # Create default settings file
            self.save_settings(self.default_settings)
            return self.default_settings.copy()
    
    def save_settings(self, settings=None):
        """Save settings to file"""
        if settings is None:
            settings = self.settings
        
        try:
            # Add metadata
            settings['last_updated'] = datetime.now().isoformat()
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Set a setting value"""
        self.settings[key] = value
        return self.save_settings()
    
    def update(self, new_settings):
        """Update multiple settings"""
        self.settings.update(new_settings)
        return self.save_settings()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self.default_settings.copy()
        return self.save_settings()
    
    def get_all(self):
        """Get all settings"""
        return self.settings.copy()
    
    def export_settings(self, filepath):
        """Export settings to a file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.settings, f, indent=4)
            return True
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, filepath):
        """Import settings from a file"""
        try:
            with open(filepath, 'r') as f:
                imported_settings = json.load(f)
            
            # Validate imported settings
            valid_settings = {}
            for key, value in imported_settings.items():
                if key in self.default_settings:
                    valid_settings[key] = value
            
            self.settings.update(valid_settings)
            return self.save_settings()
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False
    
    def validate_setting(self, key, value):
        """Validate a setting value"""
        validators = {
            'face_tolerance': lambda x: 0.1 <= float(x) <= 1.0,
            'face_detection_cooldown': lambda x: 0 <= int(x) <= 300,
            'minimum_work_hours': lambda x: 0.1 <= float(x) <= 24.0,
            'overtime_threshold': lambda x: 1.0 <= float(x) <= 24.0,
            'late_arrival_threshold': lambda x: 1 <= int(x) <= 120,
            'grace_period': lambda x: 0 <= int(x) <= 60,
            'session_timeout': lambda x: 5 <= int(x) <= 480,
            'max_login_attempts': lambda x: 1 <= int(x) <= 10,
            'lockout_duration': lambda x: 1 <= int(x) <= 60,
            'camera_fps': lambda x: 1 <= int(x) <= 60,
            'processing_threads': lambda x: 1 <= int(x) <= 8,
            'face_detection_scale': lambda x: 0.1 <= float(x) <= 1.0,
            'backup_retention_days': lambda x: 1 <= int(x) <= 365,
            'database_cleanup_days': lambda x: 1 <= int(x) <= 365
        }
        
        if key in validators:
            try:
                return validators[key](value)
            except:
                return False
        return True
    
    def get_setting_info(self, key):
        """Get information about a setting"""
        info = {
            'face_tolerance': {
                'description': 'Face recognition sensitivity (lower = stricter)',
                'type': 'float',
                'min': 0.1,
                'max': 1.0,
                'category': 'Face Recognition'
            },
            'face_detection_cooldown': {
                'description': 'Seconds between face detections for same user',
                'type': 'int',
                'min': 0,
                'max': 300,
                'category': 'Face Recognition'
            },
            'minimum_work_hours': {
                'description': 'Minimum hours before allowing checkout',
                'type': 'float',
                'min': 0.1,
                'max': 24.0,
                'category': 'Attendance Rules'
            },
            'instant_mode': {
                'description': 'Enable instant check-in/out without confirmation',
                'type': 'bool',
                'category': 'Face Recognition'
            },
            'overtime_threshold': {
                'description': 'Hours after which overtime is triggered',
                'type': 'float',
                'min': 1.0,
                'max': 24.0,
                'category': 'Attendance Rules'
            },
            'late_arrival_threshold': {
                'description': 'Minutes late before flagging as late arrival',
                'type': 'int',
                'min': 1,
                'max': 120,
                'category': 'Attendance Rules'
            }
        }
        return info.get(key, {'description': 'Setting', 'type': 'str', 'category': 'General'})