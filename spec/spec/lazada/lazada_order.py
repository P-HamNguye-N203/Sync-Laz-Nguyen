import frappe
import time
import requests
from urllib.parse import urlencode
from .utils import get_lazada_setting, generate_lazada_sign, refresh_lazada_access_token, Base_URL
from datetime import datetime, timedelta

def get_lazada_order(order_id, lazada_settings=None):
    """
    Lấy thông tin đơn hàng từ Lazada API sử dụng endpoint /order/get
    
    Args:
        order_id (str): ID của đơn hàng cần lấy thông tin
        lazada_settings (dict, optional): Cấu hình Lazada. Nếu không cung cấp, sẽ lấy từ get_lazada_setting()
        
    Returns:
        dict: Thông tin đơn hàng từ Lazada API
    """
    try:
        # Lấy cấu hình Lazada nếu không được cung cấp
        if not lazada_settings:
            lazada_settings = get_lazada_setting()
            
        if not lazada_settings:
            frappe.log_error("Không tìm thấy cấu hình Lazada", "Lazada Order API Error")
            return {"success": False, "message": "Lazada settings not found"}
            
        # Kiểm tra và làm mới access token nếu cần
        current_time = int(time.time())
        if lazada_settings.access_token_expiry and current_time >= int(lazada_settings.access_token_expiry) - 300:
            refresh_lazada_access_token()
            # Lấy lại cấu hình sau khi làm mới token
            lazada_settings = get_lazada_setting()
            
        # Chuẩn bị tham số cho API
        api_path = "/order/get"
        params = {
            "app_key": lazada_settings.app_key,
            "timestamp": str(int(time.time() * 1000)),
            "order_id": order_id,
            "sign_method": "sha256",
            "access_token": lazada_settings.access_token
        }
        
        # Tạo chữ ký
        sign = generate_lazada_sign(api_path, params, lazada_settings.app_secret)
        params["sign"] = sign
        
        # Gọi API
        api_url = f"{Base_URL}{api_path}"
        response = requests.get(api_url, params=params, timeout=15)
        
        # Kiểm tra phản hồi
        if response.status_code != 200:
            frappe.log_error(f"Lỗi khi gọi API Lazada: {response.status_code} - {response.text}", "Lazada Order API Error")
            return {"success": False, "message": f"API error: {response.status_code}", "response": response.text}
            
        # Phân tích phản hồi
        result = response.json()
        
        # Kiểm tra mã lỗi
        if result.get("code") != "0":
            error_msg = result.get("message", "Unknown error")
            frappe.log_error(f"Lỗi từ Lazada API: {error_msg}", "Lazada Order API Error")
            return {"success": False, "message": error_msg, "response": result}
            
        # Trả về dữ liệu đơn hàng
        return {
            "success": True,
            "data": result.get("data", {}),
            "response": result
        }
        
    except Exception as e:
        frappe.log_error(f"Lỗi khi lấy thông tin đơn hàng Lazada: {str(e)}", "Lazada Order API Error")
        return {"success": False, "message": str(e)}


def get_orders_from_lazada():
    """
    Lấy danh sách đơn hàng từ Lazada API sử dụng endpoint /orders/get
    
    Returns:
        dict: Thông tin đơn hàng từ Lazada API
    """
    try:
        # Lấy cấu hình Lazada nếu không được cung cấp
        lazada_settings = get_lazada_setting()
        
        if not lazada_settings:
            frappe.log_error("Không tìm thấy cấu hình Lazada", "Lazada Order API Error")
            return {"success": False, "message": "Lazada settings not found"}
        
        # Chuẩn bị tham số cho API
        api_path = "/orders/get"
        
        # Lấy ngày hiện tại và định dạng theo yêu cầu của Lazada (YYYY-MM-DDThh:mm:ss+07:00)
        current_date = datetime.now()
        yesterday = current_date - timedelta(days=1)
        formatted_date = yesterday.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        
        params = {
            "app_key": lazada_settings.app_key,
            "timestamp": str(int(time.time() * 1000)),
            "access_token": lazada_settings.access_token,
            "sign_method": "sha256",
            "update_after": formatted_date,
            "created_after": formatted_date,
            "sort_direction": "DESC"
        }   
        
        # Tạo chữ ký
        sign = generate_lazada_sign(api_path, params, lazada_settings.app_secret)
        params["sign"] = sign
        
        # Gọi API
        api_url = f"{Base_URL}{api_path}"   
        response = requests.get(api_url, params=params, timeout=15)
        
        # Kiểm tra phản hồi
        if response.status_code != 200:
            frappe.log_error(f"Lỗi khi gọi API Lazada: {response.status_code} - {response.text}", "Lazada Order API Error")
            return {"success": False, "message": f"API error: {response.status_code}", "response": response.text}   
        
        # Phân tích phản hồi
        result = response.json()
        
        # Kiểm tra mã lỗi
        if result.get("code") != "0":   
            error_msg = result.get("message", "Unknown error")
            frappe.log_error(f"Lỗi từ Lazada API: {error_msg}", "Lazada Order API Error")
            return {"success": False, "message": error_msg, "response": result}
        
        # Trả về dữ liệu đơn hàng
        return {
            "success": True,
            "data": result.get("data", {}),
            "response": result
        }
        
    except Exception as e:  
        frappe.log_error(f"Lỗi khi lấy danh sách đơn hàng Lazada: {str(e)}", "Lazada Order API Error")
        return {"success": False, "message": str(e)}            
    
    
def get_lazada_order_items(order_id, lazada_settings=None):
    """
    Lấy thông tin chi tiết các sản phẩm trong đơn hàng từ Lazada API sử dụng endpoint /order/items/get
    
    Args:
        order_id (str): ID của đơn hàng cần lấy thông tin sản phẩm
        lazada_settings (dict, optional): Cấu hình Lazada. Nếu không cung cấp, sẽ lấy từ get_lazada_setting()
        
    Returns:
        dict: Thông tin sản phẩm trong đơn hàng từ Lazada API
    """
    try:
        # Lấy cấu hình Lazada nếu không được cung cấp
        if not lazada_settings:
            lazada_settings = get_lazada_setting()
            
        if not lazada_settings:
            frappe.log_error("Không tìm thấy cấu hình Lazada", "Lazada Order API Error")
            return {"success": False, "message": "Lazada settings not found"}
            
        # Chuẩn bị tham số cho API
        api_path = "/order/items/get"
        params = {
            "app_key": lazada_settings.app_key,
            "timestamp": str(int(time.time() * 1000)),
            "order_id": order_id,
            "sign_method": "sha256",
            "access_token": lazada_settings.access_token
        }
        
        # Tạo chữ ký
        sign = generate_lazada_sign(api_path, params, lazada_settings.app_secret)
        params["sign"] = sign
        
        # Gọi API
        api_url = f"{Base_URL}{api_path}"
        response = requests.get(api_url, params=params, timeout=15)
        
        # Kiểm tra phản hồi
        if response.status_code != 200:
            frappe.log_error(f"Lỗi khi gọi API Lazada: {response.status_code} - {response.text}", "Lazada Order API Error")
            return {"success": False, "message": f"API error: {response.status_code}", "response": response.text}
            
        # Phân tích phản hồi
        result = response.json()
        
        # Kiểm tra mã lỗi
        if result.get("code") != "0":
            error_msg = result.get("message", "Unknown error")
            frappe.log_error(f"Lỗi từ Lazada API: {error_msg}", "Lazada Order API Error")
            return {"success": False, "message": error_msg, "response": result}
            
        # Trả về dữ liệu sản phẩm trong đơn hàng
        return {
            "success": True,
            "data": result.get("data", {}),
            "response": result
        }
        
    except Exception as e:
        frappe.log_error(f"Lỗi khi lấy thông tin sản phẩm đơn hàng Lazada: {str(e)}", "Lazada Order API Error")
        return {"success": False, "message": str(e)}            
    
    