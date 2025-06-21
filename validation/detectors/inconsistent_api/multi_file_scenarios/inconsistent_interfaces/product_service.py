"""
Product service with inconsistent API patterns compared to user_service.py.
This should be detected by the inconsistent API detector.
"""


class ProductRepository:
    """Product repository with different API conventions"""
    
    def fetch_product(self, product_id):
        """Fetch product - different verb than 'get'"""
        return {'product_id': product_id, 'title': f'Product {product_id}'}
    
    def save_product(self, product_details):
        """Save product - uses dict, different from user creation"""
        return {'product_id': 789, **product_details}
    
    def edit_product(self, product_id, updates):
        """Edit product - different verb than 'update'"""
        return {'product_id': product_id, **updates}
    
    def destroy_product(self, product_id):
        """Destroy product - different verb than 'delete'"""
        return {'deleted': True, 'product_id': product_id}
    
    def search_products(self, query, start=0, count=20):
        """Search products - completely different pagination style"""
        return {
            'products': [
                {'product_id': i, 'title': f'Product {i}'} 
                for i in range(start, start + count)
            ],
            'total': 1000,
            'has_more': True
        }


class ProductService:
    """Product service with yet another API style"""
    
    def retrieve_product_by_id(self, id):
        """Retrieve product - long method name"""
        return {'id': id, 'name': f'Product {id}', 'status': 'active'}
    
    def register_new_product(self, name, price, category):
        """Register product - back to individual parameters"""
        return {
            'id': 999,
            'name': name,
            'price': price,
            'category': category,
            'status': 'pending'
        }
    
    def update_product_details(self, product_id, **kwargs):
        """Update with kwargs - different parameter style"""
        return {'id': product_id, **kwargs, 'updated': True}
    
    def archive_product(self, product_id):
        """Archive instead of delete - returns status message"""
        return f"Product {product_id} archived successfully"
    
    def browse_products(self, filters=None, pagination=None):
        """Browse with complex parameters"""
        pagination = pagination or {'page': 1, 'per_page': 10}
        return {
            'items': [
                {'id': i, 'name': f'Product {i}'} 
                for i in range(10)
            ],
            'pagination': pagination
        }


def make_product(title, cost):
    """Product creation function - different parameter names"""
    return {
        'product_id': 1001,
        'product_title': title,
        'product_cost': cost,
        'status': 'draft'
    }


def build_product(product_spec):
    """Alternative product creation - dict parameter"""
    return {
        'id': 1002,
        'specification': product_spec,
        'build_status': 'complete'
    }


def validate_product(title, price):
    """Product validation - returns string message"""
    if not title:
        return "Title is required"
    if price <= 0:
        return "Price must be positive"
    return "Valid"


def verify_product_data(product_data):
    """Alternative validation - returns tuple"""
    errors = []
    if not product_data.get('title'):
        errors.append("Title missing")
    if not product_data.get('price', 0) > 0:
        errors.append("Invalid price")
    
    return len(errors) == 0, errors
