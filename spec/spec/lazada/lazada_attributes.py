import requests
import time
import frappe
from spec.spec.lazada.utils import generate_lazada_sign, get_lazada_setting, Base_URL
from urllib.parse import urlencode

# Hàm lấy thuộc tính của danh mục
@frappe.whitelist()
def get_category_attributes(category_id):
    """
    Lấy thuộc tính của danh mục từ Lazada
    """
    try:
        # Lấy các trường cần thiết từ Lazada Setting
        lazada_setting = get_lazada_setting()
        if not lazada_setting:
            frappe.log_error("Lazada Setting không được cấu hình.")
            return []

        api_path = f"/category/attributes/get"
        params = {
            "primary_category_id": category_id,
            "app_key": lazada_setting.app_key,
            "sign_method": "sha256",
            "access_token": lazada_setting.access_token,
            "timestamp": str(int(time.time() * 1000)),
            "language_code": 'vi_VN',
        }
        
        sign = generate_lazada_sign(api_path, params, lazada_setting.app_secret)
        params["sign"] = sign
        
        url = f"{Base_URL}{api_path}?{urlencode(params)}"
        print(url)
        response = requests.get(url)
        response_data = response.json()
        if response_data.get("code") != "0":
            frappe.log_error(f"Error fetching category attributes: {response_data.get('message')}")
            return []
        
        return response_data.get("data", {})
    
    except Exception as e:
        frappe.log_error(f"Error in get_category_attributes: {str(e)}")
        return []

def sync_lazada_attributes(category_id):
    """
    Hàm xử lý đồng bộ attributes từ Lazada
    """
    try:
        # Lấy attributes từ Lazada
        attributes = get_category_attributes(category_id)
        if not attributes:
            frappe.msgprint(f"Không tìm thấy attributes cho category {category_id} trên Lazada")
            return

        # Cập nhật attributes vào Marketplace Attribute
        for attr in attributes:
            update_marketplace_attribute(attr)
        frappe.db.commit()
        frappe.msgprint(f"Đã đồng bộ thành công attributes cho category {category_id}")
        
    except Exception as e:
        # Use a shorter error message
        frappe.log_error(f"Error in sync_lazada_attributes: {str(e)[:50]}", "Lazada Attribute Sync")
        frappe.throw(f"Lỗi khi đồng bộ attributes: {str(e)[:50]}")

def update_marketplace_attribute(attr):
    """
    Cập nhật hoặc tạo mới attribute trong Marketplace Attribute
    """
    try:
        attribute_id = attr.get("id")
        if not attribute_id:
            # Use a shorter error message
            frappe.log_error("No attribute_id found in attribute data", "Lazada Attribute Sync")
            return 

        # Kiểm tra attribute đã tồn tại chưa
        existing = frappe.get_all("Marketplace Attribute",
            filters={"marketplace": "Lazada", "attribute_id": attribute_id},
            limit=1
        )
        
        # Kiểm tra nếu attribute_type là SKU
        is_sku = "SALES_PROPERTY" if attr.get("attribute_type") == "sku" else "PRODUCT_PROPERTY"
        
        if not existing:
            # Tạo mới attribute
            attr_doc = frappe.get_doc({
                "doctype": "Marketplace Attribute",
                "marketplace": "Lazada",
                "attribute_id": attr.get("id"),
                "attribute_name": attr.get("name"),
                "type": is_sku,
                "label": attr.get("label"),
                "is_customizable": 0,
                "is_variants": attr.get("is_sale_prop", 0)

            })
            attr_doc.insert(ignore_permissions=True)
            frappe.logger().info(f"Added attribute {attribute_id} for Lazada")
        else:
            frappe.logger().info(f"Attribute {attribute_id} already exists, skipping.")
        
            
    except Exception as e:
        # Use a shorter error message
        frappe.log_error(f"Error in update_marketplace_attribute: {str(e)[:50]}", "Lazada Attribute Sync")


def get_attributes_mandatory_category(category_id):
    """
    Lấy danh sách các thuộc tính bắt buộc (is_mandatory=1) của một danh mục từ Lazada
    
    Args:
        category_id (str): ID của danh mục cần lấy thuộc tính
        
    Returns:
        list: Danh sách các thuộc tính bắt buộc, mỗi phần tử là dict chứa id và name
    """
    try:
        # Lấy tất cả thuộc tính của danh mục
        attributes = get_category_attributes(category_id)
        if not attributes:
            frappe.log_error(f"Không tìm thấy thuộc tính cho danh mục {category_id}", "Lazada Attribute Sync")
            return []
        
        # Lọc các thuộc tính có is_mandatory=1
        mandatory_attributes = []
        for attr in attributes:
            if attr.get("is_mandatory") == 1:
                mandatory_attributes.append({
                    "id": attr.get("id"),
                    "name": attr.get("name")
                })
        
        return mandatory_attributes
    
    except Exception as e:
        frappe.log_error(f"Lỗi trong get_attributes_mandatory_category: {str(e)[:50]}", "Lazada Attribute Sync")
        return []




