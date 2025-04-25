from frappe import get_doc, db
import frappe
import hmac
import hashlib
import hmac
import hashlib
import requests
from urllib.parse import urlencode
import time
import re

@frappe.whitelist()
def get_template_lines(item_group):
    """
    Lấy danh sách Specification Template Line dựa trên item_group.
    """
    template = db.get_value("Specification Template", 
                           {"item_group": item_group}, 
                           "name")
    if template:
        template_doc = get_doc("Specification Template", template)
        lines = [{
            "spec_name": line.spec_name,
            "data_type": line.data_type,
            "default_value": line.default_value
        } for line in template_doc.template_line]
        print(lines)
        return {"lines": lines}
    return {"lines": []}

import frappe


def generate_lazada_sign(api_path, params, app_secret):
    """
    Tạo chữ ký (sign) cho API của Lazada theo quy trình được cung cấp.
    
    :param api_path: Đường dẫn API (ví dụ: /test/api)
    :param params: Dictionary chứa các tham số (trừ sign và tham số kiểu mảng byte)
    :param app_secret: App Secret do Lazada cung cấp
    :return: Chữ ký (sign) dưới dạng hex uppercase
    """ 
    # Bước 1: Sắp xếp các tham số theo thứ tự bảng ASCII
    # Loại bỏ tham số 'sign' và các tham số kiểu mảng byte (nếu có)
    filtered_params = {k: v for k, v in params.items() if k != 'sign' and not isinstance(v, bytes)}
    sorted_params = sorted(filtered_params.items(), key=lambda x: x[0])
    
    # Bước 2: Nối các tham số thành chuỗi
    param_string = ''
    for key, value in sorted_params:
        param_string += str(key) + str(value)
    
    # Bước 3: Thêm tên API vào đầu chuỗi
    sign_string = api_path + param_string
    
    # Bước 4: Mã hóa chuỗi và tạo bản tóm tắt bằng HMAC-SHA256
    # Mã hóa chuỗi thành UTF-8
    sign_string_bytes = sign_string.encode('utf-8')
    app_secret_bytes = app_secret.encode('utf-8')
    
    # Tạo bản tóm tắt bằng HMAC-SHA256
    hmac_obj = hmac.new(
        app_secret_bytes,  # Khóa (app_secret)
        sign_string_bytes,  # Chuỗi cần mã hóa
        hashlib.sha256  # Thuật toán SHA256
    )
    
    # Bước 5: Chuyển đổi bản tóm tắt sang định dạng hex (uppercase)
    sign = hmac_obj.hexdigest().upper()
    
    return sign


@frappe.whitelist()
def get_category_suggestions(item_name, lazada_setting):
    """
    Lấy gợi ý danh mục từ Lazada dựa trên template_name và lazada_setting.
    Args:
        template_name (str): Tên của Specification Template.
        lazada_setting (str): Tên của bản ghi Lazada Setting.
    Returns:
        dict: Danh sách gợi ý danh mục dưới dạng {"lines": [...]}
    """
    try:
        # Lấy các trường cần thiết từ Lazada Setting
        app_key = frappe.db.get_value("Lazada Setting", lazada_setting, "app_key")
        access_token = frappe.db.get_value("Lazada Setting", lazada_setting, "access_token")
        app_secret = frappe.db.get_value("Lazada Setting", lazada_setting, "app_secret")

        if not (app_key and access_token and app_secret):
            frappe.log_error(f"Lazada Setting '{lazada_setting}' is not configured properly")
            return {"lines": []}

        api_path = "/product/category/suggestion/get"
        params = {
            "product_name": item_name,
            "app_key": app_key,
            "sign_method": "sha256",
            "access_token": access_token,
            "timestamp": str(int(time.time() * 1000)),
        }
        
        sign = generate_lazada_sign(api_path, params, app_secret)
        params["sign"] = sign
        
        base_url = 'https://api.lazada.vn/rest'
        url = f"{base_url}{api_path}?{urlencode(params)}"
        response = requests.get(url)
        response_data = response.json()
        
        if response_data.get("code") != "0":
            frappe.log_error(f"Error fetching category suggestions: {response_data.get('message')}")
            return {"lines": []}
        
        # Dữ liệu từ Lazada có dạng {"categorySuggestions": [...]}
        categories = response_data.get("data", {}).get("categorySuggestions", [])
        # Chuyển đổi thành định dạng {"lines": [...]}
        lines = [
            {
                "category_name": cat.get("categoryName"),
                "category_id": cat.get("categoryId"),
                "category_path": cat.get("categoryPath")
            }
            for cat in categories
        ]
        return {"lines": lines}
    
    except Exception as e:
        frappe.log_error(f"Error in get_category_suggestions: {str(e)}")
        return {"lines": []}



@frappe.whitelist()
def ensure_item_group(category_path):
    """
    Kiểm tra xem Item Group có tồn tại không, nếu không thì tạo mới với is_group = 1.
    Trả về tên của Item Group.
    """
    try:
        # Kiểm tra xem Item Group có tồn tại không
        # Xử lý ký tự đặc biệt trong category_path để tạo name hợp lệ
        # Thay thế '>' bằng '-', loại bỏ các ký tự đặc biệt và giữ lại chữ cái, số, dấu gạch nối
        clean_name = category_path.replace('>', '-').replace('<', '').replace('/', '-').replace(' ', '-')
        # Loại bỏ dấu nháy đơn và các ký tự không hợp lệ khác
        clean_name = re.sub(r"[^a-zA-Z0-9-]", "", clean_name.lower())
        # Đảm bảo name không quá dài (giới hạn của Frappe là 140 ký tự)
        clean_name = clean_name[:140]

        item_groups = frappe.get_all("Item Group", fields=["name", "item_group_name", "is_group"])

        # In kết quả
        for item_group in item_groups:
            print(item_group)
        print(clean_name)
        item_group = frappe.get_value("Item Group", {"name": clean_name}, "item_group_name")
        print(item_group)
        if item_group:
            return item_group

        # Tạo bản ghi mới
        new_item_group = frappe.get_doc({
            "doctype": "Item Group",
            "name": clean_name,  # Tạo name thủ công
            "item_group_name": clean_name,  # Giữ nguyên category_path gốc
            "is_group": 0,  # Bật is_group
            "parent_item_group": "All Item Groups"  # Parent mặc định
        })
        new_item_group.insert(ignore_permissions=False)  # Tôn trọng quyền truy cập
        
        frappe.db.commit()
        frappe.log(f"Đã tạo mới Item Group: {category_path} với name: {clean_name}")
        return new_item_group.name
        
    except Exception as e:
        frappe.log_error(f"Lỗi khi tạo Item Group {category_path}: {str(e)}", "Ensure Item Group Error")
        frappe.throw(("Không thể tạo hoặc lấy Item Group: {0}").format(clean_name))

@frappe.whitelist()
def get_category_attributes(primary_category_id, lazada_setting):
    """
    Lấy danh sách thuộc tính của một danh mục từ Lazada dựa trên primary_category_id và lazada_setting.
    Args:
        primary_category_id (str): ID của danh mục chính.
        lazada_setting (str): Tên của bản ghi Lazada Setting."
    """
    try: 
        app_key = frappe.db.get_value("Lazada Setting", lazada_setting, "app_key")
        access_token = frappe.db.get_value("Lazada Setting", lazada_setting, "access_token")
        app_secret = frappe.db.get_value("Lazada Setting", lazada_setting, "app_secret")

        if not (app_key and access_token and app_secret):
            frappe.log_error(f"Lazada Setting '{lazada_setting}' is not configured properly")
            return {"lines": []}
        api_path = "/category/attributes/get"
        params = {
            'primary_category_id': primary_category_id,
            'language_code': 'en_US',
            "app_key": app_key,
            "sign_method": "sha256",
            "access_token": access_token,
            "timestamp": str(int(time.time() * 1000)),
        }
        
        sign = generate_lazada_sign(api_path, params, app_secret)
        params["sign"] = sign
        
        base_url = 'https://api.lazada.vn/rest'
        url = f"{base_url}{api_path}?{urlencode(params)}"
        print("URL:", url)
    
        response = requests.get(url)
        return response.json()
    except Exception as e:
        frappe.log_error(f"Error in get_category_suggestions: {str(e)}")
        return {"lines": []}
    

