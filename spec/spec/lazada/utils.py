import frappe
import hmac
import hashlib
import hmac
import hashlib
from urllib.parse import urlencode
import time
from lazop import LazopClient, LazopRequest
import requests
import os
import tempfile


Base_URL = "https://api.lazada.vn/rest"


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

def refresh_lazada_access_token():
    """Làm mới access token của Lazada và cập nhật vào Lazada Setting."""
    try:
        # Lấy cấu hình Lazada từ get_lazada_setting
        lazada_settings = get_lazada_setting()
        
        if not lazada_settings:
            frappe.log_error("Không tìm thấy cấu hình Lazada.", "Lazada Token Refresh Error")
            return

        # Kiểm tra nếu không có refresh_token
        if not lazada_settings.refresh_token:
            frappe.log_error(f"Lazada Setting không có refresh_token.", "Lazada Token Refresh Error")
            return

        # Kiểm tra thời gian hết hạn của access_token (nếu có)
        if lazada_settings.access_token_expiry:
            current_time = int(time.time())
            if current_time < int(lazada_settings.access_token_expiry) - 300:  # Làm mới trước 5 phút
                frappe.logger().info(f"Access token vẫn còn hiệu lực đến {lazada_settings.access_token_expiry}. Bỏ qua.")
                return

        try:
            # Ghi log chi tiết
            frappe.logger().info(f"Bắt đầu làm mới access token cho Lazada Setting...")
            current_time = int(time.time())
            frappe.logger().info(f"Thời gian hiện tại (Unix timestamp): {current_time}")

            # Khởi tạo LazopClient và gửi yêu cầu
            client = LazopClient('https://api.lazada.com/rest', lazada_settings.app_key, lazada_settings.app_secret)
            request = LazopRequest('/auth/token/refresh')
            request.add_api_param('refresh_token', lazada_settings.refresh_token)

            frappe.logger().info(f"Gửi yêu cầu làm mới token với refresh_token: {lazada_settings.refresh_token}")
            response = client.execute(request)

            # Ghi log phản hồi
            frappe.logger().info(f"Phản hồi từ Lazada API: {response.body}")

            # Kiểm tra phản hồi
            if response.code != '0':
                frappe.log_error(f"Lỗi khi làm mới token: {response.message}", "Lazada Token Refresh Error")
                raise Exception(f"Refresh token error: {response.message}")

            # Lấy thông tin từ phản hồi
            data = response.body
            access_token = data.get('access_token')
            refresh_token = data.get('refresh_token', lazada_settings.refresh_token)  # Giữ nguyên nếu không có mới

            if not access_token:
                frappe.log_error("Không tìm thấy access_token trong phản hồi từ Lazada", "Lazada Token Refresh Error")
                raise KeyError("Access token not found in response")

            frappe.logger().info(f"Access Token mới: {access_token}")
            frappe.logger().info(f"Refresh Token: {refresh_token}")

            # Xác định thời gian hết hạn
            if "expires_in" in data:
                access_token_expiry = current_time + data["expires_in"]
            else:
                frappe.log_error("Không có thông tin thời gian hết hạn (expires_in) trong phản hồi", "Lazada Token Refresh Error")
                raise KeyError("expires_in not found in response")

            # Theo tài liệu API Lazada, refresh_token_expiry thường có trong phản hồi
            refresh_token_expiry = data.get("refresh_expires_in", lazada_settings.get("refresh_token_expiry"))
            if refresh_token_expiry:
                refresh_token_expiry = current_time + refresh_token_expiry

            frappe.logger().info(f"Thời gian hết hạn Access Token: {access_token_expiry}")
            frappe.logger().info(f"Thời gian hết hạn Refresh Token: {refresh_token_expiry if refresh_token_expiry else 'Không có'}")

            # Cập nhật trực tiếp vào đối tượng lazada_settings
            lazada_settings.access_token = access_token
            lazada_settings.refresh_token = refresh_token
            lazada_settings.access_token_expiry = access_token_expiry
            lazada_settings.refresh_token_expiry = refresh_token_expiry if refresh_token_expiry else None
            lazada_settings.time_now = frappe.utils.now_datetime()
            
            # Lưu thay đổi
            lazada_settings.save(ignore_permissions=True)
            
            # Commit thay đổi vào database
            frappe.db.commit()
            frappe.logger().info("Đã cập nhật access token mới và commit vào database")

            # Ghi log thành công
            frappe.logger().info(f"Đã làm mới Access Token cho Lazada Setting.")

        except Exception as e:
            frappe.log_error(f"Lỗi khi làm mới token: {str(e)}", "Lazada Token Refresh Error")
            raise
            
    except Exception as e:
        frappe.log_error(f"Lỗi khi làm mới token: {str(e)}", "Lazada Token Refresh Error")
        raise

def get_lazada_setting(shop_name='Lazada'):
    """
    Lấy thông tin cấu hình Lazada từ Doctype "Lazada Setting".
    Trả về một danh sách các bản ghi với các trường cần thiết.
    """
    try:
        lazada_settings = frappe.get_doc("Platform Account",shop_name)
        return lazada_settings
    except Exception as e:
        frappe.log_error(f"Error fetching Lazada settings: {str(e)}")
        return []
    
def download_image(image_path):
    """Tải ảnh từ ERPNext về local tạm thời."""
    print(f"Downloading image: {image_path}")
    full_url = frappe.utils.get_url(image_path)
    if image_path.startswith("/private"):
        token = frappe.generate_hash(image_path, 10)
        full_url = f"{full_url}?token={token}"
    
    temp_file_name = f"temp_{image_path.split('/')[-1]}"
    temp_path = frappe.get_site_path("public", "files", temp_file_name)
    
    response = requests.get(full_url)
    if response.status_code == 200:
        with open(temp_path, "wb") as f:
            f.write(response.content)
        print(f"Image downloaded to: {temp_path}")
        return temp_path
    print(f"Failed to download image: {response.status_code}")
    return None

# Cache trong bộ nhớ
image_cache = {}

def load_image_cache():
    """Tải cache từ DocType Image Cache vào dictionary dựa trên image_hash."""
    print("Loading image cache from database...")
    try:
        cached_images = frappe.get_all(
            "Image Cache",
            fields=["image_path", "image_hash", "uri", "use_case"],
            filters={"use_case": ["in", ["MAIN_IMAGE", "ATTRIBUTE_IMAGE", "DESCRIPTION_IMAGE", "SIZE_CHART", "CERTIFICATION"]]}
        )
        
        print(f"Found {len(cached_images)} cached images in database")
        
        for img in cached_images:
            if img.image_hash:  # Chỉ lưu nếu có hash
                cache_key = (img.image_hash, img.use_case)
                image_cache[cache_key] = img.uri
                print(f"Loaded cache entry: {cache_key} -> {img.uri}")
        
        print(f"Image cache loaded with {len(image_cache)} entries")
    except Exception as e:
        print(f"Error loading image cache: {str(e)}")
        frappe.log_error(f"Error loading image cache: {str(e)}", "Image Cache Error")

def save_to_image_cache(image_path, image_hash, uri, use_case):
    """Lưu URI vào DocType Image Cache với image_hash."""
    print(f"Attempting to save to image cache: {image_path}, {image_hash}, {uri}, {use_case}")
    
    if not image_path:
        print("Error: image_path is empty")
        return
        
    if not image_hash:
        print("Error: image_hash is empty")
        return
        
    if not use_case:
        print("Error: use_case is empty")
        return
    
    try:
        # Check if the record already exists
        existing = frappe.get_all(
            "Image Cache",
            filters={"image_path": image_path, "use_case": use_case},
            fields=["name"]
        )
        
        if existing:
            print(f"Updating existing image cache record: {existing[0]['name']}")
            doc = frappe.get_doc("Image Cache", existing[0]["name"])
        else:
            print("Creating new image cache record")
            doc = frappe.new_doc("Image Cache")
            doc.image_path = image_path
            doc.use_case = use_case
        
        # Set the fields
        doc.image_hash = image_hash
        doc.uri = uri
        doc.last_updated = frappe.utils.now()
        
        # Validate the document before saving
        
        # Save the document
        doc.save()
        print(f"Successfully saved image cache record: {doc.name}")
        
        # Update memory cache if we have valid data
        if image_hash and uri:
            cache_key = (image_hash, use_case)
            image_cache[cache_key] = uri
            print(f"Updated memory cache with key {cache_key}: {uri}")
            
        # Commit the transaction to ensure it's saved
        frappe.db.commit()
        print("Database transaction committed")
        
    except Exception as e:
        print(f"Error saving to Image Cache: {str(e)}")
        frappe.log_error(f"Error saving to Image Cache: {str(e)}", "Image Cache Error")
        # Rollback the transaction in case of error
        frappe.db.rollback()
        print("Database transaction rolled back due to error")

def upload_image_lazada(image_path, use_case="MAIN_IMAGE"):
    """
    Upload an image to Lazada and return the image URL.
    
    Args:
        image_path: Path to the image file
        use_case: Use case for the image (MAIN_IMAGE, ATTRIBUTE_IMAGE, etc.)
        
    Returns:
        str: URL of the uploaded image or None if upload failed
    """
    try:
        # Check if we have a cached result
        cache_key = f"{image_path}_{use_case}"
        if hasattr(upload_image_lazada, "cache") and cache_key in upload_image_lazada.cache:
            return upload_image_lazada.cache[cache_key]
            
        # Initialize cache if not exists
        if not hasattr(upload_image_lazada, "cache"):
            upload_image_lazada.cache = {}
            
        # Get Lazada settings
        lazada_setting = get_lazada_setting()
        if not lazada_setting:
            print("Lazada settings not found")
            return None
            
        # Download the image to a temporary file
        import os
        import tempfile
        import requests
        from urllib.parse import urlencode
        
        # Create a temporary file
        temp_file = None
        try:
            # If image_path is a URL, download it
            if image_path.startswith(('http://', 'https://')):
                response = requests.get(image_path)
                if response.status_code != 200:
                    print(f"Failed to download image from {image_path}")
                    return None
                    
                # Create a temporary file with the correct extension
                ext = os.path.splitext(image_path)[1] or '.jpg'
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                temp_file.write(response.content)
                temp_file.close()
                local_path = temp_file.name
            else:
                # If image_path is a local path, use it directly
                if not os.path.exists(image_path):
                    print(f"Image file not found: {image_path}")
                    return None
                local_path = image_path
                
            print(f"Image downloaded to: {local_path}")
            
            # Prepare the API request
            api_path = "/image/upload"
            params = {
                "app_key": lazada_setting.app_key,
                "sign_method": "sha256",
                "access_token": lazada_setting.access_token,
                "timestamp": str(int(time.time() * 1000)),
                "image": local_path,
                "use_case": use_case
            }
            
            # Generate signature
            sign = generate_lazada_sign(api_path, params, lazada_setting.app_secret)
            params["sign"] = sign
            
            # Build the URL
            url = f"{Base_URL}{api_path}?{urlencode(params)}"
            print(f"Sending image upload request to Lazada API: {url}")
            
            # Send the request
            response = requests.post(url)
            print(f"Image upload response status code: {response.status_code}")
            print(f"Image upload response content: {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("code") == "0" or response_data.get("code") == 0:
                    image_url = response_data.get("data", {}).get("image", {}).get("url")
                    if image_url:
                        # Cache the result
                        upload_image_lazada.cache[cache_key] = image_url
                        return image_url
                    else:
                        print("No image URL in response")
                else:
                    print(f"Lazada API error: {response_data.get('message', 'Unknown error')}")
            else:
                print(f"HTTP error {response.status_code}: {response.text}")
                
        finally:
            # Clean up the temporary file
            if temp_file and os.path.exists(temp_file.name):
                print(f"Cleaned up: {temp_file.name}")
                os.unlink(temp_file.name)
                
        return None
    except Exception as e:
        print(f"Error uploading image to Lazada: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def get_category_id(item_group,platform):
    """Lấy category_id từ Item Group."""
    print(f"Fetching category for {item_group}")
    group_categories = frappe.get_all(
        "Item Group Category",
        filters={"parent": item_group, "parenttype": "Item Group", "ecommerce_platform": platform},
        fields=["marketplace_category"],
        limit=1
    )
    if not group_categories:
        print(f"No {platform} category mapping for {item_group}")
        return None
    
    # Get the marketplace_category reference
    marketplace_category = group_categories[0]["marketplace_category"]
    if not marketplace_category:
        print(f"No marketplace category set for {item_group}")
        return None
    
    # Get the actual category_id from Market Category
    market_category = frappe.get_doc("Market Category", marketplace_category)
    if not market_category:
        print(f"Market Category {marketplace_category} not found")
        return None
    
    # Return the category_id, not the category name
    return market_category.category_id


load_image_cache()