"""
Complex business logic module with high complexity functions.
This should be detected by the complexity hotspot detector.
"""


def complex_order_processor(order_data, user_preferences, inventory, pricing_rules, tax_rules, shipping_rules, discount_codes):
    """
    Complex order processing function with high cyclomatic complexity.
    This function should be flagged for having too many conditional branches and being too long.
    """
    # Validate order data
    if not order_data:
        raise ValueError("Order data is required")
    
    if not order_data.get('items'):
        raise ValueError("Order must contain items")
    
    if not order_data.get('customer_id'):
        raise ValueError("Customer ID is required")
    
    if not user_preferences:
        user_preferences = {}
    
    # Initialize order processing
    processed_order = {
        'order_id': order_data.get('order_id', 'temp'),
        'customer_id': order_data['customer_id'],
        'items': [],
        'subtotal': 0,
        'tax': 0,
        'shipping': 0,
        'discounts': 0,
        'total': 0,
        'status': 'processing'
    }
    
    # Process each item
    for item in order_data['items']:
        if not item.get('product_id'):
            continue
        
        product_id = item['product_id']
        quantity = item.get('quantity', 1)
        
        # Check inventory
        if product_id not in inventory:
            processed_order['status'] = 'failed'
            processed_order['error'] = f"Product {product_id} not in inventory"
            return processed_order
        
        if inventory[product_id]['stock'] < quantity:
            if user_preferences.get('allow_backorder', False):
                item['status'] = 'backordered'
                backorder_days = inventory[product_id].get('backorder_days', 14)
                if backorder_days > 30:
                    processed_order['status'] = 'failed'
                    processed_order['error'] = f"Product {product_id} backorder too long"
                    return processed_order
                item['estimated_ship_date'] = f"In {backorder_days} days"
            else:
                processed_order['status'] = 'failed'
                processed_order['error'] = f"Insufficient stock for product {product_id}"
                return processed_order
        else:
            item['status'] = 'in_stock'
        
        # Calculate item price
        base_price = inventory[product_id]['price']
        item_total = base_price * quantity
        
        # Apply pricing rules
        if pricing_rules:
            for rule in pricing_rules:
                if rule['type'] == 'bulk_discount':
                    if quantity >= rule['min_quantity']:
                        if rule['discount_type'] == 'percentage':
                            discount = item_total * (rule['discount_value'] / 100)
                            item_total -= discount
                        elif rule['discount_type'] == 'fixed':
                            item_total -= rule['discount_value'] * quantity
                
                elif rule['type'] == 'category_discount':
                    if inventory[product_id].get('category') == rule['category']:
                        if rule['discount_type'] == 'percentage':
                            discount = item_total * (rule['discount_value'] / 100)
                            item_total -= discount
                        elif rule['discount_type'] == 'fixed':
                            item_total -= rule['discount_value']
                
                elif rule['type'] == 'customer_tier':
                    customer_tier = user_preferences.get('tier', 'standard')
                    if customer_tier == rule['tier']:
                        if rule['discount_type'] == 'percentage':
                            discount = item_total * (rule['discount_value'] / 100)
                            item_total -= discount
                        elif rule['discount_type'] == 'fixed':
                            item_total -= rule['discount_value']
        
        # Update inventory
        inventory[product_id]['stock'] -= quantity
        
        # Add to processed items
        processed_item = {
            'product_id': product_id,
            'quantity': quantity,
            'unit_price': base_price,
            'total_price': item_total,
            'status': item['status']
        }
        
        if 'estimated_ship_date' in item:
            processed_item['estimated_ship_date'] = item['estimated_ship_date']
        
        processed_order['items'].append(processed_item)
        processed_order['subtotal'] += item_total
    
    # Apply order-level discount codes
    if discount_codes and order_data.get('discount_codes'):
        for code in order_data['discount_codes']:
            if code in discount_codes:
                discount_rule = discount_codes[code]
                
                # Check if discount is still valid
                if discount_rule.get('expired', False):
                    continue
                
                # Check minimum order requirement
                if discount_rule.get('min_order_amount', 0) > processed_order['subtotal']:
                    continue
                
                # Check usage limits
                if discount_rule.get('usage_count', 0) >= discount_rule.get('max_usage', 1000):
                    continue
                
                # Apply discount
                if discount_rule['type'] == 'percentage':
                    discount_amount = processed_order['subtotal'] * (discount_rule['value'] / 100)
                    max_discount = discount_rule.get('max_discount_amount', float('inf'))
                    discount_amount = min(discount_amount, max_discount)
                elif discount_rule['type'] == 'fixed':
                    discount_amount = discount_rule['value']
                elif discount_rule['type'] == 'free_shipping':
                    processed_order['free_shipping'] = True
                    discount_amount = 0
                else:
                    continue
                
                processed_order['discounts'] += discount_amount
                discount_codes[code]['usage_count'] = discount_codes[code].get('usage_count', 0) + 1
    
    # Calculate tax
    if tax_rules:
        customer_state = user_preferences.get('state', 'CA')
        customer_country = user_preferences.get('country', 'US')
        
        for rule in tax_rules:
            if rule['country'] == customer_country:
                if rule.get('state') and rule['state'] == customer_state:
                    tax_rate = rule['rate']
                elif not rule.get('state'):
                    tax_rate = rule['rate']
                else:
                    continue
                
                taxable_amount = processed_order['subtotal'] - processed_order['discounts']
                
                # Check for tax-exempt items
                taxable_amount_adjusted = 0
                for item in processed_order['items']:
                    product_id = item['product_id']
                    if inventory[product_id].get('tax_exempt', False):
                        continue
                    taxable_amount_adjusted += item['total_price']
                
                processed_order['tax'] = taxable_amount_adjusted * tax_rate
                break
    
    # Calculate shipping
    if shipping_rules and not processed_order.get('free_shipping', False):
        total_weight = 0
        total_volume = 0
        
        for item in processed_order['items']:
            product_id = item['product_id']
            quantity = item['quantity']
            
            item_weight = inventory[product_id].get('weight', 0) * quantity
            item_volume = inventory[product_id].get('volume', 0) * quantity
            
            total_weight += item_weight
            total_volume += item_volume
        
        shipping_method = user_preferences.get('shipping_method', 'standard')
        customer_zip = user_preferences.get('zip_code', '90210')
        
        for rule in shipping_rules:
            if rule['method'] == shipping_method:
                # Zone-based shipping
                if rule.get('zones'):
                    customer_zone = 'zone1'  # Simplified zone lookup
                    if customer_zip.startswith(('9', '8')):
                        customer_zone = 'zone1'
                    elif customer_zip.startswith(('7', '6')):
                        customer_zone = 'zone2'
                    elif customer_zip.startswith(('5', '4')):
                        customer_zone = 'zone3'
                    else:
                        customer_zone = 'zone4'
                    
                    if customer_zone in rule['zones']:
                        zone_rule = rule['zones'][customer_zone]
                        
                        if zone_rule['type'] == 'flat_rate':
                            processed_order['shipping'] = zone_rule['rate']
                        elif zone_rule['type'] == 'weight_based':
                            processed_order['shipping'] = total_weight * zone_rule['rate_per_lb']
                        elif zone_rule['type'] == 'tiered':
                            for tier in zone_rule['tiers']:
                                if total_weight <= tier['max_weight']:
                                    processed_order['shipping'] = tier['rate']
                                    break
                
                # Free shipping threshold
                if rule.get('free_shipping_threshold'):
                    if processed_order['subtotal'] >= rule['free_shipping_threshold']:
                        processed_order['shipping'] = 0
                        processed_order['free_shipping'] = True
                
                break
    
    # Apply final calculations
    processed_order['total'] = (
        processed_order['subtotal'] 
        - processed_order['discounts'] 
        + processed_order['tax'] 
        + processed_order['shipping']
    )
    
    # Final validations
    if processed_order['total'] < 0:
        processed_order['total'] = 0
    
    if processed_order['total'] > 999999:  # Maximum order limit
        processed_order['status'] = 'failed'
        processed_order['error'] = 'Order exceeds maximum limit'
        return processed_order
    
    # Check payment processing requirements
    if processed_order['total'] > 5000:
        processed_order['requires_manual_review'] = True
    
    if any(item['status'] == 'backordered' for item in processed_order['items']):
        processed_order['contains_backorders'] = True
    
    processed_order['status'] = 'processed'
    return processed_order


def deeply_nested_configuration_parser(config_data, schema, defaults, overrides, environment):
    """
    Another complex function with deep nesting and high cyclomatic complexity.
    This should also be flagged by the complexity detector.
    """
    if not config_data:
        config_data = {}
    
    if not schema:
        schema = {}
    
    if not defaults:
        defaults = {}
    
    parsed_config = {}
    errors = []
    warnings = []
    
    # Process each schema section
    for section_name, section_schema in schema.items():
        if section_name not in parsed_config:
            parsed_config[section_name] = {}
        
        section_data = config_data.get(section_name, {})
        section_defaults = defaults.get(section_name, {})
        section_overrides = overrides.get(section_name, {}) if overrides else {}
        
        # Process each field in the section
        for field_name, field_schema in section_schema.items():
            field_value = None
            
            # Determine field value precedence: overrides > config > defaults
            if field_name in section_overrides:
                field_value = section_overrides[field_name]
            elif field_name in section_data:
                field_value = section_data[field_name]
            elif field_name in section_defaults:
                field_value = section_defaults[field_name]
            else:
                if field_schema.get('required', False):
                    errors.append(f"Required field {section_name}.{field_name} is missing")
                    continue
                else:
                    field_value = field_schema.get('default')
            
            # Type validation
            expected_type = field_schema.get('type')
            if expected_type:
                if expected_type == 'string':
                    if not isinstance(field_value, str):
                        if field_value is not None:
                            field_value = str(field_value)
                            warnings.append(f"Converted {section_name}.{field_name} to string")
                
                elif expected_type == 'integer':
                    if not isinstance(field_value, int):
                        if isinstance(field_value, str) and field_value.isdigit():
                            field_value = int(field_value)
                            warnings.append(f"Converted {section_name}.{field_name} to integer")
                        else:
                            errors.append(f"Field {section_name}.{field_name} must be an integer")
                            continue
                
                elif expected_type == 'float':
                    if not isinstance(field_value, (int, float)):
                        try:
                            field_value = float(field_value)
                            warnings.append(f"Converted {section_name}.{field_name} to float")
                        except (ValueError, TypeError):
                            errors.append(f"Field {section_name}.{field_name} must be a number")
                            continue
                
                elif expected_type == 'boolean':
                    if not isinstance(field_value, bool):
                        if isinstance(field_value, str):
                            if field_value.lower() in ('true', '1', 'yes', 'on'):
                                field_value = True
                            elif field_value.lower() in ('false', '0', 'no', 'off'):
                                field_value = False
                            else:
                                errors.append(f"Field {section_name}.{field_name} must be a boolean")
                                continue
                        elif isinstance(field_value, int):
                            field_value = bool(field_value)
                        else:
                            errors.append(f"Field {section_name}.{field_name} must be a boolean")
                            continue
                
                elif expected_type == 'list':
                    if not isinstance(field_value, list):
                        if isinstance(field_value, str):
                            # Try to split comma-separated values
                            field_value = [item.strip() for item in field_value.split(',')]
                            warnings.append(f"Converted {section_name}.{field_name} to list")
                        else:
                            errors.append(f"Field {section_name}.{field_name} must be a list")
                            continue
                
                elif expected_type == 'dict':
                    if not isinstance(field_value, dict):
                        errors.append(f"Field {section_name}.{field_name} must be a dictionary")
                        continue
            
            # Value validation
            if 'enum' in field_schema:
                if field_value not in field_schema['enum']:
                    errors.append(f"Field {section_name}.{field_name} must be one of {field_schema['enum']}")
                    continue
            
            if 'min' in field_schema:
                if isinstance(field_value, (int, float)) and field_value < field_schema['min']:
                    errors.append(f"Field {section_name}.{field_name} must be >= {field_schema['min']}")
                    continue
            
            if 'max' in field_schema:
                if isinstance(field_value, (int, float)) and field_value > field_schema['max']:
                    errors.append(f"Field {section_name}.{field_name} must be <= {field_schema['max']}")
                    continue
            
            if 'pattern' in field_schema:
                import re
                if isinstance(field_value, str) and not re.match(field_schema['pattern'], field_value):
                    errors.append(f"Field {section_name}.{field_name} does not match required pattern")
                    continue
            
            # Environment variable substitution
            if environment and isinstance(field_value, str):
                if field_value.startswith('${') and field_value.endswith('}'):
                    env_var = field_value[2:-1]
                    if env_var in environment:
                        field_value = environment[env_var]
                        warnings.append(f"Substituted environment variable for {section_name}.{field_name}")
                    else:
                        if field_schema.get('required', False):
                            errors.append(f"Environment variable {env_var} not found for {section_name}.{field_name}")
                            continue
                        else:
                            field_value = field_schema.get('default')
            
            parsed_config[section_name][field_name] = field_value
    
    return {
        'config': parsed_config,
        'errors': errors,
        'warnings': warnings,
        'valid': len(errors) == 0
    }
