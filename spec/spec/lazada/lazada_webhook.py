import frappe
from datetime import datetime, timedelta
from frappe.utils import get_datetime, now_datetime
import json
from frappe.utils.file_manager import save_file
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hashlib
import hmac
import time
from .lazada_order_status import update_order_status
from .lazada_utils import process_buyer_information
from frappe import _
from .lazada_order import get_lazada_order


# Thiết lập session với retry mechanism
@frappe.whitelist(allow_guest=True)
def handle_webhook():
    """
    Xử lý thông báo từ webhook của Lazada khi có tin nhắn mới
    """
    try:
        # Log bước 1: Nhận dữ liệu từ request
        print("=== Bắt đầu xử lý webhook ===")
        data = frappe.request.get_data(as_text=True)

        if not data:
            print("Bước 1: Không nhận được dữ liệu từ webhook")
            frappe.log_error("No data received in webhook", "Lazada Webhook Error")
            return {"success": False, "error": "No data received"}

        print(f"Bước 1: Dữ liệu webhook nhận được: {data[:500]}...")  # Giới hạn log để tránh quá dài

        # Log bước 2: Parse dữ liệu JSON
        try:
            webhook_data = json.loads(data)
            print(f"Bước 2: Parse JSON thành công: {json.dumps(webhook_data, indent=2)[:500]}...")
        except json.JSONDecodeError as e:
            print(f"Bước 2: Lỗi parse JSON: {str(e)}")
            frappe.log_error(f"Invalid JSON in webhook data: {data}, Error: {str(e)}", "Lazada Webhook Error")
            return {"success": False, "error": "Invalid JSON"}

        # Trả về phản hồi ngay lập tức cho Lazada
        print("Bước 3: Trả về phản hồi 200 cho Lazada")
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = {"success": True, "message": "Webhook received"}

        # Đưa xử lý vào hàng đợi bất đồng bộ
        print("Bước 4: Đưa xử lý vào hàng đợi bất đồng bộ")

        frappe.enqueue(
            process_webhook_data,
            queue="short",
            data=data
        )
        # process_webhook_data(data)
        
        # Gọi trực tiếp hàm process_webhook_data để xử lý ngay lập tức
        print("Bước 5: Xử lý webhook data ngay lập tức")
        
        print("=== Kết thúc xử lý webhook ===")
        return {"success": True, "message": "Webhook received and processed"}
    except Exception as e:
        print(f"Lỗi xử lý webhook: {str(e)}")
        frappe.log_error(frappe.get_traceback(), "Lazada Webhook Exception")
        return {"success": False, "error": str(e)}

def process_webhook_data(data):
    """Process webhook data from Lazada"""
    try:
        print(f"=== Bắt đầu xử lý webhook data ===")
        
        # Parse webhook data
        webhook_data = json.loads(data)
        
        # Process based on message type
        message_type = webhook_data.get("message_type")
        print(f"Message type: {message_type}")
        
        if message_type == 0:  # Order notification
            result = handle_order_notification(webhook_data)
        else:
            result = {"status": "error", "message": f"Unsupported message type: {message_type}"}
        
        print(f"=== Kết thúc xử lý webhook data: {result.get('status')} ===")
        return result
    except Exception as e:
        error_message = str(e)
        print(f"Error processing webhook data: {error_message}")
        frappe.log_error(f"Error processing webhook data: {error_message}", "Webhook Processing Error")
        return {"status": "error", "message": error_message}

def handle_order_notification(webhook_data):
    """Handle order notification from Lazada webhook"""
    try:
        print("=== Bắt đầu xử lý thông báo đơn hàng ===")
        order_data = webhook_data.get("data", {})
        trade_order_id = order_data.get("trade_order_id")
        order_status = order_data.get("order_status")
        
        if not trade_order_id:
            print("Missing trade_order_id in webhook data")
            return {"status": "error", "message": "Missing trade_order_id in webhook data"}
        
        print(f"Processing order: {trade_order_id}, status: {order_status}")
        
        # Check if order exists
        existing_order = frappe.get_all(
            "Sales Order",
            filters={"lazada_order_id": trade_order_id},
            fields=["name", "docstatus"]
        )
        
        if existing_order:
            # Update order status
            print(f"Order exists, updating status: {existing_order[0].name}")
            order_doc = frappe.get_doc("Sales Order", existing_order[0].name)
            update_order_status(order_doc, order_status)
            print("Order status updated successfully")
            return {"status": "success", "message": "Order status updated"}
        else:
            # Get order details from Lazada API
            print(f"Order does not exist, fetching details from Lazada API")
            order_details = get_lazada_order(trade_order_id)
            if not order_details:
                print("Failed to get order details from Lazada")
                return {"status": "error", "message": "Failed to get order details from Lazada"}
            
            # Create new Sales Order
            print("Creating new Sales Order")
            create_sales_order(order_details)
            print("New Sales Order created successfully")
            return {"status": "success", "message": "New order created"}
    except Exception as e:
        error_message = str(e)
        print(f"Error handling order notification: {error_message}")
        frappe.log_error(f"Error handling order notification: {error_message}", "Order Notification Error")
        return {"status": "error", "message": error_message}

def create_sales_order(order_details):
    """Create a new Sales Order from Lazada order details"""
    try:
        # Create Sales Order
        sales_order = frappe.get_doc({
            "doctype": "Sales Order",
            "lazada_order_id": order_details.get("order_id"),
            "lazada_order_status": order_details.get("order_status"),
            "transaction_date": frappe.utils.nowdate(),
            "delivery_date": frappe.utils.add_days(frappe.utils.nowdate(), 7),
            "customer": get_or_create_customer(order_details.get("buyer_info", {})),
            "items": get_order_items(order_details.get("items", [])),
            "taxes_and_charges": "",
            "status": "Draft"
        })
        
        sales_order.insert()
        frappe.db.commit()
        
        # Publish realtime event
        frappe.publish_realtime(
            "lazada_order_created",
            {
                "order_id": sales_order.name,
                "lazada_order_id": order_details.get("order_id")
            }
        )
        
        return sales_order.name
    except Exception as e:
        frappe.log_error(f"Error creating sales order: {str(e)}", "Sales Order Creation Error")
        raise

def get_or_create_customer(buyer_info):
    """Get or create customer from buyer info"""
    try:
        # Check if customer exists
        customer_name = frappe.db.get_value(
            "Customer",
            {"lazada_buyer_id": buyer_info.get("buyer_id")},
            "name"
        )
        
        if customer_name:
            return customer_name
        
        # Create new customer
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": buyer_info.get("buyer_name", "Lazada Customer"),
            "customer_type": "Individual",
            "lazada_buyer_id": buyer_info.get("buyer_id"),
            "email_id": buyer_info.get("email"),
            "mobile_no": buyer_info.get("phone")
        })
        
        customer.insert()
        frappe.db.commit()
        
        return customer.name
    except Exception as e:
        frappe.log_error(f"Error getting/creating customer: {str(e)}", "Customer Creation Error")
        raise

def get_order_items(items_data):
    """Convert Lazada order items to Sales Order items"""
    order_items = []
    
    for item in items_data:
        # Get or create Item
        item_code = get_or_create_item(item)
        
        order_items.append({
            "item_code": item_code,
            "qty": item.get("quantity", 1),
            "rate": item.get("price", 0),
            "amount": item.get("price", 0) * item.get("quantity", 1)
        })
    
    return order_items

def get_or_create_item(item_data):
    """Get or create Item from Lazada item data"""
    try:
        # Check if item exists
        item_code = frappe.db.get_value(
            "Item",
            {"lazada_item_id": item_data.get("item_id")},
            "name"
        )
        
        if item_code:
            return item_code
        
        # Create new item
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": f"LAZ-{item_data.get('item_id')}",
            "item_name": item_data.get("name", "Lazada Item"),
            "item_group": "Lazada Items",
            "stock_uom": "Nos",
            "is_stock_item": 1,
            "lazada_item_id": item_data.get("item_id")
        })
        
        item.insert()
        frappe.db.commit()
        
        return item.name
    except Exception as e:
        frappe.log_error(f"Error getting/creating item: {str(e)}", "Item Creation Error")
        raise

