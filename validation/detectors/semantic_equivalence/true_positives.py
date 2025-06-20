"""
True positive cases for semantic equivalence detector.
These contain semantically equivalent code blocks that should be detected.
"""

# Case 1: Equivalent mathematical operations
def calculate_area_v1(width, height):
    """First version of area calculation"""
    return width * height

def calculate_area_v2(w, h):
    """Semantically equivalent area calculation"""
    result = w * h
    return result

def calculate_area_v3(length, breadth):
    """Another equivalent area calculation"""
    area = length * breadth
    return area

# Case 2: Equivalent list processing
def process_numbers_v1(numbers):
    """First version of number processing"""
    result = []
    for num in numbers:
        if num > 0:
            result.append(num * 2)
    return result

def process_numbers_v2(number_list):
    """Semantically equivalent processing"""
    output = []
    for n in number_list:
        if n > 0:
            doubled = n * 2
            output.append(doubled)
    return output

def process_numbers_v3(nums):
    """Another equivalent processing approach"""
    processed = []
    for value in nums:
        if value > 0:
            processed.append(value + value)  # Same as value * 2
    return processed

# Case 3: Equivalent string validation
def validate_email_v1(email):
    """First email validation"""
    if "@" in email and "." in email:
        return True
    return False

def validate_email_v2(email_address):
    """Semantically equivalent validation"""
    has_at = "@" in email_address
    has_dot = "." in email_address
    if has_at and has_dot:
        return True
    else:
        return False

def validate_email_v3(mail):
    """Another equivalent validation"""
    return "@" in mail and "." in mail

# Case 4: Equivalent data filtering
def filter_adults_v1(people):
    """First version of adult filtering"""
    adults = []
    for person in people:
        if person['age'] >= 18:
            adults.append(person)
    return adults

def filter_adults_v2(person_list):
    """Semantically equivalent filtering"""
    result = []
    for p in person_list:
        age = p['age']
        if age >= 18:
            result.append(p)
    return result

def filter_adults_v3(individuals):
    """Another equivalent filtering approach"""
    filtered = []
    for individual in individuals:
        if individual.get('age', 0) >= 18:
            filtered.append(individual)
    return filtered

# Case 5: Equivalent error handling
def safe_divide_v1(a, b):
    """First version of safe division"""
    try:
        return a / b
    except ZeroDivisionError:
        return None

def safe_divide_v2(numerator, denominator):
    """Semantically equivalent division"""
    try:
        result = numerator / denominator
        return result
    except ZeroDivisionError:
        return None

def safe_divide_v3(x, y):
    """Another equivalent division approach"""
    if y == 0:
        return None
    return x / y

# Case 6: Equivalent data transformation
def normalize_name_v1(name):
    """First version of name normalization"""
    trimmed = name.strip()
    return trimmed.title()

def normalize_name_v2(full_name):
    """Semantically equivalent normalization"""
    cleaned = full_name.strip()
    capitalized = cleaned.title()
    return capitalized

def normalize_name_v3(person_name):
    """Another equivalent normalization"""
    return person_name.strip().title()

# Case 7: Equivalent search operations
def find_user_by_id_v1(users, user_id):
    """First version of user search"""
    for user in users:
        if user['id'] == user_id:
            return user
    return None

def find_user_by_id_v2(user_list, target_id):
    """Semantically equivalent search"""
    for u in user_list:
        if u['id'] == target_id:
            return u
    return None

def find_user_by_id_v3(all_users, search_id):
    """Another equivalent search approach"""
    found_user = None
    for current_user in all_users:
        if current_user['id'] == search_id:
            found_user = current_user
            break
    return found_user

# Case 8: Equivalent aggregation operations
def calculate_total_v1(items):
    """First version of total calculation"""
    total = 0
    for item in items:
        total += item['price']
    return total

def calculate_total_v2(item_list):
    """Semantically equivalent calculation"""
    sum_total = 0
    for i in item_list:
        sum_total = sum_total + i['price']
    return sum_total

def calculate_total_v3(products):
    """Another equivalent calculation"""
    result = 0
    for product in products:
        price = product['price']
        result += price
    return result

# Case 9: Equivalent configuration loading
def load_config_v1(filename):
    """First version of config loading"""
    config = {}
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    except FileNotFoundError:
        pass
    return config

def load_config_v2(config_file):
    """Semantically equivalent config loading"""
    settings = {}
    try:
        with open(config_file, 'r') as file:
            content = file.readlines()
            for content_line in content:
                if '=' in content_line:
                    parts = content_line.strip().split('=', 1)
                    settings[parts[0]] = parts[1]
    except FileNotFoundError:
        pass
    return settings

# Case 10: Equivalent validation chains
def validate_user_data_v1(data):
    """First version of user validation"""
    if not data:
        return False
    if 'name' not in data:
        return False
    if 'email' not in data:
        return False
    if len(data['name']) < 2:
        return False
    if '@' not in data['email']:
        return False
    return True

def validate_user_data_v2(user_data):
    """Semantically equivalent validation"""
    if user_data is None:
        return False
    if 'name' not in user_data:
        return False
    if 'email' not in user_data:
        return False
    name = user_data['name']
    if len(name) < 2:
        return False
    email = user_data['email']
    if '@' not in email:
        return False
    return True

def validate_user_data_v3(input_data):
    """Another equivalent validation approach"""
    # Check if data exists
    if not input_data:
        return False
    
    # Check required fields
    required_fields = ['name', 'email']
    for field in required_fields:
        if field not in input_data:
            return False
    
    # Validate name length
    if len(input_data['name']) < 2:
        return False
    
    # Validate email format
    if '@' not in input_data['email']:
        return False
    
    return True

# Case 11: Equivalent sorting operations
def sort_by_priority_v1(tasks):
    """First version of priority sorting"""
    sorted_tasks = []
    for task in tasks:
        inserted = False
        for i in range(len(sorted_tasks)):
            if task['priority'] > sorted_tasks[i]['priority']:
                sorted_tasks.insert(i, task)
                inserted = True
                break
        if not inserted:
            sorted_tasks.append(task)
    return sorted_tasks

def sort_by_priority_v2(task_list):
    """Semantically equivalent sorting"""
    result = []
    for t in task_list:
        position_found = False
        for index in range(len(result)):
            if t['priority'] > result[index]['priority']:
                result.insert(index, t)
                position_found = True
                break
        if not position_found:
            result.append(t)
    return result

# Case 12: Equivalent data merging
def merge_dictionaries_v1(dict1, dict2):
    """First version of dictionary merging"""
    result = {}
    for key in dict1:
        result[key] = dict1[key]
    for key in dict2:
        result[key] = dict2[key]
    return result

def merge_dictionaries_v2(first_dict, second_dict):
    """Semantically equivalent merging"""
    merged = {}
    for k in first_dict:
        merged[k] = first_dict[k]
    for k in second_dict:
        merged[k] = second_dict[k]
    return merged

def merge_dictionaries_v3(d1, d2):
    """Another equivalent merging approach"""
    combined = {}
    # Copy first dictionary
    for key, value in d1.items():
        combined[key] = value
    # Copy second dictionary (overwrites conflicts)
    for key, value in d2.items():
        combined[key] = value
    return combined
