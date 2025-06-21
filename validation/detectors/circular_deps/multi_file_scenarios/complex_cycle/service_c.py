"""
Service C in a complex circular dependency chain: A -> B -> C -> A
This completes the cycle by importing from Service A.
"""

from .service_a import ServiceA, process_a_specific, SERVICE_A_CONFIG


class ServiceC:
    """Third service that completes the circular dependency chain"""
    
    def __init__(self):
        self.name = "ServiceC"
        # This completes the circle: A -> B -> C -> A
        self.service_a = ServiceA()
    
    def execute(self, data):
        """Execute using ServiceA functionality"""
        processed = process_a_specific(data)
        return self.service_a.process_request(processed)
    
    def get_status(self):
        """Get status, completing the circular chain"""
        return f"ServiceC -> {self.service_a.get_status()}"


def transform_data(data):
    """Transform data using ServiceA configuration"""
    config = SERVICE_A_CONFIG
    return f"Transformed[{config['name']}]: {data}"


# Import configuration from ServiceA
SERVICE_C_CONFIG = {
    'name': 'ServiceC',
    'version': '1.0',
    'dependencies': ['ServiceA'],
    'a_config': SERVICE_A_CONFIG
}
