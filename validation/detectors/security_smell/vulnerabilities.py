"""
Security Smell Detector Validation - True Positives

This module contains code patterns that represent genuine security vulnerabilities
and should be detected by the security smell detector.
"""

import os
import subprocess
import pickle
import hashlib

# =============================================================================
# SQL INJECTION VULNERABILITIES
# =============================================================================

def unsafe_sql_query(user_input):
    """Function with SQL injection vulnerability."""
    import sqlite3
    
    # DANGEROUS: Direct string interpolation in SQL
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(query)  # Vulnerable to SQL injection
    return cursor.fetchall()

def unsafe_sql_format(username, password):
    """Another SQL injection vulnerability using format."""
    import sqlite3
    
    # DANGEROUS: Using % formatting in SQL
    query = "SELECT * FROM users WHERE username = '%s' AND password = '%s'" % (username, password)
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(query)  # Vulnerable to SQL injection
    return cursor.fetchone()

def unsafe_sql_concatenation(table_name, column):
    """SQL injection through string concatenation."""
    import sqlite3
    
    # DANGEROUS: Concatenating user input directly
    query = "SELECT " + column + " FROM " + table_name + " WHERE active = 1"
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(query)  # Vulnerable to SQL injection
    return cursor.fetchall()

# =============================================================================
# COMMAND INJECTION VULNERABILITIES
# =============================================================================

def unsafe_command_execution(filename):
    """Function with command injection vulnerability."""
    # DANGEROUS: Direct use of user input in shell command
    command = f"cat {filename}"
    result = os.system(command)  # Vulnerable to command injection
    return result

def unsafe_subprocess_call(user_command):
    """Command injection through subprocess."""
    # DANGEROUS: Using shell=True with user input
    result = subprocess.call(f"echo {user_command}", shell=True)
    return result

def unsafe_file_operations(path):
    """Unsafe file path operations."""
    # DANGEROUS: No path validation
    command = f"rm -rf {path}"
    os.system(command)  # Vulnerable to path traversal and command injection

# =============================================================================
# HARDCODED CREDENTIALS
# =============================================================================

def hardcoded_database_credentials():
    """Function with hardcoded database credentials."""
    # DANGEROUS: Hardcoded credentials
    username = "admin"
    password = "secret123"
    api_key = "sk-1234567890abcdef"
    
    connection_string = f"mysql:///{username}:{password}@localhost/mydb"
    return connection_string

def hardcoded_api_keys():
    """Function with hardcoded API keys."""
    # DANGEROUS: Hardcoded API keys
    aws_access_key = "AKIAIOSFODNN7EXAMPLE"
    aws_secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    github_token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    
    return {
        'aws_access': aws_access_key,
        'aws_secret': aws_secret_key,
        'github': github_token
    }

def hardcoded_encryption_key():
    """Function with hardcoded encryption key."""
    # DANGEROUS: Hardcoded encryption key
    encryption_key = "supersecretkey123"
    salt = "fixedsalt456"
    
    return encryption_key, salt

# =============================================================================
# INSECURE CRYPTOGRAPHY
# =============================================================================

def weak_password_hashing(password):
    """Function using weak password hashing."""
    import hashlib
    
    # DANGEROUS: MD5 is cryptographically broken
    hash_md5 = hashlib.md5(password.encode()).hexdigest()
    
    # DANGEROUS: SHA1 is also weak
    hash_sha1 = hashlib.sha1(password.encode()).hexdigest()
    
    # DANGEROUS: No salt
    hash_no_salt = hashlib.sha256(password.encode()).hexdigest()
    
    return hash_md5

def insecure_random_generation():
    """Function using insecure random number generation."""
    import random
    
    # DANGEROUS: Using predictable random for security purposes
    session_id = random.randint(1000000, 9999999)
    token = str(random.random())
    
    return session_id, token

def weak_encryption():
    """Function with weak encryption implementation."""
    # DANGEROUS: Weak encryption algorithm
    def caesar_cipher(text, shift):
        result = ""
        for char in text:
            if char.isalpha():
                ascii_offset = 65 if char.isupper() else 97
                result += chr((ord(char) - ascii_offset + shift) % 26 + ascii_offset)
            else:
                result += char
        return result
    
    # Using weak encryption for sensitive data
    sensitive_data = "credit_card_number_1234567890123456"
    encrypted = caesar_cipher(sensitive_data, 3)
    return encrypted

# =============================================================================
# INSECURE DESERIALIZATION
# =============================================================================

def unsafe_pickle_deserialization(data):
    """Function with unsafe pickle deserialization."""
    # DANGEROUS: Deserializing untrusted data
    obj = pickle.loads(data)  # Can execute arbitrary code
    return obj

def unsafe_eval_usage(user_input):
    """Function using eval with user input."""
    # DANGEROUS: eval can execute arbitrary code
    result = eval(user_input)
    return result

def unsafe_exec_usage(code_string):
    """Function using exec with user input."""
    # DANGEROUS: exec can execute arbitrary code
    exec(code_string)

# =============================================================================
# INSECURE FILE HANDLING
# =============================================================================

def insecure_file_upload(filename, content):
    """Function with insecure file upload handling."""
    # DANGEROUS: No validation of file type or path
    with open(f"/uploads/{filename}", "wb") as f:
        f.write(content)

def insecure_file_access(filepath):
    """Function with path traversal vulnerability."""
    # DANGEROUS: No path validation
    with open(f"/data/{filepath}", "r") as f:
        return f.read()

def insecure_temp_file():
    """Function creating insecure temporary files."""
    import tempfile
    
    # DANGEROUS: Predictable temp file names
    temp_filename = "/tmp/myapp_temp_123.txt"
    with open(temp_filename, "w") as f:
        f.write("sensitive data")
    
    return temp_filename

# =============================================================================
# INSECURE NETWORK OPERATIONS
# =============================================================================

def insecure_ssl_context():
    """Function with insecure SSL configuration."""
    import ssl
    import urllib.request
    
    # DANGEROUS: Disabled SSL verification
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    return context

def insecure_http_requests():
    """Function making insecure HTTP requests."""
    import urllib.request
    
    # DANGEROUS: Using HTTP instead of HTTPS for sensitive data
    url = "http://api.example.com/sensitive-endpoint"
    response = urllib.request.urlopen(url)
    return response.read()

# =============================================================================
# INFORMATION DISCLOSURE
# =============================================================================

def information_disclosure_error_handling():
    """Function that discloses sensitive information in errors."""
    try:
        # Some operation that might fail
        result = 1 / 0
    except Exception as e:
        # DANGEROUS: Exposing internal details
        error_message = f"Database connection failed: username=admin, host=internal-db.company.com, error={str(e)}"
        print(error_message)
        return error_message

def debug_information_exposure():
    """Function that exposes debug information."""
    import traceback
    
    try:
        # Some operation that will fail
        result = 1 / 0  # This will raise ZeroDivisionError
    except Exception as e:
        # DANGEROUS: Exposing full stack traces to users
        full_traceback = traceback.format_exc()
        return full_traceback

# =============================================================================
# WEAK SESSION MANAGEMENT
# =============================================================================

def weak_session_management():
    """Function with weak session management."""
    import time
    
    # DANGEROUS: Predictable session IDs
    user_id = 12345
    timestamp = int(time.time())
    session_id = f"{user_id}_{timestamp}"
    
    return session_id

def insecure_cookie_settings():
    """Function with insecure cookie configuration."""
    # DANGEROUS: Missing security flags
    cookie = {
        'name': 'session_id',
        'value': 'abc123',
        'secure': False,      # Should be True for HTTPS
        'httponly': False,    # Should be True to prevent XSS
        'samesite': None      # Should be set to prevent CSRF
    }
    
    return cookie

# =============================================================================
# INPUT VALIDATION ISSUES
# =============================================================================

def insufficient_input_validation(email):
    """Function with insufficient input validation."""
    # DANGEROUS: Weak email validation
    if "@" in email:
        return True
    return False

def no_length_validation(user_input):
    """Function without length validation."""
    # DANGEROUS: No length limits
    buffer = user_input * 1000  # Could cause memory issues
    return buffer

def regex_dos_vulnerability(pattern, text):
    """Function vulnerable to ReDoS attack."""
    import re
    
    # DANGEROUS: Potentially catastrophic backtracking
    regex = re.compile(r"(a+)+b")
    match = regex.match(text)
    return match

# =============================================================================
# AUTHENTICATION BYPASS
# =============================================================================

def weak_authentication_check(username, password):
    """Function with weak authentication logic."""
    # DANGEROUS: Easily bypassed authentication
    if username == "admin" or password == "password":
        return True
    
    # DANGEROUS: Using == for string comparison (timing attack)
    stored_password = "secret123"
    if password == stored_password:
        return True
    
    return False

def timing_attack_vulnerability(user_token, valid_token):
    """Function vulnerable to timing attacks."""
    # DANGEROUS: String comparison vulnerable to timing attacks
    if user_token == valid_token:
        return True
    return False
