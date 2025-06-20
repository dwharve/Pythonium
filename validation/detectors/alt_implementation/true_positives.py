"""
True positive cases for alternative implementation detector.
These should be detected as having better alternative implementations.
"""

# Case 1: Manual iteration instead of list comprehension
def process_numbers_manual(numbers):
    """Manual iteration that could be a list comprehension"""
    result = []
    for num in numbers:
        if num > 0:
            result.append(num * 2)
    return result

# Better alternative would be: [num * 2 for num in numbers if num > 0]

# Case 2: Manual string concatenation instead of join
def create_csv_line_manual(items):
    """Manual string concatenation instead of join"""
    result = ""
    for i, item in enumerate(items):
        if i > 0:
            result += ","
        result += str(item)
    return result

# Better alternative would be: ",".join(str(item) for item in items)

# Case 3: Manual dictionary building instead of dict comprehension
def create_mapping_manual(keys, values):
    """Manual dictionary building"""
    result = {}
    for i in range(len(keys)):
        result[keys[i]] = values[i]
    return result

# Better alternative would be: dict(zip(keys, values))

# Case 4: Inefficient file reading
def read_lines_inefficient(filename):
    """Reading file line by line inefficiently"""
    lines = []
    with open(filename, 'r') as f:
        line = f.readline()
        while line:
            lines.append(line.strip())
            line = f.readline()
    return lines

# Better alternative would be: [line.strip() for line in open(filename)]

# Case 5: Manual max/min finding
def find_maximum_manual(numbers):
    """Manual maximum finding"""
    if not numbers:
        return None
    max_val = numbers[0]
    for num in numbers[1:]:
        if num > max_val:
            max_val = num
    return max_val

# Better alternative would be: max(numbers) if numbers else None

# Case 6: Inefficient string checking
def has_any_substring_manual(text, substrings):
    """Manual substring checking"""
    for substring in substrings:
        found = False
        for i in range(len(text) - len(substring) + 1):
            if text[i:i+len(substring)] == substring:
                found = True
                break
        if found:
            return True
    return False

# Better alternative would be: any(sub in text for sub in substrings)

# Case 7: Manual sorting with comparison
def sort_by_length_manual(strings):
    """Manual bubble sort by length"""
    result = strings.copy()
    n = len(result)
    for i in range(n):
        for j in range(0, n - i - 1):
            if len(result[j]) > len(result[j + 1]):
                result[j], result[j + 1] = result[j + 1], result[j]
    return result

# Better alternative would be: sorted(strings, key=len)

# Case 8: Manual set operations
def get_common_elements_manual(list1, list2):
    """Manual intersection finding"""
    common = []
    for item in list1:
        if item in list2 and item not in common:
            common.append(item)
    return common

# Better alternative would be: list(set(list1) & set(list2))

# Case 9: Manual counting
def count_occurrences_manual(items, target):
    """Manual counting instead of using count()"""
    count = 0
    for item in items:
        if item == target:
            count += 1
    return count

# Better alternative would be: items.count(target)

# Case 10: Manual filtering and mapping combined
def process_data_manual(data):
    """Manual filtering and transformation"""
    result = []
    for item in data:
        if isinstance(item, (int, float)) and item > 0:
            result.append(item ** 2)
    return result

# Better alternative would be: [x**2 for x in data if isinstance(x, (int, float)) and x > 0]
