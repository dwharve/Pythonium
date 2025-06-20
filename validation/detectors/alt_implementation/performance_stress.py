"""
Performance stress test for validation system.
This file contains many instances of code patterns to test detector performance.
"""

# Generate many instances of alternative implementations to stress test
def process_list_manual_1(items):
    """Manual list processing version 1"""
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result

def process_list_manual_2(data):
    """Manual list processing version 2"""
    output = []
    for element in data:
        if element > 0:
            output.append(element * 2)
    return output

def process_list_manual_3(values):
    """Manual list processing version 3"""
    processed = []
    for val in values:
        if val > 0:
            processed.append(val * 2)
    return processed

def process_list_manual_4(numbers):
    """Manual list processing version 4"""
    results = []
    for num in numbers:
        if num > 0:
            results.append(num * 2)
    return results

def process_list_manual_5(input_list):
    """Manual list processing version 5"""
    filtered = []
    for x in input_list:
        if x > 0:
            filtered.append(x * 2)
    return filtered

# Generate many string concatenation patterns
def build_string_manual_1(parts):
    """Manual string building version 1"""
    result = ""
    for part in parts:
        result += str(part) + ","
    return result[:-1] if result else ""

def build_string_manual_2(elements):
    """Manual string building version 2"""
    output = ""
    for element in elements:
        output += str(element) + ","
    return output[:-1] if output else ""

def build_string_manual_3(items):
    """Manual string building version 3"""
    text = ""
    for item in items:
        text += str(item) + ","
    return text[:-1] if text else ""

# Generate many dictionary building patterns
def create_dict_manual_1(keys, values):
    """Manual dictionary creation version 1"""
    result = {}
    for i in range(len(keys)):
        result[keys[i]] = values[i]
    return result

def create_dict_manual_2(key_list, value_list):
    """Manual dictionary creation version 2"""
    output = {}
    for idx in range(len(key_list)):
        output[key_list[idx]] = value_list[idx]
    return output

def create_dict_manual_3(k_array, v_array):
    """Manual dictionary creation version 3"""
    mapping = {}
    for index in range(len(k_array)):
        mapping[k_array[index]] = v_array[index]
    return mapping

# Generate many max/min finding patterns
def find_max_manual_1(numbers):
    """Manual max finding version 1"""
    if not numbers:
        return None
    maximum = numbers[0]
    for num in numbers[1:]:
        if num > maximum:
            maximum = num
    return maximum

def find_max_manual_2(values):
    """Manual max finding version 2"""
    if not values:
        return None
    max_val = values[0]
    for val in values[1:]:
        if val > max_val:
            max_val = val
    return max_val

def find_max_manual_3(data):
    """Manual max finding version 3"""
    if not data:
        return None
    largest = data[0]
    for item in data[1:]:
        if item > largest:
            largest = item
    return largest

# Generate many validation patterns
def validate_data_1(data):
    """Validation pattern version 1"""
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

def validate_data_2(info):
    """Validation pattern version 2"""
    if not info:
        return False
    if 'name' not in info:
        return False
    if 'email' not in info:
        return False
    if len(info['name']) < 2:
        return False
    if '@' not in info['email']:
        return False
    return True

def validate_data_3(input_data):
    """Validation pattern version 3"""
    if not input_data:
        return False
    if 'name' not in input_data:
        return False
    if 'email' not in input_data:
        return False
    if len(input_data['name']) < 2:
        return False
    if '@' not in input_data['email']:
        return False
    return True

# Generate many file processing patterns
def process_file_1(filename):
    """File processing version 1"""
    lines = []
    try:
        with open(filename, 'r') as f:
            line = f.readline()
            while line:
                lines.append(line.strip())
                line = f.readline()
    except FileNotFoundError:
        pass
    return lines

def process_file_2(filepath):
    """File processing version 2"""
    content = []
    try:
        with open(filepath, 'r') as file:
            current_line = file.readline()
            while current_line:
                content.append(current_line.strip())
                current_line = file.readline()
    except FileNotFoundError:
        pass
    return content

def process_file_3(file_path):
    """File processing version 3"""
    result = []
    try:
        with open(file_path, 'r') as f:
            text_line = f.readline()
            while text_line:
                result.append(text_line.strip())
                text_line = f.readline()
    except FileNotFoundError:
        pass
    return result

# Generate many mathematical calculation patterns
def calculate_average_1(numbers):
    """Average calculation version 1"""
    if not numbers:
        return 0
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

def calculate_average_2(values):
    """Average calculation version 2"""
    if not values:
        return 0
    sum_total = 0
    for val in values:
        sum_total += val
    return sum_total / len(values)

def calculate_average_3(data):
    """Average calculation version 3"""
    if not data:
        return 0
    accumulator = 0
    for item in data:
        accumulator += item
    return accumulator / len(data)

# Generate many error handling patterns
def safe_operation_1(a, b):
    """Safe operation version 1"""
    try:
        return a / b
    except ZeroDivisionError:
        return None
    except TypeError:
        return None

def safe_operation_2(x, y):
    """Safe operation version 2"""
    try:
        return x / y
    except ZeroDivisionError:
        return None
    except TypeError:
        return None

def safe_operation_3(num1, num2):
    """Safe operation version 3"""
    try:
        return num1 / num2
    except ZeroDivisionError:
        return None
    except TypeError:
        return None

# Generate many data transformation patterns
def transform_data_1(raw_data):
    """Data transformation version 1"""
    processed = []
    for item in raw_data:
        if isinstance(item, str):
            processed.append(item.upper().strip())
    return processed

def transform_data_2(input_data):
    """Data transformation version 2"""
    cleaned = []
    for element in input_data:
        if isinstance(element, str):
            cleaned.append(element.upper().strip())
    return cleaned

def transform_data_3(source_data):
    """Data transformation version 3"""
    output = []
    for value in source_data:
        if isinstance(value, str):
            output.append(value.upper().strip())
    return output
