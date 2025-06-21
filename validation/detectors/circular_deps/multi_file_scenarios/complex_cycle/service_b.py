"""
Service B in a complex circular dependency chain: A -> B -> C -> A
"""

from .service_c import ServiceC, transform_data


class ServiceB:
    """Second service in the circular dependency chain"""
    
    def __init__(self):
        self.name = "ServiceB"
        self.service_c = ServiceC()
    
    def handle_request(self, request):
        """Handle request through ServiceC"""
        transformed = transform_data(request)
        return self.service_c.execute(transformed)
    
    def get_status(self):
        """Get status from the service chain"""
        return f"ServiceB -> {self.service_c.get_status()}"


def validate_input(data):
    """Validate input data"""
    return data is not None and len(str(data)) > 0


# Import from service_c for configuration
from .service_c import SERVICE_C_CONFIG

SERVICE_B_CONFIG = {
    'name': 'ServiceB',
    'version': '1.0',
    'dependencies': ['ServiceC'],
    'c_config': SERVICE_C_CONFIG
}
