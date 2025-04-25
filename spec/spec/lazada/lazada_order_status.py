import frappe
from datetime import datetime, timedelta
from frappe.utils import get_datetime, now_datetime
import json
from .lazada_order import get_lazada_order, get_lazada_order_items
from .lazada_utils import process_buyer_information

def handle_unpaid_order(trade_order_id, trade_order_line_id, update_time, notify_time, site, seller_id, buyer_id):
    """
    Handle an unpaid order from Lazada
    
    Args:
        trade_order_id (str): The Lazada trade order ID
        trade_order_line_id (str): The Lazada trade order line ID
        update_time (datetime): The time the order was updated
        notify_time (datetime): The time the notification was received
        site (str): The Lazada site (e.g., 'vn', 'sg')
        seller_id (str): The Lazada seller ID
        buyer_id (str): The Lazada buyer ID
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Check if the order already exists
        existing_order = frappe.get_all(
            "Sales Order",
            filters={"po_no": trade_order_id},
            fields=["name", "docstatus"],
            limit=1
        )
        
        if existing_order:
            # Update the existing order
            order_doc = frappe.get_doc("Sales Order", existing_order[0].name)
            order_doc.lazada_order_status = "Unpaid"
            order_doc.lazada_status_update_time = update_time
            order_doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            return {
                "success": True,
                "message": f"Order status updated: {order_doc.name}"
            }
        
        # Get order details from Lazada API
        order_details = get_lazada_order(trade_order_id)
        
        if not order_details or not order_details.get("success"):
            frappe.log_error(
                f"Failed to get order details for order {trade_order_id}: {order_details.get('message') if order_details else 'No response'}",
                "Lazada Order Error"
            )
            return {
                "success": False,
                "message": "Failed to get order details"
            }
        
        # Get order items details
        order_items_details = get_lazada_order_items(trade_order_id)
        
        if not order_items_details or not order_items_details.get("success"):
            frappe.log_error(
                f"Failed to get order items details for order {trade_order_id}: {order_items_details.get('message') if order_items_details else 'No response'}",
                "Lazada Order Error"
            )
            return {
                "success": False,
                "message": "Failed to get order items details"
            }
        
        # Process buyer information
        buyer_info = process_buyer_information(
            order_details.get("data", {}),
            order_items_details.get("data", [])
        )
        
        # Create a new Sales Order
        order_doc = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": buyer_info.get("customer_name"),
            "po_no": trade_order_id,
            "lazada_order_id": trade_order_id,
            "lazada_order_line_id": trade_order_line_id,
            "lazada_order_status": "Unpaid",
            "lazada_status_update_time": update_time,
            "lazada_notify_time": notify_time,
            "lazada_site": site,
            "lazada_seller_id": seller_id,
            "transaction_date": update_time.date(),
            "delivery_date": update_time.date() + timedelta(days=7),
            "status": "Draft",
            "payment_status": "Unpaid",
            "custom_market_platform_": "Lazada"
        })
        
        # Add order items
        for item in order_items_details.get("data", []):
            order_doc.append("items", {
                "item_code": item.get("sku", ""),
                "item_name": item.get("name", ""),
                "qty": item.get("quantity", 0),
                "rate": item.get("price", 0),
                "amount": float(item.get("price", 0)) * float(item.get("quantity", 0))
            })
        
        # Add shipping address
        shipping_address = order_details.get("data", {}).get("address_shipping", {})
        if shipping_address:
            order_doc.append("addresses", {
                "address_type": "Shipping",
                "address_line1": shipping_address.get("address1", ""),
                "address_line2": shipping_address.get("address2", ""),
                "address_line3": shipping_address.get("address3", ""),
                "city": shipping_address.get("city", ""),
                "state": shipping_address.get("addressDistrict", ""),
                "country": shipping_address.get("country", ""),
                "pincode": shipping_address.get("post_code", ""),
                "phone": shipping_address.get("phone", "")
            })
        
        # Save the order
        order_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        # Publish realtime event
        frappe.publish_realtime(
            event="new_order",
            message={
                "order_name": order_doc.name,
                "order_id": trade_order_id,
                "order_status": "Unpaid",
                "update_time": str(update_time)
            },
            doctype="Sales Order",
            docname=order_doc.name
        )
        
        return {
            "success": True,
            "message": f"New order created: {order_doc.name}"
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Lazada Unpaid Order Error")
        return {
            "success": False,
            "message": str(e)
        }

def handle_pending_order(trade_order_id, trade_order_line_id, update_time, notify_time, site, seller_id, buyer_id):
    """
    Handle a pending order from Lazada
    
    Args:
        trade_order_id (str): The Lazada trade order ID
        trade_order_line_id (str): The Lazada trade order line ID
        update_time (datetime): The time the order was updated
        notify_time (datetime): The time the notification was received
        site (str): The Lazada site (e.g., 'vn', 'sg')
        seller_id (str): The Lazada seller ID
        buyer_id (str): The Lazada buyer ID
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Check if the order already exists
        existing_order = frappe.get_all(
            "Sales Order",
            filters={"po_no": trade_order_id},
            fields=["name", "docstatus", "lazada_order_status"],
            limit=1
        )
        
        if existing_order:
            # Update the existing order
            order_doc = frappe.get_doc("Sales Order", existing_order[0].name)
            
            # If the order was previously unpaid, update the payment status
            if order_doc.lazada_order_status == "Unpaid":
                order_doc.payment_status = "Paid"
            
            # Update the order status
            order_doc.lazada_order_status = "Pending"
            order_doc.lazada_status_update_time = update_time
            order_doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            return {
                "success": True,
                "message": f"Order status updated: {order_doc.name}"
            }
        
        # Get order details from Lazada API
        order_details = get_lazada_order(trade_order_id)
        
        if not order_details or not order_details.get("success"):
            frappe.log_error(
                f"Failed to get order details for order {trade_order_id}: {order_details.get('message') if order_details else 'No response'}",
                "Lazada Order Error"
            )
            return {
                "success": False,
                "message": "Failed to get order details"
            }
        
        # Get order items details
        order_items_details = get_lazada_order_items(trade_order_id)
        
        if not order_items_details or not order_items_details.get("success"):
            frappe.log_error(
                f"Failed to get order items details for order {trade_order_id}: {order_items_details.get('message') if order_items_details else 'No response'}",
                "Lazada Order Error"
            )
            return {
                "success": False,
                "message": "Failed to get order items details"
            }
        
        # Process buyer information
        buyer_info = process_buyer_information(
            order_details.get("data", {}),
            order_items_details.get("data", [])
        )
        
        # Create a new Sales Order
        order_doc = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": buyer_info.get("customer_name"),
            "po_no": trade_order_id,
            "lazada_order_id": trade_order_id,
            "lazada_order_line_id": trade_order_line_id,
            "lazada_order_status": "Pending",
            "lazada_status_update_time": update_time,
            "lazada_notify_time": notify_time,
            "lazada_site": site,
            "lazada_seller_id": seller_id,
            "transaction_date": update_time.date(),
            "delivery_date": update_time.date() + timedelta(days=7),
            "status": "Draft",
            "payment_status": "Paid",
            "custom_market_platform_": "Lazada"
        })
        
        # Add order items
        for item in order_items_details.get("data", []):
            order_doc.append("items", {
                "item_code": item.get("sku", ""),
                "item_name": item.get("name", ""),
                "qty": item.get("quantity", 0),
                "rate": item.get("price", 0),
                "amount": float(item.get("price", 0)) * float(item.get("quantity", 0))
            })
        
        # Add shipping address
        shipping_address = order_details.get("data", {}).get("address_shipping", {})
        if shipping_address:
            order_doc.append("addresses", {
                "address_type": "Shipping",
                "address_line1": shipping_address.get("address1", ""),
                "address_line2": shipping_address.get("address2", ""),
                "address_line3": shipping_address.get("address3", ""),
                "city": shipping_address.get("city", ""),
                "state": shipping_address.get("addressDistrict", ""),
                "country": shipping_address.get("country", ""),
                "pincode": shipping_address.get("post_code", ""),
                "phone": shipping_address.get("phone", "")
            })
        
        # Save the order
        order_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        # Check inventory availability
        check_inventory_availability(order_doc)
        
        # Publish realtime event
        frappe.publish_realtime(
            event="new_order",
            message={
                "order_name": order_doc.name,
                "order_id": trade_order_id,
                "order_status": "Pending",
                "update_time": str(update_time)
            },
            doctype="Sales Order",
            docname=order_doc.name
        )
        
        return {
            "success": True,
            "message": f"New order created: {order_doc.name}"
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Lazada Pending Order Error")
        return {
            "success": False,
            "message": str(e)
        }

def check_inventory_availability(order_doc):
    """
    Check if there is enough inventory for the order
    
    Args:
        order_doc (Document): The Sales Order document
        
    Returns:
        bool: True if inventory is available, False otherwise
    """
    try:
        # Get the warehouse from settings
        warehouse = frappe.db.get_single_value("Lazada Setting", "default_warehouse")
        if not warehouse:
            frappe.log_error("Default warehouse not set in Lazada Setting", "Lazada Inventory Error")
            return False
        
        # Check each item in the order
        for item in order_doc.items:
            # Get the available quantity
            available_qty = frappe.db.get_value(
                "Bin",
                {"item_code": item.item_code, "warehouse": warehouse},
                "actual_qty"
            ) or 0
            
            # If not enough quantity, create a Material Request
            if available_qty < item.qty:
                material_request = frappe.get_doc({
                    "doctype": "Material Request",
                    "material_request_type": "Purchase",
                    "transaction_date": order_doc.transaction_date,
                    "schedule_date": order_doc.delivery_date,
                    "status": "Draft",
                    "items": [{
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "qty": item.qty - available_qty,
                        "warehouse": warehouse
                    }],
                    "custom_sales_order": order_doc.name,
                    "custom_market_platform_": "Lazada"
                })
                
                material_request.insert(ignore_permissions=True)
                frappe.db.commit()
                
                # Add a comment to the Sales Order
                order_doc.add_comment(
                    "Info",
                    f"Material Request {material_request.name} created for insufficient inventory of {item.item_code}"
                )
                order_doc.save(ignore_permissions=True)
                frappe.db.commit()
                
                return False
        
        return True
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Lazada Inventory Check Error")
        return False

def update_order_status(trade_order_id, order_status, update_time, notify_time, site, seller_id, buyer_id):
    """
    Update the order status based on the Lazada order status
    
    Args:
        trade_order_id (str): The Lazada trade order ID
        order_status (str): The Lazada order status
        update_time (datetime): The time the order was updated
        notify_time (datetime): The time the notification was received
        site (str): The Lazada site (e.g., 'vn', 'sg')
        seller_id (str): The Lazada seller ID
        buyer_id (str): The Lazada buyer ID
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Map Lazada order status to handler function
        status_handlers = {
            "unpaid": handle_unpaid_order,
            "pending": handle_pending_order,
            "ready_to_ship": handle_ready_to_ship_order,
            "shipping": handle_shipping_order,
            "delivered": handle_delivered_order,
            "cancelled": handle_cancelled_order
        }
        
        # Get the handler function
        handler = status_handlers.get(order_status.lower())
        
        if not handler:
            frappe.log_error(f"Unknown order status: {order_status}", "Lazada Order Status Error")
            return {
                "success": False,
                "message": f"Unknown order status: {order_status}"
            }
        
        # Call the handler function
        return handler(
            trade_order_id=trade_order_id,
            trade_order_line_id=None,  # This will be filled by the handler if needed
            update_time=update_time,
            notify_time=notify_time,
            site=site,
            seller_id=seller_id,
            buyer_id=buyer_id
        )
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Lazada Order Status Update Error")
        return {
            "success": False,
            "message": str(e)
        }

# Placeholder functions for other order statuses
def handle_ready_to_ship_order(trade_order_id, trade_order_line_id, update_time, notify_time, site, seller_id, buyer_id):
    """Handle a ready to ship order"""
    # Implementation will be added later
    pass

def handle_shipping_order(trade_order_id, trade_order_line_id, update_time, notify_time, site, seller_id, buyer_id):
    """Handle a shipping order"""
    # Implementation will be added later
    pass

def handle_delivered_order(trade_order_id, trade_order_line_id, update_time, notify_time, site, seller_id, buyer_id):
    """Handle a delivered order"""
    # Implementation will be added later
    pass

def handle_cancelled_order(trade_order_id, trade_order_line_id, update_time, notify_time, site, seller_id, buyer_id):
    """Handle a cancelled order"""
    # Implementation will be added later
    pass 