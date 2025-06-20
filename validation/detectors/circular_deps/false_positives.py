"""
False positive cases for circular dependency detector.
These should NOT be flagged as circular dependencies.
"""

# Case 1: Legitimate layered architecture
class DataLayer:
    """Data access layer - bottom of the stack"""
    def __init__(self):
        self.connection = "database_connection"
    
    def fetch_data(self, query):
        """Fetch data from database"""
        return f"Fetching: {query}"
    
    def save_data(self, data):
        """Save data to database"""
        return f"Saving: {data}"

class BusinessLayer:
    """Business logic layer - uses data layer"""
    def __init__(self):
        # Legitimate downward dependency
        self.data_layer = DataLayer()
    
    def process_business_logic(self, input_data):
        """Process business logic using data layer"""
        raw_data = self.data_layer.fetch_data(input_data)
        processed = f"Processed: {raw_data}"
        self.data_layer.save_data(processed)
        return processed

class PresentationLayer:
    """Presentation layer - uses business layer"""
    def __init__(self):
        # Legitimate downward dependency
        self.business_layer = BusinessLayer()
    
    def handle_request(self, request):
        """Handle user request"""
        result = self.business_layer.process_business_logic(request)
        return f"Response: {result}"

# Case 2: Composition without circular reference
class Engine:
    """Engine component - no external dependencies"""
    def __init__(self, horsepower):
        self.horsepower = horsepower
    
    def start(self):
        """Start the engine"""
        return f"Engine with {self.horsepower}hp started"
    
    def stop(self):
        """Stop the engine"""
        return "Engine stopped"

class Car:
    """Car that contains an engine - composition"""
    def __init__(self, make, model, engine):
        self.make = make
        self.model = model
        # Composition - Car has an Engine
        self.engine = engine
    
    def start_car(self):
        """Start the car by starting the engine"""
        return f"{self.make} {self.model}: {self.engine.start()}"
    
    def stop_car(self):
        """Stop the car"""
        return f"{self.make} {self.model}: {self.engine.stop()}"

# Case 3: Observer pattern (one-way dependency)
class Subject:
    """Subject in observer pattern"""
    def __init__(self):
        self.observers = []
        self.state = None
    
    def attach(self, observer):
        """Attach observer"""
        self.observers.append(observer)
    
    def detach(self, observer):
        """Detach observer"""
        self.observers.remove(observer)
    
    def notify(self):
        """Notify all observers"""
        for observer in self.observers:
            observer.update(self.state)
    
    def set_state(self, state):
        """Set state and notify observers"""
        self.state = state
        self.notify()

class Observer:
    """Observer that watches subject"""
    def __init__(self, name):
        self.name = name
    
    def update(self, state):
        """Update when subject changes"""
        print(f"Observer {self.name} notified of state: {state}")

# Case 4: Strategy pattern (one-way dependency)
class PaymentStrategy:
    """Base payment strategy"""
    def pay(self, amount):
        """Payment method to be implemented"""
        raise NotImplementedError()

class CreditCardStrategy(PaymentStrategy):
    """Credit card payment strategy"""
    def __init__(self, card_number):
        self.card_number = card_number
    
    def pay(self, amount):
        """Pay with credit card"""
        return f"Paid ${amount} with credit card ending in {self.card_number[-4:]}"

class PayPalStrategy(PaymentStrategy):
    """PayPal payment strategy"""
    def __init__(self, email):
        self.email = email
    
    def pay(self, amount):
        """Pay with PayPal"""
        return f"Paid ${amount} via PayPal account {self.email}"

class PaymentContext:
    """Payment context that uses strategies"""
    def __init__(self, strategy):
        # One-way dependency on strategy
        self.strategy = strategy
    
    def set_strategy(self, strategy):
        """Change payment strategy"""
        self.strategy = strategy
    
    def execute_payment(self, amount):
        """Execute payment using current strategy"""
        return self.strategy.pay(amount)

# Case 5: Dependency injection (external dependency management)
class EmailService:
    """Email service - pure business logic"""
    def send_email(self, to, subject, body):
        """Send email"""
        return f"Email sent to {to}: {subject}"

class NotificationService:
    """Notification service with injected dependencies"""
    def __init__(self, email_service):
        # Dependency injected from outside
        self.email_service = email_service
    
    def send_notification(self, recipient, message):
        """Send notification via email"""
        return self.email_service.send_email(recipient, "Notification", message)

# Case 6: Template method pattern (inheritance-based)
class DataProcessor:
    """Template method pattern base class"""
    def process(self, data):
        """Template method defining the algorithm"""
        validated = self.validate(data)
        if validated:
            cleaned = self.clean(data)
            transformed = self.transform(cleaned)
            return self.save(transformed)
        return None
    
    def validate(self, data):
        """Default validation"""
        return data is not None
    
    def clean(self, data):
        """Must be implemented by subclasses"""
        raise NotImplementedError()
    
    def transform(self, data):
        """Must be implemented by subclasses"""
        raise NotImplementedError()
    
    def save(self, data):
        """Default save implementation"""
        return f"Saved: {data}"

class CsvProcessor(DataProcessor):
    """CSV-specific processor"""
    def clean(self, data):
        """Clean CSV data"""
        return data.strip()
    
    def transform(self, data):
        """Transform CSV data"""
        return data.split(',')

class JsonProcessor(DataProcessor):
    """JSON-specific processor"""
    def clean(self, data):
        """Clean JSON data"""
        return data.strip()
    
    def transform(self, data):
        """Transform JSON data"""
        import json
        return json.loads(data)

# Case 7: Factory pattern (one-way dependency)
class Product:
    """Base product class"""
    def __init__(self, name):
        self.name = name
    
    def use(self):
        """Use the product"""
        return f"Using {self.name}"

class ConcreteProductA(Product):
    """Concrete product A"""
    def __init__(self):
        super().__init__("Product A")

class ConcreteProductB(Product):
    """Concrete product B"""
    def __init__(self):
        super().__init__("Product B")

class ProductFactory:
    """Factory that creates products"""
    @staticmethod
    def create_product(product_type):
        """Create product based on type"""
        if product_type == "A":
            return ConcreteProductA()
        elif product_type == "B":
            return ConcreteProductB()
        else:
            raise ValueError(f"Unknown product type: {product_type}")

# Case 8: Adapter pattern (one-way dependency)
class LegacyService:
    """Legacy service with old interface"""
    def old_method(self, old_data):
        """Old method with legacy interface"""
        return f"Legacy processing: {old_data}"

class ModernInterface:
    """Modern interface that clients expect"""
    def modern_method(self, modern_data):
        """Modern method interface"""
        raise NotImplementedError()

class LegacyAdapter(ModernInterface):
    """Adapter that bridges legacy service to modern interface"""
    def __init__(self, legacy_service):
        # One-way dependency on legacy service
        self.legacy_service = legacy_service
    
    def modern_method(self, modern_data):
        """Adapt modern interface to legacy service"""
        # Convert modern data to legacy format
        legacy_data = f"adapted_{modern_data}"
        result = self.legacy_service.old_method(legacy_data)
        # Convert legacy result to modern format
        return f"modern_{result}"
