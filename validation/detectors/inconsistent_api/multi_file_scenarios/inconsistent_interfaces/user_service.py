"""
Data repository with inconsistent API patterns across multiple files.
This should be detected by the inconsistent API detector.
"""


class UserRepository:
    """User repository with one API pattern"""
    
    def get_user(self, user_id):
        """Get user by ID - returns user object"""
        return {'id': user_id, 'name': f'User {user_id}'}
    
    def create_user(self, name, email):
        """Create user - takes individual parameters"""
        return {'id': 123, 'name': name, 'email': email}
    
    def update_user(self, user_id, name, email):
        """Update user - takes individual parameters"""
        return {'id': user_id, 'name': name, 'email': email}
    
    def delete_user(self, user_id):
        """Delete user - returns boolean"""
        return True
    
    def list_users(self, page=1, size=10):
        """List users with pagination"""
        return [
            {'id': i, 'name': f'User {i}'} 
            for i in range((page-1)*size, page*size)
        ]


class UserManager:
    """User manager with different API patterns"""
    
    def find_user_by_id(self, id):
        """Find user - different method name, different parameter name"""
        return {'user_id': id, 'username': f'User {id}'}
    
    def add_new_user(self, user_data):
        """Add user - takes dict parameter instead of individual params"""
        return {'user_id': 456, **user_data}
    
    def modify_user(self, id, user_data):
        """Modify user - different name, mixed parameter style"""
        return {'user_id': id, **user_data}
    
    def remove_user(self, id):
        """Remove user - returns None instead of boolean"""
        return None
    
    def get_all_users(self, offset=0, limit=10):
        """Get all users - different parameter names for pagination"""
        return [
            {'user_id': i, 'username': f'User {i}'} 
            for i in range(offset, offset + limit)
        ]


def create_user_v1(name, email, age):
    """Version 1 of user creation - individual parameters"""
    return {
        'id': 1,
        'name': name,
        'email': email,
        'age': age,
        'created': 'now'
    }


def create_user_v2(user_info):
    """Version 2 of user creation - dict parameter"""
    return {
        'user_id': 2,
        'full_name': user_info['name'],
        'email_address': user_info['email'],
        'user_age': user_info['age'],
        'creation_time': 'now'
    }


def validate_user_input(name, email):
    """Validation function - returns boolean"""
    return bool(name and email and '@' in email)


def check_user_data(user_data):
    """Similar validation - different name, returns dict"""
    is_valid = bool(
        user_data.get('name') and 
        user_data.get('email') and 
        '@' in user_data.get('email', '')
    )
    return {'valid': is_valid, 'errors': [] if is_valid else ['Invalid data']}
