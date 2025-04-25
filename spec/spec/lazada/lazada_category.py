import frappe
from spec.spec.lazada.utils import generate_lazada_sign, get_lazada_setting, Base_URL
import time
from urllib.parse import urlencode
import requests
from collections import deque
import lazop

@frappe.whitelist()
def get_category_suggestions(item_name):
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
        lazada_setting = get_lazada_setting()
        if not lazada_setting:
            frappe.log_error("Lazada Setting không được cấu hình.")
            return {"lines": []}

        api_path = "/product/category/suggestion/get"
        params = {
            "product_name": item_name,
            "app_key": lazada_setting.app_key,
            "sign_method": "sha256",
            "access_token": lazada_setting.access_token,
            "timestamp": str(int(time.time() * 1000)),
        }
        
        sign = generate_lazada_sign(api_path, params, lazada_setting.app_secret)
        params["sign"] = sign
        
        url = f"{Base_URL}{api_path}?{urlencode(params)}"
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


def get_category_lazada():
    """
    Lấy danh sách danh mục từ Lazada.
    Returns:
        dict: Danh sách danh mục dưới dạng {"lines": [...]}
    """
    try:
        lazada_setting = get_lazada_setting()
        
        if not lazada_setting:
            frappe.log_error("Lazada Setting không được cấu hình.")
            return {"lines": []}
        api_path = "/category/tree/get"
        params = {
            "app_key": lazada_setting.app_key,
            "sign_method": "sha256",
            "access_token": lazada_setting.access_token,
            "timestamp": str(int(time.time() * 1000)),
            "language_code": 'en_US',
        }
        
        sign = generate_lazada_sign(api_path, params, lazada_setting.app_secret)
        params["sign"] = sign
        
        url = f"{Base_URL}{api_path}?{urlencode(params)}"
        response = requests.get(url)
        response_data = response.json()

        if response_data.get("code") != "0":
            frappe.log_error(f"Error fetching category: {response_data.get('message')}")
            return {"lines": []}
        
        
        return response_data
    except Exception as e:
        frappe.log_error(f"Error in get_category: {str(e)}")
        return {"lines": []}


def add_category(marketplace='Lazada'):
    """
    Thêm danh mục từ Lazada vào Marketplace Category
    """
    try:
        category_data = get_category_lazada()
        if not category_data.get("data"):
            frappe.msgprint("Không tìm thấy danh mục từ API Lazada.")
            return
        
        # Clear existing categories for Lazada
        frappe.db.sql("DELETE FROM `tabMarketplace Category` WHERE marketplace = 'Lazada'")
        frappe.db.commit()
        print("Cleared existing Lazada categories from Marketplace Category")

        # Create root category for Lazada
        root_category_id = f"lazada_root"
        root_name_view = 'Lazada Root'
        
        root_doc = frappe.new_doc("Marketplace Category")
        root_doc.name_view = root_name_view
        root_doc.category_name = "Lazada Root"
        root_doc.category_id = root_category_id
        root_doc.marketplace = marketplace
        root_doc.is_leaf = 0
        root_doc.is_group = 1
        root_doc.permission_status = "AVAILABLE"
        root_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"Created root category: {root_name_view}")

        # Use BFS to traverse and save categories
        categories = category_data.get("data", [])
        queue = deque()  # Queue for BFS
        
        # Add root document to be parent of top-level categories
        root_doc = {
            "name": root_name_view,  # Name of root document (Marketplace Category)
            "children": categories
        }
        queue.append((root_doc, None))  # (node, parent_doc_name)
        
        # Track processed categories to avoid duplicates
        processed_categories = set()
        
        while queue:
            # Get a node from the queue
            current_node, parent_doc_name = queue.popleft()
            
            # Skip if node has no children
            if "children" not in current_node:
                continue
            
            # Process all child categories of current node
            for category in current_node["children"]:
                # Determine if category is a group (not a leaf)
                is_group = not category.get("leaf", True)
                
                # Get category name and check if already processed
                if parent_doc_name is None:
                    # Top-level category
                    category_name = category.get('name')
                    name_view = f"Lazada - {category_name}"
                else:
                    # Child category, include parent in name
                    category_name = category.get('name')
                    name_view = f"{parent_doc_name} _ {category_name}"
                
                if name_view in processed_categories:
                    print(f"Skipping duplicate category: {name_view}")
                    continue
                    
                processed_categories.add(name_view)
                
                # Create new document for category
                new_category = frappe.new_doc("Marketplace Category")
                new_category.name_view = name_view
                new_category.marketplace = marketplace
                new_category.category_id = category.get("category_id")
                new_category.category_name = category_name
                new_category.is_leaf = category.get("leaf", True)
                new_category.is_group = is_group
                new_category.permission_status = "AVAILABLE"
                
                # Set parent category
                if parent_doc_name:
                    new_category.parent_marketplace_category = parent_doc_name
                
                # Save document with ignore_if_duplicate=True to handle duplicates gracefully
                try:
                    new_category.insert(ignore_permissions=True, ignore_if_duplicate=True)
                    frappe.db.commit()
                    # print(f"Added category: {name_view}")
                except frappe.DuplicateEntryError:
                    print(f"Duplicate category skipped: {name_view}")
                    continue
                except Exception as insert_error:
                    print(f"Error inserting category {name_view}: {str(insert_error)}")
                    continue
                
                # If category has children, add to queue for further traversal
                if "children" in category:
                    queue.append((category, new_category.name_view))
        
        frappe.msgprint("Đã đồng bộ thành công các danh mục từ Lazada.")
    
    except Exception as e:
        # Use a shorter error message to avoid character length exceeded error
        error_msg = f"Lỗi đồng bộ danh mục: {str(e)[:100]}"
        frappe.log_error(error_msg, "Lazada Category Sync Error")
        frappe.throw(error_msg)

@frappe.whitelist()
def get_category_suggestions(item_name):
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
        lazada_setting = get_lazada_setting()
        api_path = "/product/category/suggestion/get"
        params = {
            "product_name": item_name,
            "app_key": lazada_setting.app_key,
            "sign_method": "sha256",
            "access_token": lazada_setting.access_token,
            "timestamp": str(int(time.time() * 1000)),
        }
        
        sign = generate_lazada_sign(api_path, params, lazada_setting.app_secret)
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
        print(lines[0])
        return {"lines": lines[0]}
    
    except Exception as e:
        frappe.log_error(f"Error in get_category_suggestions: {str(e)}")
        return {"lines": []}




def run_sync():
    add_category()

if __name__ == "__main__":
    run_sync()

