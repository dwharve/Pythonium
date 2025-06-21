"""
Web API module with additional security vulnerabilities.
These should be detected by the security smell detector.
"""

import os
import hashlib
import base64
import pickle
import subprocess
from .database import get_database_config


# More hardcoded secrets
GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
SLACK_WEBHOOK = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
TWILIO_SID = "AC1234567890abcdef1234567890abcdef"
TWILIO_TOKEN = "auth_token_1234567890abcdef"


class APIHandler:
    """API handler with security vulnerabilities"""
    
    def __init__(self):
        # Hardcoded API keys
        self.api_keys = {
            'sendgrid': 'SG.1234567890abcdef.1234567890abcdef',
            'mailgun': 'key-1234567890abcdef1234567890abcdef',
            'openai': 'sk-1234567890abcdefghijklmnopqrstuvwxyz'
        }
        self.webhook_secret = "webhook_secret_hardcoded_123"
    
    def process_user_input(self, user_data):
        """Process user input with security issues"""
        # Command injection vulnerability
        if 'command' in user_data:
            result = os.system(f"echo {user_data['command']}")
            return result
        
        # Deserialization vulnerability
        if 'serialized_data' in user_data:
            data = base64.b64decode(user_data['serialized_data'])
            return pickle.loads(data)  # Unsafe deserialization
    
    def execute_shell_command(self, command):
        """Execute shell command - command injection risk"""
        # Vulnerable to command injection
        result = subprocess.run(
            f"bash -c '{command}'",
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout
    
    def generate_temp_file(self, content):
        """Generate temp file with predictable name"""
        # Predictable temp file names - security risk
        temp_filename = f"/tmp/temp_{hashlib.md5(content.encode()).hexdigest()[:8]}"
        with open(temp_filename, 'w') as f:
            f.write(content)
        return temp_filename
    
    def validate_token(self, token):
        """Validate token with weak comparison"""
        # Hardcoded valid tokens
        valid_tokens = [
            "token_12345",
            "secret_abcdef",
            "api_key_xyz789"
        ]
        # Timing attack vulnerability - should use secure comparison
        return token in valid_tokens


class AuthenticationService:
    """Authentication service with security issues"""
    
    def __init__(self):
        # Weak encryption key
        self.encryption_key = "1234567890123456"  # Too simple
        self.salt = "fixed_salt"  # Fixed salt is insecure
    
    def hash_password(self, password):
        """Hash password with weak method"""
        # MD5 is cryptographically broken
        return hashlib.md5(password.encode()).hexdigest()
    
    def encrypt_data(self, data):
        """Encrypt data with weak method"""
        # Simple XOR encryption - very weak
        key = self.encryption_key.encode()
        encrypted = bytearray()
        for i, byte in enumerate(data.encode()):
            encrypted.append(byte ^ key[i % len(key)])
        return base64.b64encode(encrypted).decode()
    
    def generate_session_token(self):
        """Generate session token with poor randomness"""
        import random
        # Poor randomness for security-critical operation
        return f"session_{random.randint(1000, 9999)}"
    
    def check_admin_access(self, user_id, password):
        """Check admin access with hardcoded credentials"""
        # Multiple hardcoded admin accounts
        admin_accounts = {
            'admin': 'password',
            'root': 'toor',
            'administrator': 'admin123',
            'superuser': 'super123'
        }
        return admin_accounts.get(user_id) == password


def create_jwt_token(user_id):
    """Create JWT token with hardcoded secret"""
    import json
    
    # Hardcoded JWT secret
    jwt_secret = "jwt_signing_secret_123456"
    
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"user_id": user_id, "exp": "never"}
    
    # Weak JWT implementation
    header_b64 = base64.b64encode(json.dumps(header).encode()).decode()
    payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
    signature = hashlib.md5(f"{header_b64}.{payload_b64}.{jwt_secret}".encode()).hexdigest()
    
    return f"{header_b64}.{payload_b64}.{signature}"


def send_notification(message, webhook_url=None):
    """Send notification with hardcoded webhook"""
    if not webhook_url:
        # Hardcoded webhook URL
        webhook_url = "https://hooks.slack.com/services/HARDCODED/WEBHOOK/URL"
    
    # Potential SSRF if webhook_url comes from user input
    import urllib.request
    data = f'{{"text": "{message}"}}'.encode()
    req = urllib.request.Request(webhook_url, data=data)
    urllib.request.urlopen(req)


# Configuration with embedded secrets
CONFIG = {
    'database': get_database_config(),
    'redis_url': 'redis://:password123@localhost:6379/0',
    'elasticsearch_url': 'http://elastic:changeme@localhost:9200',
    'mongodb_uri': 'mongodb://admin:password@localhost:27017/mydb'
}
