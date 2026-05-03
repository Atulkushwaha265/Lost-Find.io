"""
Security utilities and middleware for the Lost and Found Portal
"""

import re
from functools import wraps
from flask import request, jsonify, session, abort
from flask_login import current_user
from werkzeug.security import check_password_hash
import time
from datetime import datetime, timedelta

class SecurityMiddleware:
    """Security middleware for Flask application"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Security checks before each request"""
        # Rate limiting
        if not self.check_rate_limit():
            abort(429, description="Rate limit exceeded")
        
        # Security headers
        self.set_security_headers()
        
        # Input validation
        self.validate_input()
    
    def after_request(self, response):
        """Security headers after each request"""
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdnjs.cloudflare.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        
        return response
    
    def check_rate_limit(self):
        """Simple rate limiting based on IP"""
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Get current requests from session
        requests = session.get('requests', [])
        now = time.time()
        
        # Remove old requests (older than 1 minute)
        requests = [req_time for req_time in requests if now - req_time < 60]
        
        # Check if exceeded limit (100 requests per minute)
        if len(requests) > 100:
            return False
        
        # Add current request
        requests.append(now)
        session['requests'] = requests
        
        return True
    
    def set_security_headers(self):
        """Set security headers for the request"""
        pass  # Headers are set in after_request
    
    def validate_input(self):
        """Validate input for common attacks"""
        # Check for SQL injection patterns
        sql_patterns = [
            r'(\bUNION\b.*\bSELECT\b)',
            r'(\bSELECT\b.*\bFROM\b)',
            r'(\bINSERT\b.*\bINTO\b)',
            r'(\bUPDATE\b.*\bSET\b)',
            r'(\bDELETE\b.*\bFROM\b)',
            r'(\bDROP\b.*\bTABLE\b)',
            r'(\bCREATE\b.*\bTABLE\b)',
            r'(\bALTER\b.*\bTABLE\b)',
            r'(--|#|/\*|\*/)',
            r'(\bOR\b.*\b1\s*=\s*1\b)',
            r'(\bAND\b.*\b1\s*=\s*1\b)'
        ]
        
        # Check for XSS patterns
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'eval\s*\(',
            r'expression\s*\('
        ]
        
        # Validate form data and query parameters
        all_input = []
        
        # Add query parameters
        for key, value in request.args.items():
            all_input.append(str(value))
        
        # Add form data
        if request.form:
            for key, value in request.form.items():
                all_input.append(str(value))
        
        # Add JSON data
        if request.is_json:
            try:
                json_data = request.get_json()
                if json_data:
                    for key, value in json_data.items():
                        all_input.append(str(value))
            except:
                pass
        
        # Check for malicious patterns
        for input_value in all_input:
            # Check SQL injection
            for pattern in sql_patterns:
                if re.search(pattern, input_value, re.IGNORECASE):
                    abort(400, description="Invalid input detected")
            
            # Check XSS
            for pattern in xss_patterns:
                if re.search(pattern, input_value, re.IGNORECASE):
                    abort(400, description="Invalid input detected")

def rate_limit(max_requests=100, per_seconds=60):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            
            # Simple in-memory rate limiting (in production, use Redis)
            if not hasattr(decorated_function, 'rate_limits'):
                decorated_function.rate_limits = {}
            
            now = time.time()
            if client_ip not in decorated_function.rate_limits:
                decorated_function.rate_limits[client_ip] = []
            
            # Clean old requests
            decorated_function.rate_limits[client_ip] = [
                req_time for req_time in decorated_function.rate_limits[client_ip]
                if now - req_time < per_seconds
            ]
            
            # Check limit
            if len(decorated_function.rate_limits[client_ip]) >= max_requests:
                abort(429, description="Rate limit exceeded")
            
            # Add current request
            decorated_function.rate_limits[client_ip].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validate phone number format"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    # Check if it's a valid phone number (10-15 digits)
    return len(digits) >= 10 and len(digits) <= 15

def sanitize_filename(filename):
    """Sanitize uploaded file names"""
    # Remove path separators
    filename = filename.replace('/', '').replace('\\', '')
    # Remove dangerous characters
    filename = re.sub(r'[<>:"|?*]', '', filename)
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    return filename

def validate_image_file(file):
    """Validate uploaded image files"""
    if not file:
        return False, "No file provided"
    
    # Check file extension
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    if not ('.' in file.filename and 
            file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return False, "Invalid file type"
    
    # Check file size (16MB max)
    if len(file.read()) > 16 * 1024 * 1024:
        file.seek(0)
        return False, "File too large"
    
    file.seek(0)
    
    # Check file signature (magic numbers)
    file_header = file.read(10)
    file.seek(0)
    
    # Check for common image signatures
    image_signatures = {
        b'\x89PNG\r\n\x1a\n': 'PNG',
        b'\xff\xd8\xff': 'JPEG',
        b'GIF87a': 'GIF',
        b'GIF89a': 'GIF',
        b'RIFF': 'WEBP',  # WEBP files start with RIFF
    }
    
    valid_image = False
    for signature, format_name in image_signatures.items():
        if file_header.startswith(signature):
            valid_image = True
            break
    
    if not valid_image:
        return False, "Invalid image file"
    
    return True, "Valid image file"

def log_security_event(event_type, description, ip_address=None, user_id=None):
    """Log security events for auditing"""
    timestamp = datetime.utcnow()
    
    # In production, this should go to a secure logging system
    log_entry = {
        'timestamp': timestamp.isoformat(),
        'event_type': event_type,
        'description': description,
        'ip_address': ip_address or request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'user_id': user_id
    }
    
    # For now, just print to console (in production, use proper logging)
    print(f"SECURITY LOG: {log_entry}")

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            log_security_event('UNAUTHORIZED_ACCESS', 
                              f"Attempted to access admin route: {request.endpoint}")
            abort(401)
        
        if not current_user.is_admin():
            log_security_event('ADMIN_ACCESS_DENIED', 
                              f"User {current_user.id} attempted to access admin route: {request.endpoint}",
                              user_id=current_user.id)
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def validate_csrf_token():
    """Validate CSRF token for API requests"""
    if request.method in ['POST', 'PUT', 'DELETE']:
        if not request.headers.get('X-CSRF-Token'):
            abort(400, description="CSRF token missing")
        
        # In a real implementation, validate against session token
        # For now, just check if it exists
        return True
    
    return True

def check_session_integrity():
    """Check if session is valid and not tampered"""
    if 'user_id' in session:
        # Check if session is too old (24 hours)
        if 'session_start' in session:
            session_age = datetime.utcnow() - datetime.fromisoformat(session['session_start'])
            if session_age > timedelta(hours=24):
                session.clear()
                return False
        
        # Check IP address consistency
        if 'client_ip' in session:
            current_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            if session['client_ip'] != current_ip:
                log_security_event('SESSION_HIJACK_ATTEMPT', 
                                  f"IP address changed for user {session['user_id']}")
                session.clear()
                return False
    
    return True

def setup_session_security():
    """Setup secure session settings"""
    if 'session_start' not in session and current_user.is_authenticated:
        session['session_start'] = datetime.utcnow().isoformat()
        session['client_ip'] = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        session.permanent = True  # Make session permanent
