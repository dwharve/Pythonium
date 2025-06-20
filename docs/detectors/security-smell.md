# Security Smell Detector

The Security Smell Detector identifies potential security vulnerabilities and anti-patterns in Python code, helping prevent security issues before they reach production.

## What it Detects

- Hard-coded credentials and secrets
- SQL injection vulnerabilities
- Unsafe use of `eval()` and `exec()`
- Weak cryptographic practices
- Insecure file operations
- Command injection risks
- Unsafe deserialization patterns
- Missing input validation

## When to Use

- **Pre-deployment security reviews**: Essential before production releases
- **Code reviews**: Catch security issues early in development
- **Legacy code audits**: Identify security debt in existing codebases
- **Compliance preparation**: Meet security standards and regulations

## Configuration Options

```yaml
detectors:
  security_smell:
    # Confidence threshold for reported issues
    confidence_threshold: 0.7
    
    # Enable specific security checks
    check_hardcoded_secrets: true
    check_sql_injection: true
    check_command_injection: true
    check_unsafe_eval: true
    check_weak_crypto: true
    check_file_operations: true
    
    # Patterns for secrets detection
    secret_patterns:
      - "password\\s*=\\s*['\"][^'\"]+['\"]"
      - "api_key\\s*=\\s*['\"][^'\"]+['\"]"
      - "secret\\s*=\\s*['\"][^'\"]+['\"]"
    
    # Exclude test files from some checks
    exclude_test_files: true
```

## Example Output

```
[ERROR] Security Smell: Hard-coded password detected
  File: src/config.py:12
  Line: PASSWORD = "admin123"
  Risk: Credentials should be stored in environment variables
  
[ERROR] Security Smell: Potential SQL injection vulnerability
  File: src/database.py:45
  Line: cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
  Risk: Use parameterized queries to prevent SQL injection
  
[WARN] Security Smell: Unsafe use of eval()
  File: src/processor.py:78
  Line: result = eval(user_input)
  Risk: eval() can execute arbitrary code, use ast.literal_eval() instead
```

## Common Vulnerabilities Detected

### Hard-coded Credentials
```python
# Detected security smell
DATABASE_PASSWORD = "secret123"  # Hard-coded password
API_KEY = "sk-1234567890abcdef"  # Hard-coded API key

# Better approach
import os
DATABASE_PASSWORD = os.getenv("DB_PASSWORD")
API_KEY = os.getenv("API_KEY")
```

### SQL Injection
```python
# Vulnerable to SQL injection
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # Detected
    cursor.execute(query)
    return cursor.fetchone()

# Safe parameterized query
def get_user(user_id):
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_id,))
    return cursor.fetchone()
```

### Unsafe Evaluation
```python
# Dangerous use of eval
def calculate(expression):
    return eval(expression)  # Detected security smell

# Safer alternatives
import ast
def calculate(expression):
    # For simple expressions
    return ast.literal_eval(expression)

# Or for math expressions
import operator
import ast

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

def safe_eval(node):
    if isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.BinOp):
        return OPERATORS[type(node.op)](
            safe_eval(node.left), 
            safe_eval(node.right)
        )
    else:
        raise TypeError(node)

def calculate(expression):
    tree = ast.parse(expression, mode='eval')
    return safe_eval(tree.body)
```

### Command Injection
```python
# Vulnerable to command injection
import os
def backup_file(filename):
    os.system(f"cp {filename} backup/")  # Detected security smell

# Safer approach
import subprocess
def backup_file(filename):
    subprocess.run(["cp", filename, "backup/"], check=True)
```

### Weak Cryptography
```python
# Weak hashing algorithm
import hashlib
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()  # Detected

# Strong password hashing
import bcrypt
def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)
```

### Insecure File Operations
```python
# Unsafe file operations
def read_config(filename):
    # Path traversal vulnerability
    with open(f"configs/{filename}") as f:  # Detected if filename is user input
        return f.read()

# Secure file operations
import os
def read_config(filename):
    # Validate and sanitize filename
    if ".." in filename or "/" in filename:
        raise ValueError("Invalid filename")
    
    safe_path = os.path.join("configs", filename)
    if not safe_path.startswith("/safe/config/path"):
        raise ValueError("File outside allowed directory")
    
    with open(safe_path) as f:
        return f.read()
```

### Unsafe Deserialization
```python
# Dangerous pickle usage
import pickle
def load_data(serialized_data):
    return pickle.loads(serialized_data)  # Detected security smell

# Safer alternatives
import json
def load_data(json_data):
    return json.loads(json_data)  # Only for trusted data

# Or use safe serialization libraries
import msgpack
def load_data(data):
    return msgpack.unpackb(data)
```

## Security Best Practices

### Environment Variables for Secrets
```python
# Instead of hard-coding
DATABASE_URL = "postgresql://user:pass@localhost/db"

# Use environment variables
import os
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")
```

### Input Validation
```python
# Always validate user input
def process_user_id(user_id_str):
    try:
        user_id = int(user_id_str)
        if user_id <= 0:
            raise ValueError("User ID must be positive")
        return user_id
    except ValueError:
        raise ValueError("Invalid user ID format")
```

### Secure File Handling
```python
import os
import tempfile

def secure_file_upload(uploaded_file, allowed_extensions):
    # Validate file extension
    if not any(uploaded_file.filename.endswith(ext) for ext in allowed_extensions):
        raise ValueError("File type not allowed")
    
    # Use temporary file with secure permissions
    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_file:
        temp_file.write(uploaded_file.read())
        os.chmod(temp_file.name, 0o600)  # Owner read/write only
        return temp_file.name
```

## Integration Examples

### Command Line
```bash
# Security-focused analysis
pythonium crawl --detectors security_smell src/

# High-confidence security issues only
pythonium crawl --detectors security_smell --config security_smell.confidence_threshold=0.9 src/

# Focus on specific security checks
pythonium crawl --detectors security_smell --config security_smell.check_hardcoded_secrets=true src/
```

### Python API
```python
from pythonium import analyze_code

# Security audit configuration
security_config = {
    "security_smell": {
        "confidence_threshold": 0.8,
        "check_hardcoded_secrets": True,
        "check_sql_injection": True,
        "check_command_injection": True,
        "exclude_test_files": False  # Include tests in security review
    }
}

results = analyze_code(
    path="src/",
    detectors=["security_smell"],
    config=security_config
)

# Categorize security issues by severity
critical_issues = []
high_issues = []
medium_issues = []

for issue in results.get_issues("security_smell"):
    if "injection" in issue.description.lower():
        critical_issues.append(issue)
    elif "hard-coded" in issue.description.lower():
        high_issues.append(issue)
    else:
        medium_issues.append(issue)

print(f"Critical security issues: {len(critical_issues)}")
print(f"High priority issues: {len(high_issues)}")
print(f"Medium priority issues: {len(medium_issues)}")
```

### CI/CD Integration
```yaml
# .github/workflows/security.yml
name: Security Analysis
on: [push, pull_request]

jobs:
  security_scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install Pythonium
        run: pip install pythonium
      - name: Security Analysis
        run: |
          pythonium crawl --detectors security_smell --output json --file security-report.json src/
          # Fail if critical security issues found
          if grep -q '"severity": "ERROR"' security-report.json; then
            echo "Critical security issues found!"
            exit 1
          fi
```

## Related Detectors

- **Deprecated API**: Old APIs may have known security vulnerabilities
- **Dead Code**: Unused code with security issues still poses risks
- **Inconsistent API**: Inconsistent security patterns across the codebase

## Troubleshooting

**Too many false positives?**
- Increase `confidence_threshold`
- Enable `exclude_test_files` if test code triggers false positives
- Customize `secret_patterns` for your specific context

**Missing known vulnerabilities?**
- Lower `confidence_threshold`
- Enable all security checks
- Verify the detector supports the specific vulnerability type

**Performance issues?**
- Disable specific checks you don't need
- Use higher confidence thresholds
- Analyze smaller code sections incrementally

## Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Guide](https://python-security.readthedocs.io/)
- [Bandit Security Linter](https://bandit.readthedocs.io/)
- [PyCQA Security Guidelines](https://github.com/PyCQA)
