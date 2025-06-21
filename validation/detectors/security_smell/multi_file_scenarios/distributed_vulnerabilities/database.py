"""
Database module with security vulnerabilities.
These should be detected by the security smell detector.
"""

import sqlite3
import mysql.connector
import os


# Hardcoded credentials - security vulnerability
DB_USER = "admin"
DB_PASSWORD = "password123"
DB_HOST = "localhost"
API_KEY = "sk-1234567890abcdef"
SECRET_TOKEN = "secret_token_hardcoded"


class DatabaseConnection:
    """Database connection with security issues"""
    
    def __init__(self):
        # Hardcoded connection string
        self.connection_string = f"mysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/mydb"
        self.api_key = API_KEY
    
    def connect(self):
        """Connect to database with hardcoded credentials"""
        try:
            # SQL injection vulnerability
            connection = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,  # Hardcoded password
                database="production_db"
            )
            return connection
        except Exception as e:
            print(f"Connection failed: {e}")
            return None
    
    def execute_query(self, user_input):
        """Execute query with SQL injection vulnerability"""
        connection = self.connect()
        if connection:
            cursor = connection.cursor()
            # Direct string interpolation - SQL injection risk
            query = f"SELECT * FROM users WHERE name = '{user_input}'"
            cursor.execute(query)
            return cursor.fetchall()
    
    def authenticate_user(self, username, password):
        """Authenticate user with weak security"""
        # Hardcoded admin credentials
        if username == "admin" and password == "admin123":
            return True
        
        # SQL injection vulnerability
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        connection = self.connect()
        if connection:
            cursor = connection.cursor()
            cursor.execute(query)
            return len(cursor.fetchall()) > 0
        return False


def get_database_config():
    """Get database config with hardcoded values"""
    return {
        'host': 'prod-server.company.com',
        'username': 'prod_user',
        'password': 'Prod123!@#',  # Hardcoded production password
        'database': 'production',
        'api_secret': 'sk-live-abcdef123456789'  # Hardcoded API secret
    }


def create_backup_script():
    """Create backup script with embedded credentials"""
    script = """
    #!/bin/bash
    export DB_USER="backup_user"
    export DB_PASS="BackupPass2023!"
    mysqldump -u $DB_USER -p$DB_PASS production_db > backup.sql
    """
    return script


class ConfigManager:
    """Configuration manager with security issues"""
    
    def __init__(self):
        # Hardcoded encryption key
        self.encryption_key = "super_secret_key_123"
        self.jwt_secret = "jwt_secret_hardcoded_value"
    
    def get_api_credentials(self):
        """Return API credentials"""
        return {
            'key': 'live_key_abcdef123',
            'secret': 'live_secret_xyz789',
            'webhook_secret': 'whsec_hardcoded_webhook_secret'
        }
    
    def get_oauth_config(self):
        """Get OAuth configuration"""
        return {
            'client_id': 'oauth_client_12345',
            'client_secret': 'oauth_secret_abcdef67890',  # Hardcoded OAuth secret
            'redirect_uri': 'https://app.example.com/callback'
        }


# More hardcoded credentials
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
STRIPE_SECRET_KEY = "sk_live_1234567890abcdef1234567890abcdef"
