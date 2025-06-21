"""
Order service with more inconsistent API patterns.
This should be detected by the inconsistent API detector.
"""


class OrderHandler:
    """Order handler with mixed API conventions"""
    
    def load_order(self, order_number):
        """Load order - different from get/fetch/retrieve"""
        return {
            'order_number': order_number,
            'customer': f'Customer for {order_number}',
            'status': 'processing'
        }
    
    def place_order(self, customer_id, items, shipping_address, billing_address):
        """Place order - many individual parameters"""
        return {
            'order_id': 5555,
            'customer_id': customer_id,
            'items': items,
            'shipping': shipping_address,
            'billing': billing_address,
            'placed_at': 'now'
        }
    
    def change_order(self, order_id, modifications):
        """Change order - different verb"""
        return {
            'order_id': order_id,
            'modifications': modifications,
            'changed_at': 'now'
        }
    
    def cancel_order(self, order_id, reason):
        """Cancel order - requires reason parameter"""
        return {
            'order_id': order_id,
            'cancelled': True,
            'reason': reason,
            'refund_status': 'pending'
        }
    
    def find_orders(self, customer_id, status_filter=None, date_range=None):
        """Find orders - complex filtering"""
        return {
            'orders': [
                {'order_id': i, 'customer_id': customer_id, 'status': status_filter or 'active'}
                for i in range(5)
            ],
            'filters_applied': {
                'status': status_filter,
                'date_range': date_range
            }
        }


class OrderProcessor:
    """Order processor with different conventions"""
    
    def get_order_details(self, id):
        """Get order details - back to 'get' but different return style"""
        return [id, f'Customer {id}', 'shipped']  # Returns list instead of dict
    
    def submit_order(self, order_request):
        """Submit order - single complex parameter"""
        return (True, 6666, "Order submitted successfully")  # Returns tuple
    
    def revise_order(self, id, changes):
        """Revise order - another different verb"""
        return f"Order {id} revised: {changes}"  # Returns string
    
    def void_order(self, id):
        """Void order - no additional parameters"""
        return {'voided': True}  # Returns dict again
    
    def query_orders(self, **search_criteria):
        """Query orders - uses kwargs"""
        return [
            f"Order matching {k}={v}" 
            for k, v in search_criteria.items()
        ]


def process_order_payment(order_id, amount, payment_method):
    """Process payment - specific parameters"""
    return {
        'transaction_id': f'txn_{order_id}',
        'amount_charged': amount,
        'method': payment_method,
        'success': True
    }


def handle_payment(payment_info):
    """Handle payment - dict parameter"""
    return payment_info['order_id'], payment_info['amount'], True


def calculate_order_total(items, tax_rate, shipping_cost):
    """Calculate total - individual parameters, returns number"""
    subtotal = sum(item['price'] * item['quantity'] for item in items)
    tax = subtotal * tax_rate
    return subtotal + tax + shipping_cost


def compute_total(order_data):
    """Compute total - dict parameter, returns dict"""
    items = order_data['items']
    subtotal = sum(item['price'] * item['quantity'] for item in items)
    tax = subtotal * order_data.get('tax_rate', 0.1)
    shipping = order_data.get('shipping_cost', 0)
    
    return {
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping,
        'total': subtotal + tax + shipping
    }
