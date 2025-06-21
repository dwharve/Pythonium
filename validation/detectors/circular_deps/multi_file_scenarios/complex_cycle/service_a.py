"""
Service A in a complex circular dependency chain: A -> B -> C -> A
"""

from .service_b import ServiceB, validate_input


class ServiceA:
    """First service in the circular dependency chain"""
    
    def __init__(self):
        self.name = "ServiceA"
        self.service_b = ServiceB()
    
    def process_request(self, request):
        """Process request through ServiceB"""
        if not validate_input(request):
            raise ValueError("Invalid input")
        
        return self.service_b.handle_request(request)
    
    def get_status(self):
        """Get status from the service chain"""
        return f"ServiceA -> {self.service_b.get_status()}"


def process_a_specific(data):
    """Function specific to ServiceA"""
    return f"ProcessedByA: {data}"


# Constants used by other services
SERVICE_A_CONFIG = {
    'name': 'ServiceA',
    'version': '1.0',
    'dependencies': ['ServiceB']
}
