"""
Alternative implementations that should be detected as semantically equivalent.
This file contains different approaches to the same problems as manual_utils.py.
"""


def calculate_total(number_list):
    """Alternative sum implementation - also should use sum() builtin"""
    result = 0
    i = 0
    while i < len(number_list):
        result = result + number_list[i]
        i += 1
    return result


def find_largest(values):
    """Alternative max implementation - also should use max() builtin"""
    if len(values) == 0:
        return None
    
    biggest = values[0]
    for value in values:
        if value > biggest:
            biggest = value
    return biggest


def find_smallest(values):
    """Alternative min implementation - also should use min() builtin"""
    if len(values) == 0:
        return None
    
    smallest = values[0]
    for i in range(len(values)):
        if values[i] < smallest:
            smallest = values[i]
    return smallest


def check_all_true(boolean_list):
    """Alternative all() implementation - should use all() builtin"""
    for boolean_value in boolean_list:
        if boolean_value == False:
            return False
    return True


def check_any_true(boolean_list):
    """Alternative any() implementation - should use any() builtin"""
    for boolean_value in boolean_list:
        if boolean_value == True:
            return True
    return False


def join_strings(string_list, delimiter):
    """Alternative string join - should use str.join() method"""
    if len(string_list) == 0:
        return ""
    
    output = string_list[0]
    for i in range(1, len(string_list)):
        output = output + delimiter + string_list[i]
    return output


def filter_items(item_list, condition_func):
    """Alternative filtering - should use filter() or list comprehension"""
    filtered = []
    for element in item_list:
        if condition_func(element):
            filtered.append(element)
    return filtered


def transform_items(item_list, transformation_func):
    """Alternative mapping - should use map() or list comprehension"""
    transformed = []
    for element in item_list:
        new_element = transformation_func(element)
        transformed.append(new_element)
    return transformed


def create_indexed_pairs(items):
    """Alternative enumerate - should use enumerate() builtin"""
    pairs = []
    counter = 0
    for item in items:
        pair = (counter, item)
        pairs.append(pair)
        counter = counter + 1
    return pairs


class ItemCounter:
    """Alternative counter - should use collections.Counter"""
    
    def __init__(self):
        self.frequency_map = {}
    
    def count_items(self, item_list):
        """Count items using different approach"""
        for item in item_list:
            current_count = self.frequency_map.get(item, 0)
            self.frequency_map[item] = current_count + 1
        return self.frequency_map


def manual_reverse(items):
    """Manual reverse implementation - should use reversed() or list[::-1]"""
    reversed_items = []
    for i in range(len(items) - 1, -1, -1):
        reversed_items.append(items[i])
    return reversed_items


def manual_sorted_implementation(items):
    """Manual sort implementation - should use sorted() builtin"""
    # Simple bubble sort
    sorted_list = items.copy()
    n = len(sorted_list)
    
    for i in range(n):
        for j in range(0, n - i - 1):
            if sorted_list[j] > sorted_list[j + 1]:
                sorted_list[j], sorted_list[j + 1] = sorted_list[j + 1], sorted_list[j]
    
    return sorted_list
