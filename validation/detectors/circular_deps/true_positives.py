"""
True positive cases for circular dependency detector.
These contain circular import dependencies that should be detected.
"""

# Case 1: Direct circular dependency simulation
# File A imports B, B imports A

# Simulating module_a.py
class ModuleA:
    """Simulates a class that would import from module B"""
    def __init__(self):
        # This would typically be: from module_b import ModuleB
        # We simulate this with a string reference
        self.dependency = "module_b.ModuleB"
    
    def use_module_b(self):
        """Method that would use ModuleB"""
        # In real code: return ModuleB().process()
        return f"Using {self.dependency}"

# Simulating module_b.py
class ModuleB:
    """Simulates a class that would import from module A"""
    def __init__(self):
        # This would typically be: from module_a import ModuleA
        # We simulate this with a string reference
        self.dependency = "module_a.ModuleA"
    
    def use_module_a(self):
        """Method that would use ModuleA"""
        # In real code: return ModuleA().process()
        return f"Using {self.dependency}"

# Case 2: Indirect circular dependency (A -> B -> C -> A)
class ServiceA:
    """First service in circular chain"""
    def __init__(self):
        # Would import ServiceB
        self.service_b_ref = "services.service_b.ServiceB"
    
    def process(self, data):
        """Process data using ServiceB"""
        # Would call ServiceB().transform(data)
        return f"ServiceA processing with {self.service_b_ref}"

class ServiceB:
    """Second service in circular chain"""
    def __init__(self):
        # Would import ServiceC
        self.service_c_ref = "services.service_c.ServiceC"
    
    def transform(self, data):
        """Transform data using ServiceC"""
        # Would call ServiceC().validate(data)
        return f"ServiceB transforming with {self.service_c_ref}"

class ServiceC:
    """Third service that completes the circular chain"""
    def __init__(self):
        # Would import ServiceA - completing the circle
        self.service_a_ref = "services.service_a.ServiceA"
    
    def validate(self, data):
        """Validate data, might need ServiceA for some cases"""
        # Would call ServiceA().process(data) in some cases
        return f"ServiceC validating with {self.service_a_ref}"

# Case 3: Circular dependency in inheritance hierarchy
class BaseHandler:
    """Base handler that references derived handler"""
    def __init__(self):
        # Would import SpecializedHandler
        self.specialized_type = "handlers.specialized.SpecializedHandler"
    
    def handle(self, request):
        """Handle request, may delegate to specialized handler"""
        if request.get('type') == 'special':
            # Would instantiate SpecializedHandler
            return f"Delegating to {self.specialized_type}"
        return "Handled by base"

class SpecializedHandler:
    """Specialized handler that inherits from base"""
    # In real code: class SpecializedHandler(BaseHandler)
    def __init__(self):
        # Would import BaseHandler for inheritance
        self.base_type = "handlers.base.BaseHandler"
        # Simulation of super().__init__()
        self.base_initialized = True
    
    def handle(self, request):
        """Specialized handling"""
        # Would call super().handle(request) first
        base_result = f"Would call {self.base_type}.handle()"
        return f"Specialized handling after {base_result}"

# Case 4: Model relationship circular dependency
class User:
    """User model with reference to Profile"""
    def __init__(self, username):
        self.username = username
        # Would import Profile model
        self.profile_model = "models.profile.Profile"
    
    def get_profile(self):
        """Get user profile"""
        # Would query Profile.objects.filter(user=self)
        return f"Getting profile using {self.profile_model}"

class Profile:
    """Profile model with reference back to User"""
    def __init__(self, profile_data):
        self.data = profile_data
        # Would import User model for foreign key
        self.user_model = "models.user.User"
    
    def get_user(self):
        """Get associated user"""
        # Would access self.user (foreign key)
        return f"Getting user using {self.user_model}"

# Case 5: Controller circular dependency
class UserController:
    """User controller that uses AuthController"""
    def __init__(self):
        # Would import AuthController
        self.auth_controller = "controllers.auth.AuthController"
    
    def create_user(self, user_data):
        """Create user with authentication setup"""
        # Would call AuthController().setup_auth(user)
        return f"Creating user with {self.auth_controller}"

class AuthController:
    """Auth controller that uses UserController"""
    def __init__(self):
        # Would import UserController
        self.user_controller = "controllers.user.UserController"
    
    def authenticate(self, credentials):
        """Authenticate and update user info"""
        # Might call UserController().update_last_login()
        return f"Authenticating with {self.user_controller}"

# Case 6: Utility circular dependency
class DatabaseUtils:
    """Database utilities that use CacheUtils"""
    def __init__(self):
        # Would import CacheUtils
        self.cache_utils = "utils.cache.CacheUtils"
    
    def get_with_cache(self, query):
        """Get data from DB with caching"""
        # Would call CacheUtils().get_or_set()
        return f"DB query with caching via {self.cache_utils}"

class CacheUtils:
    """Cache utilities that use DatabaseUtils"""
    def __init__(self):
        # Would import DatabaseUtils
        self.db_utils = "utils.database.DatabaseUtils"
    
    def invalidate_related(self, key):
        """Invalidate cache and refresh from DB"""
        # Would call DatabaseUtils().refresh_data()
        return f"Cache invalidation with DB refresh via {self.db_utils}"

# Case 7: Factory pattern circular dependency
class ComponentFactory:
    """Factory that creates components"""
    def __init__(self):
        # Would import Component for type checking
        self.component_type = "components.base.Component"
    
    def create_component(self, component_type):
        """Create component instance"""
        # Would instantiate specific Component subclass
        return f"Creating component of type {self.component_type}"

class Component:
    """Component that uses factory for creating sub-components"""
    def __init__(self):
        # Would import ComponentFactory
        self.factory = "factories.component.ComponentFactory"
    
    def create_child(self, child_type):
        """Create child component using factory"""
        # Would call ComponentFactory().create_component()
        return f"Creating child using {self.factory}"

# Case 8: Event system circular dependency
class EventDispatcher:
    """Event dispatcher that uses event handlers"""
    def __init__(self):
        # Would import EventHandler
        self.handler_type = "events.handlers.EventHandler"
    
    def dispatch(self, event):
        """Dispatch event to handlers"""
        # Would instantiate and call EventHandler().handle()
        return f"Dispatching event to {self.handler_type}"

class EventHandler:
    """Event handler that dispatches new events"""
    def __init__(self):
        # Would import EventDispatcher
        self.dispatcher = "events.dispatcher.EventDispatcher"
    
    def handle(self, event):
        """Handle event and possibly dispatch new ones"""
        # Might call EventDispatcher().dispatch() for cascading events
        return f"Handling event, may dispatch via {self.dispatcher}"
