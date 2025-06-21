"""
Utilities module with manual implementations that could use builtins.
This should be detected by the semantic equivalence detector.
"""


def manual_sum_implementation(numbers):
    """Manual sum implementation - should use sum() builtin"""
    total = 0
    for num in numbers:
        total += num
    return total


def manual_max_finder(numbers):
    """Manual max implementation - should use max() builtin"""
    if not numbers:
        return None
    
    maximum = numbers[0]
    for num in numbers[1:]:
        if num > maximum:
            maximum = num
    return maximum


def manual_min_finder(numbers):
    """Manual min implementation - should use min() builtin"""
    if not numbers:
        return None
    
    minimum = numbers[0]
    for num in numbers[1:]:
        if num < minimum:
            minimum = num
    return minimum


def manual_all_checker(items):
    """Manual all() implementation - should use all() builtin"""
    for item in items:
        if not item:
            return False
    return True


def manual_any_checker(items):
    """Manual any() implementation - should use any() builtin"""
    for item in items:
        if item:
            return True
    return False


def manual_string_joiner(strings, separator):
    """Manual string join - should use str.join() method"""
    if not strings:
        return ""
    
    result = strings[0]
    for s in strings[1:]:
        result += separator + s
    return result


def manual_list_filter(items, predicate):
    """Manual filtering - should use filter() or list comprehension"""
    result = []
    for item in items:
        if predicate(item):
            result.append(item)
    return result


def manual_list_map(items, transform):
    """Manual mapping - should use map() or list comprehension"""
    result = []
    for item in items:
        result.append(transform(item))
    return result


def manual_enumerate_implementation(items):
    """Manual enumerate - should use enumerate() builtin"""
    result = []
    index = 0
    for item in items:
        result.append((index, item))
        index += 1
    return result


class ManualCounter:
    """Manual counter implementation - should use collections.Counter"""
    
    def __init__(self):
        self.counts = {}
    
    def count(self, items):
        """Count items manually"""
        for item in items:
            if item in self.counts:
                self.counts[item] += 1
            else:
                self.counts[item] = 1
        return self.counts
