import frappe
from datetime import datetime, timedelta
from frappe.utils import get_datetime, now_datetime

def process_buyer_information(order_data, order_items_data):
    """
    Process buyer information from Lazada order data
    
    Args:
        order_data (dict): The order data from Lazada
        order_items_data (list): The order items data from Lazada
        
    Returns:
        dict: The processed buyer information
    """
    try:
        # Extract buyer information
        buyer_info = order_data.get("buyer_info", {})
        if not buyer_info:
            frappe.log_error("No buyer information in order data", "Lazada Buyer Information Error")
            return {
                "customer_name": "Lazada Customer",
                "customer_email": "",
                "customer_phone": ""
            }
        
        # Extract buyer details
        buyer_name = buyer_info.get("name", "Lazada Customer")
        buyer_email = buyer_info.get("email", "")
        buyer_phone = buyer_info.get("phone", "")
        
        # Check if the customer already exists
        existing_customer = frappe.get_all(
            "Customer",
            filters={"customer_name": buyer_name},
            fields=["name"],
            limit=1
        )
        
        if existing_customer:
            return {
                "customer_name": existing_customer[0].name,
                "customer_email": buyer_email,
                "customer_phone": buyer_phone
            }
        
        # Create a new customer
        customer_doc = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": buyer_name,
            "customer_type": "Individual",
            "customer_group": "All Customer Groups",
            "territory": "All Territories",
            "email_id": buyer_email,
            "mobile_no": buyer_phone,
            "custom_market_platform_": "Lazada"
        })
        
        customer_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "customer_name": customer_doc.name,
            "customer_email": buyer_email,
            "customer_phone": buyer_phone
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Lazada Buyer Information Processing Error")
        return {
            "customer_name": "Lazada Customer",
            "customer_email": "",
            "customer_phone": ""
        } 