import requests
import time
import frappe
from spec.spec.lazada.utils import generate_lazada_sign, get_lazada_setting, Base_URL, upload_image_lazada, get_category_id
from urllib.parse import urlencode

def delete_product(seller_sku_list, sku_id_list=None, shop_name='Lazada'):
    """delete a product from Lazada marketplace."""
    lazada_setting = get_lazada_setting(shop_name)
    if not lazada_setting:
        return None
    api_path = "/product/remove"
    params = {
        "app_key": lazada_setting.app_key,
        "sign_method": "sha256",
        "access_token": lazada_setting.access_token,
        "timestamp": str(int(time.time() * 1000)),
    }

    if seller_sku_list:
        params['seller_sku_list'] = seller_sku_list
    
    if sku_id_list:
        params['sku_id_list'] = sku_id_list
        
    sign = generate_lazada_sign(api_path, params, lazada_setting.app_secret)
    params["sign"] = sign
    url = f"{Base_URL}{api_path}?{urlencode(params)}"
    
    try:
        print(f"Sending delete request to Lazada API: {url}")
        response = requests.post(url)
        print(f"Delete response status code: {response.status_code}")
        print(f"Delete response content: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('code') == "0" or response_data.get('code') == 0:
                print(f"Successfully deleted Lazada product with response: {response_data}")
                return response_data
            else:
                error_message = f"Lazada API error: {response_data.get('message', 'Unknown error')}"
                print(error_message)
                frappe.log_error(error_message, "Lazada Product Deletion")
                return None
        else:
            error_message = f"HTTP error {response.status_code}: {response.text}"
            print(error_message)
            frappe.log_error(error_message, "Lazada Product Deletion")
            return None
    except Exception as e:
        error_message = f"Error removing Lazada product: {str(e)}"
        print(error_message)
        frappe.log_error(error_message, "Lazada Product Deletion")
        return None

def create_lazada_product(product_data, shop_name='Lazada'):
    """Create a new product on Lazada marketplace."""
    lazada_setting = get_lazada_setting(shop_name)
    if not lazada_setting:
        return None
    
    api_path = "/product/create"
    params = {
        "app_key": lazada_setting.app_key,
        "sign_method": "sha256",
        "access_token": lazada_setting.access_token,
        "timestamp": str(int(time.time() * 1000)),
        "payload": product_data,
    }

    sign = generate_lazada_sign(api_path, params, lazada_setting.app_secret)
    params["sign"] = sign
    url = f"{Base_URL}{api_path}?{urlencode(params)}"
    
    try:
        print(f"Sending request to Lazada API: {url}")
        print(f"Request payload: {product_data}")
        response = requests.post(url)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('code') == "0" or response_data.get('code') == 0:
                print(f"Successfully created Lazada product with response: {response_data}")
                return response_data
            else:
                error_message = f"Lazada API error: {response_data.get('message', 'Unknown error')}"
                print(error_message)
                frappe.log_error(error_message, "Lazada Product Creation")
                return None
        else:
            error_message = f"HTTP error {response.status_code}: {response.text}"
            print(error_message)
            frappe.log_error(error_message, "Lazada Product Creation")
            return None
    except Exception as e:
        error_message = f"Error creating Lazada Product: {str(e)}"
        print(error_message)
        frappe.log_error(error_message, "Lazada Product Creation")
        return None

def update_product(product_id, product_data, shop_name='Lazada'):
    """Update product information on Lazada marketplace."""
    lazada_setting = get_lazada_setting(shop_name)
    if not lazada_setting:
        return None
    
    # Extract the product data from the original payload
    original_product = product_data.get("Request", {}).get("Product", {})
    
    # Create the correct payload structure for update API
    update_payload = {
        "Request": {
            "Product": {
                "ItemId": str(product_id),  # Convert to string to ensure compatibility
                "Attributes": original_product.get("Attributes", {}),
                "Skus": {
                    "Sku": []
                }
            }
        }
    }
    
    # Process SKUs to ensure correct field names
    if "Skus" in original_product and "Sku" in original_product["Skus"]:
        for sku in original_product["Skus"]["Sku"]:
            # Create a new SKU object with correct field names
            new_sku = {}
            
            # Get the SKU ID from SKU Mapping if available
            seller_sku = sku.get("SellerSku")
            if seller_sku:
                # Try to find SKU mapping
                sku_mapping = frappe.db.get_value(
                    "SKU Mapping",
                    {"seller_sku": seller_sku},
                    ["sku_id"]
                )
                
                if sku_mapping:
                    # Use the SKU ID from mapping
                    new_sku["SkuId"] = sku_mapping
                else:
                    # Fallback to using SellerSku as SkuId
                    new_sku["SkuId"] = seller_sku
            else:
                # If no SellerSku, skip this SKU
                continue
            
            # Copy other fields with correct casing
            for key, value in sku.items():
                if key != "SellerSku":  # Skip SellerSku as we've already mapped it
                    # Keep original casing for other fields
                    new_sku[key] = value
            
            update_payload["Request"]["Product"]["Skus"]["Sku"].append(new_sku)
    
    # Remove any fields that shouldn't be in the update payload
    if "PrimaryCategory" in update_payload["Request"]["Product"]:
        del update_payload["Request"]["Product"]["PrimaryCategory"]
    
    # If there are no attributes or skus, remove those sections
    if not update_payload["Request"]["Product"]["Attributes"]:
        del update_payload["Request"]["Product"]["Attributes"]
    
    if not update_payload["Request"]["Product"]["Skus"]["Sku"]:
        del update_payload["Request"]["Product"]["Skus"]
    
    api_path = "/product/update"
    params = {
        "app_key": lazada_setting.app_key,
        "sign_method": "sha256",
        "access_token": lazada_setting.access_token,
        "timestamp": str(int(time.time() * 1000)),
        "payload": update_payload,
    }

    sign = generate_lazada_sign(api_path, params, lazada_setting.app_secret)
    params["sign"] = sign
    url = f"{Base_URL}{api_path}?{urlencode(params)}"
    
    try:
        print(f"Sending update request to Lazada API: {url}")
        print(f"Update payload: {update_payload}")
        response = requests.post(url)
        print(f"Update response status code: {response.status_code}")
        print(f"Update response content: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('code') == "0" or response_data.get('code') == 0:
                print(f"Successfully updated Lazada product with response: {response_data}")
                return response_data
            else:
                error_message = f"Lazada API error: {response_data.get('message', 'Unknown error')}"
                print(error_message)
                frappe.log_error(error_message, "Lazada Product Update")
                return None
        else:
            error_message = f"HTTP error {response.status_code}: {response.text}"
            print(error_message)
            frappe.log_error(error_message, "Lazada Product Update")
            return None
    except Exception as e:
        error_message = f"Error updating Lazada Product: {str(e)}"
        print(error_message)
        frappe.log_error(error_message, "Lazada Product Update")
        return None

def update_price(product_id, price):
    """Update product price on Lazada marketplace."""
    # Implementation needed
    pass

def get_item_price(item_code, price_list="Standard Selling"):
    """Get item price from Frappe database."""
    price_data = frappe.db.get_value(
        "Item Price",
        {
            "item_code": item_code,
            "price_list": price_list,
            "selling": 1
        },
        ["price_list_rate", "currency"]
    )
    if price_data:
        price, currency = price_data
        return price, currency
    return None, None

def prepare_main_images(item, default_image_url=""):
    main_images = []
    if item.image:
        main_image_uri = upload_image_lazada(item.image, use_case="MAIN_IMAGE") or default_image_url
        main_images.append({"uri": main_image_uri})
    else:
        main_images.append({"uri": default_image_url})
    return main_images

# Hàm phụ trợ chuẩn bị ảnh bổ sung
def prepare_additional_images(item):
    additional_images = []
    for i in range(1, 6):
        attach_field = f"custom_attach_image_{i}" if i > 1 else "custom_attach_image"
        if hasattr(item, attach_field) and getattr(item, attach_field):
            uri = upload_image_lazada(getattr(item, attach_field), use_case="DESCRIPTION_IMAGE") or None
            if uri:
                additional_images.append({"uri": uri})
    for i in range(1, 9):
        attach_field = f"custom_attach_360_image_{i}"
        if hasattr(item, attach_field) and getattr(item, attach_field) and len(additional_images) < 9:
            uri = upload_image_lazada(getattr(item, attach_field), use_case="DESCRIPTION_IMAGE") or None
            if uri:
                additional_images.append({"uri": uri})
    return additional_images[:9] # Lazada limits to 9 additional images

def get_variant_image(variant, default_image_url=None):
    """Get variant image and upload to Lazada."""
    try:
        # Get variant image
        variant_image = variant.get("image")
        if not variant_image and default_image_url:
            variant_image = default_image_url

        if not variant_image:
            print("No variant image found")
            return None

        # Upload variant image to Lazada
        lazada_image_url = upload_image_lazada(variant_image, "VARIANT_IMAGE")
        if not lazada_image_url:
            print(f"Failed to upload variant image: {variant_image}")
            return None

        print(f"Successfully uploaded variant image to Lazada: {lazada_image_url}")
        return lazada_image_url

    except Exception as e:
        print(f"Error getting variant image: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def prepare_all_images(item, default_image_url=None):
    """Prepare all images for Lazada product including custom_attach_image fields."""
    try:
        all_images = []
        
        # Get main images
        main_images = prepare_main_images(item, default_image_url)
        all_images.extend(main_images)
        
        # Get additional images
        additional_images = prepare_additional_images(item, default_image_url)
        all_images.extend(additional_images)
        
        # Remove duplicates while preserving order
        seen = set()
        all_images = [x for x in all_images if not (x in seen or seen.add(x))]
        
        print(f"Total images prepared: {len(all_images)}")
        return all_images

    except Exception as e:
        print(f"Error preparing all images: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return default image if available
        if default_image_url:
            return [default_image_url]
        return []

def update_or_create_lazada(**kwargs):
    """
    Đồng bộ sản phẩm lên Lazada Shop (tạo mới hoặc cập nhật).
    Sử dụng cấu trúc giống với TikTok Shop để thống nhất.
    """
    try:
        inner_kwargs = kwargs.get("kwargs", {})
        item_doc = inner_kwargs.get("item_doc")
        shop_name = inner_kwargs.get("shop", 'Lazada')

        print(f"===== BẮT ĐẦU ĐỒNG BỘ LAZADA cho {item_doc.name} - Shop: {shop_name} =====")

        # Tải lại item_doc từ database để tránh xung đột
        item_doc = frappe.get_doc("Item", item_doc.name)

        # Tìm mapping trong child table
        lazada_mapping = next(
            (m for m in (item_doc.custom_marketplace_item_mapping or []) 
             if m.marketplace == "Lazada" and 
             m.active ),
            None
        )
        print(f"Mapping for {item_doc.name}: {lazada_mapping}")

        # Chuẩn bị dữ liệu sản phẩm
        if item_doc.has_variants:
            # Lấy tất cả các biến thể
            variants = frappe.get_all(
                "Item",
                filters={"variant_of": item_doc.name},
                fields=["name", "item_name", "item_code"]
            )
            
            print(f"Item {item_doc.name} có {len(variants)} biến thể. Chuẩn bị dữ liệu cho tất cả biến thể.")
            product_data = prepare_product_data_with_variants(
                template_item=item_doc,
                variants=variants,
                name_product=item_doc.item_name,
                shop_name=shop_name
            )
        else:
            print(f"Item {item_doc.name} không có biến thể. Chuẩn bị dữ liệu sản phẩm đơn.")
            product_data = prepare_product_data(
                item=item_doc,
                name_product=item_doc.item_name,
                shop_name=shop_name
            )
        
        if not product_data:
            error_msg = f"Failed to prepare product data for {item_doc.name}"
            print(error_msg)
            update_sync_status(item_doc.name, "Failed", "Lazada", error_msg)
            return {"success": False, "message": error_msg}

        if not lazada_mapping or not lazada_mapping.marketplace_product_id:
            print(f"Creating new Lazada Product for {item_doc.name}")
            response = create_lazada_product(product_data, shop_name)
            if response and (response.get("code") == "0" or response.get("code") == 0):
                # Xử lý phản hồi từ create API
                lazada_product_id = response.get("data", {}).get("item_id")
                if lazada_product_id:
                    # Lưu mapping vào custom_marketplace_item_mapping
                    frappe.db.append("Item", item_doc.name, "custom_marketplace_item_mapping", {
                        "marketplace": "Lazada",
                        "marketplace_product_id": lazada_product_id,
                        "marketplace_sku": item_doc.item_code,
                        "last_sync_time": frappe.utils.now(),
                        "sync_status": "Success",
                        "active": 1,
                        "shop_name": shop_name
                    })
                    frappe.db.commit()
                    success_msg = f"TẠO MỚI SẢN PHẨM LAZADA THÀNH CÔNG: {item_doc.name} - ID: {lazada_product_id}"
                    print(success_msg)
                    
                    # Lưu mapping cho các biến thể nếu có
                    if item_doc.has_variants:
                        save_variant_mappings_to_custom_marketplace(item_doc, response, "Lazada", shop_name)
                        
                    return {"success": True, "message": success_msg, "product_id": lazada_product_id}
                else:
                    error_msg = f"Không tìm thấy item_id trong phản hồi từ Lazada API"
                    print(error_msg)
                    frappe.db.append("Item", item_doc.name, "custom_marketplace_item_mapping", {
                        "marketplace": "Lazada",
                        "marketplace_sku": item_doc.item_code,
                        "last_sync_time": frappe.utils.now(),
                        "sync_status": "Failed",
                        "active": 1,
                        "shop_name": shop_name
                    })
                    frappe.db.commit()
                    return {"success": False, "message": error_msg}
            else:
                error_message = f"Failed to create Lazada Product: {response}"
                print(f"TẠO MỚI SẢN PHẨM LAZADA THẤT BẠI: {item_doc.name} - Lỗi: {error_message}")
                frappe.log_error(error_message)
                frappe.db.append("Item", item_doc.name, "custom_marketplace_item_mapping", {
                    "marketplace": "Lazada",
                    "marketplace_sku": item_doc.item_code,
                    "last_sync_time": frappe.utils.now(),
                    "sync_status": "Failed",
                    "active": 1,
                    "shop_name": shop_name
                })
                frappe.db.commit()
                return {"success": False, "message": error_message}
        else:
            print(f"Updating Lazada Product for {item_doc.name}")
            lazada_product_id = lazada_mapping.marketplace_product_id
            if not lazada_product_id:
                error_msg = f"No marketplace_product_id found for {item_doc.name}"
                print(error_msg)
                return {"success": False, "message": error_msg}

            response = update_product(lazada_product_id, product_data, shop_name)
            if response and (response.get("code") == "0" or response.get("code") == 0):
                success_msg = f"CẬP NHẬT SẢN PHẨM LAZADA THÀNH CÔNG: {item_doc.name} - ID: {lazada_product_id}"
                print(success_msg)
                frappe.db.set_value("Marketplace Item Mapping", lazada_mapping.name, {
                    "sync_status": "Success",
                    "last_sync_time": frappe.utils.now()
                })
                frappe.db.commit()
                
                # Lưu mapping cho các biến thể nếu có
                if item_doc.has_variants:
                    save_variant_mappings_to_custom_marketplace(item_doc, response, "Lazada", shop_name)
                    
                return {"success": True, "message": success_msg, "product_id": lazada_product_id}
            else:
                error_message = f"Failed to update Lazada Product {lazada_product_id}: {response}"
                print(f"CẬP NHẬT SẢN PHẨM LAZADA THẤT BẠI: {item_doc.name} - ID: {lazada_product_id} - Lỗi: {error_message}")
                frappe.log_error(error_message)
                frappe.db.set_value("Marketplace Item Mapping", lazada_mapping.name, {
                    "sync_status": "Failed",
                    "last_sync_time": frappe.utils.now()
                })
                frappe.db.commit()
                return {"success": False, "message": error_message}
    except Exception as e:
        error_msg = f"Exception in update_or_create_lazada: {str(e)}"
        print(error_msg)
        frappe.log_error(message=error_msg, title="Lazada Sync Error")
        return {"success": False, "message": error_msg}
    finally:
        print(f"===== KẾT THÚC ĐỒNG BỘ LAZADA cho {item_doc.name if 'item_doc' in locals() else 'unknown'} =====")

def delete_lazada_product(item_doc, shop_name=None):
    """
    Xử lý toàn bộ logic xóa sản phẩm Lazada Shop.
    Sử dụng cấu trúc giống với TikTok Shop để thống nhất.
    """
    print(f"Preparing to delete Lazada product for {item_doc.name}")
    
    lazada_mapping = next(
        (m for m in (item_doc.custom_marketplace_item_mapping or []) 
         if m.marketplace == "Lazada" and m.active and
         (not shop_name or not hasattr(m, 'shop_name') or not m.shop_name or m.shop_name == shop_name)),
        None
    )
    print(f"Mapping for {item_doc.name}: {lazada_mapping}")

    if not lazada_mapping or not lazada_mapping.marketplace_product_id:
        print(f"No Lazada mapping found for {item_doc.name}. No action taken.")
        return

    # Xóa bản ghi trong child table
    frappe.db.delete("Marketplace Item Mapping", {"name": lazada_mapping.name})
    frappe.db.commit()
    print(f"Deleted Lazada mapping for {item_doc.name}")

    # Gọi API xóa sản phẩm trên Lazada
    seller_sku = lazada_mapping.marketplace_sku
    if not seller_sku:
        seller_sku = item_doc.item_code
        
    # Đẩy việc xóa trên Lazada vào queue
    shop = getattr(lazada_mapping, 'shop_name', 'Lazada')
    frappe.enqueue(
        "spec.spec.lazada.lazada_product.delete_product",
        queue="short",
        timeout=20,
        seller_sku_list=seller_sku,
        shop_name=shop
    )
    print(f"Enqueued deletion of Lazada Product with seller_sku {seller_sku} for {item_doc.name}")

@frappe.whitelist()
def update_or_create(**kwargs):
    """
    Đóng vai trò là wrapper (bọc) cho hàm update_or_create_lazada.
    Giữ lại để tương thích với mã hiện có, nhưng forward đến hàm mới.
    """
    inner_kwargs = kwargs.get("kwargs", {})
    item_doc = inner_kwargs.get("item_doc")
    shop_name = inner_kwargs.get("shop", 'Lazada')
    
    print(f"Update or create called for {item_doc.name}, forwarding to update_or_create_lazada")
    
    try:
        # Đưa vào queue để xử lý bất đồng bộ
        task = frappe.enqueue(
            "spec.spec.lazada.lazada_product.update_or_create_lazada",
            queue="short",
            timeout=60,  # Tăng timeout lên 60 giây
            kwargs={"item_doc": item_doc, "shop_name": shop_name},
            now=True  # Chạy đồng bộ để dễ debug
        )
        
        # Nếu chạy đồng bộ với now=True, task chính là kết quả
        if isinstance(task, dict) and "success" in task:
            print(f"Đồng bộ hoàn thành: {task['message']}")
            return task
        
        return {"status": "success", "message": "Task enqueued successfully", "task": str(task)}
    except Exception as e:
        error_msg = f"Lỗi khi đồng bộ sản phẩm Lazada: {str(e)}"
        print(error_msg)
        frappe.log_error(message=error_msg, title="Lazada Sync Error")
        return {"status": "failed", "message": error_msg}

def prepare_product_data_with_variants(template_item, variants, name_product, shop_name):
    """Prepare data for Lazada product creation/update with all variants in a single request."""
    try:
        # Sử dụng hình ảnh mặc định nếu không có hình ảnh nào được tải lên
        default_image_url = "https://sg-test-11.slatic.net/p/e8c35b24bb34152c25c1d9abbf1a619e.jpg"

        # Nếu không có category_id được truyền vào, lấy từ item_group
        category_id = get_category_id(template_item.item_group, "Lazada")
        
        if not category_id:
            print(f"Missing category_id for product {template_item.name}")
            update_sync_status(template_item.name, "Failed", "Lazada", "Missing category_id")
            return None
        
        # Get sales attributes mapping for Lazada
        sales_attrs = get_sales_attributes_mapping("Lazada")
        if not sales_attrs:
            print(f"No sales attributes mapping found for marketplace Lazada")
            return None
            
        # Collect all product images (from template and variants)
        all_product_images = []
        
        # Add template image if available
        if template_item.image:
            template_image = upload_image_lazada(template_item.image, "MAIN_IMAGE")
            if template_image:
                all_product_images.append(template_image)
                print(f"Added template image to product images: {template_image}")
        
        # Nếu không có hình ảnh nào được tải lên, sử dụng hình ảnh mặc định
        if not all_product_images:
            print(f"No images found, using default image: {default_image_url}")
            all_product_images.append(default_image_url)
        
        # Prepare SKUs for all variants
        skus = []
        for variant in variants:
            variant_doc = frappe.get_doc("Item", variant.name)
            
            # Lấy giá từ variant_doc
            variant_price = variant_doc.standard_rate or template_item.standard_rate or 300000
                
            # Get variant image
            variant_image = None
            if variant_doc.image:
                variant_image = upload_image_lazada(variant_doc.image, "ATTRIBUTE_IMAGE")
                if variant_image:
                    # Add variant image to product images if not already there
                    if variant_image not in all_product_images:
                        all_product_images.append(variant_image)
                        print(f"Added variant image to product images: {variant_image}")
            elif variant_doc.custom_attach_image:
                variant_image = upload_image_lazada(variant_doc.custom_attach_image, "ATTRIBUTE_IMAGE")
                if variant_image:
                    # Add variant image to product images if not already there
                    if variant_image not in all_product_images:
                        all_product_images.append(variant_image)
                        print(f"Added variant image to product images: {variant_image}")
                
            # Get variant attributes
            variant_attrs = frappe.get_all(
                "Item Variant Attribute",
                filters={"parent": variant.name},
                fields=["attribute", "attribute_value"]
            )
            
            # Prepare saleProp for this variant
            sale_prop = {}
            for attr in variant_attrs:
                if attr["attribute"] in sales_attrs:
                    # Use the attribute name from Lazada mapping
                    lazada_attr_name = sales_attrs[attr["attribute"]]["name"].lower()
                    # Replace spaces with underscores for consistency
                    lazada_attr_name = lazada_attr_name.replace(" ", "_")
                    sale_prop[lazada_attr_name] = attr["attribute_value"]
            
            # Get quantity from bin or use default value
            quantity = 10  # Default quantity
            try:
                bin_data = frappe.get_all(
                    "Bin",
                    filters={"item_code": variant_doc.item_code, "warehouse": variant_doc.default_warehouse},
                    fields=["actual_qty"],
                    limit=1
                )
                if bin_data and bin_data[0].actual_qty:
                    quantity = int(bin_data[0].actual_qty)
            except Exception as e:
                print(f"Error getting quantity for variant {variant_doc.item_code}: {str(e)}")
            
            # Create SKU data
            sku_data = {
                "SellerSku": variant_doc.item_code,
                "package_height": variant_doc.custom_package_height or 10,
                "package_length": variant_doc.custom_package_length or 10,
                "package_width": variant_doc.custom_package_width or 10,
                "package_weight": variant_doc.custom_package_weight or 10,
                "price": variant_price,
                "quantity": quantity,
                "Images": {"Image": [variant_image] if variant_image else []},
            }
            
            # Add sale properties if available
            if sale_prop:
                sku_data["saleProp"] = sale_prop
                
            skus.append(sku_data)
            
        # Prepare product data
        product_data = {
            "Request": {
                "Product": {
                    "PrimaryCategory": category_id,
                    "Images": {"Image": all_product_images},
                    "Attributes": {
                        "name": name_product,
                        "brand": template_item.brand or "No Brand",
                        "description": prepare_description(template_item)
                    },
                    "Skus": {
                        "Sku": skus
                    }
                }
            }
        }
        
        # Thêm các thuộc tính tùy chỉnh từ cross_channel_selling nếu có
        if hasattr(template_item, "custom_attributes") and template_item.custom_attributes:
            if "Attributes" not in product_data["Request"]["Product"]:
                product_data["Request"]["Product"]["Attributes"] = {}
                
            # Thêm các thuộc tính tùy chỉnh vào Attributes
            for attr_id, attr_value in template_item.custom_attributes.items():
                product_data["Request"]["Product"]["Attributes"][attr_id] = attr_value
                
        return product_data
    except Exception as e:
        print(f"Error preparing data for product {template_item.name} with variants: {str(e)}")
        frappe.log_error(
            message=f"Error preparing data for product {template_item.name} with variants: {str(e)}", 
            title="Lazada Product Sync Error"
        )
        update_sync_status(template_item.name, "Failed", "Lazada", str(e))
        return None

def prepare_product_data(item, name_product, shop_name):
    """Prepare data for Lazada product creation/update."""
    try:
        default_image_url = "https://sg-test-11.slatic.net/p/e8c35b24bb34152c25c1d9abbf1a619e.jpg"

        # Nếu không có category_id được truyền vào, lấy từ item_group
        category_id = get_category_id(item.item_group, "Lazada")
        
        if not category_id:
            print(f"Missing category_id for product {item.name}")
            update_sync_status(item.name, "Failed", "Lazada", "Missing category_id")
            return None
        
        # Lấy tất cả hình ảnh
        all_images = prepare_all_images(item, default_image_url)
        
        # Prepare product data
        product_data = {
            "Request": {
                "Product": {
                    "PrimaryCategory": category_id,
                    "Images": {"Image": all_images},
                    "Attributes": {
                        "name": name_product,
                        "brand": item.brand or "No Brand",
                        "description": prepare_description(item)
                    },
                    "Skus": {
                        "Sku": prepare_skus(
                            item=item, 
                            marketplace="Lazada",
                            default_image_url=default_image_url
                        )}
                }
            }
        }
        
        # Thêm các thuộc tính tùy chỉnh từ cross_channel_selling nếu có
        if hasattr(item, "custom_attributes") and item.custom_attributes:
            if "Attributes" not in product_data["Request"]["Product"]:
                product_data["Request"]["Product"]["Attributes"] = {}
                
            # Thêm các thuộc tính tùy chỉnh vào Attributes
            for attr_id, attr_value in item.custom_attributes.items():
                product_data["Request"]["Product"]["Attributes"][attr_id] = attr_value
        
        return product_data
    except Exception as e:
        print(f"Error preparing data for product {item.name}: {str(e)}")
        frappe.log_error(
            message=f"Error preparing data for product {item.name}: {str(e)}", 
            title="Lazada Product Sync Error"
        )
        update_sync_status(item.name, "Failed", "Lazada", str(e))
        return None
    

def update_sync_status(item_code, status, marketplace, message=None):
    """Update synchronization status for a product."""
    try:
        # Thử sử dụng custom_marketplace_item_mapping trực tiếp
        try:
            item_doc = frappe.get_doc("Item", item_code)
            found_mapping = False
            
            # Tìm mapping trong child table
            for mapping in (item_doc.custom_marketplace_item_mapping or []):
                if mapping.marketplace == marketplace:
                    mapping.sync_status = status
                    mapping.last_sync_time = frappe.utils.now()
                    found_mapping = True
            
            if found_mapping:
                item_doc.save(ignore_permissions=True)
                frappe.db.commit()
                print(f"Updated sync status for {item_code} to {status} in custom_marketplace_item_mapping")
                return
        except Exception as e:
            print(f"Không thể cập nhật custom_marketplace_item_mapping: {str(e)}")
            # Tiếp tục với phương pháp khác
        
        # Nếu không thể cập nhật trực tiếp, tạo hoặc cập nhật bản ghi Marketplace Item Mapping riêng
        try:
            # Check if mapping already exists
            mapping = frappe.get_all(
                "Marketplace Item Mapping",
                filters={"item_code": item_code, "marketplace": marketplace},
                fields=["name"]
            )
            
            if mapping:
                doc = frappe.get_doc("Marketplace Item Mapping", mapping[0]["name"])
                doc.sync_status = status
                doc.last_sync_time = frappe.utils.now()
                doc.save(ignore_permissions=True)
                print(f"Updated existing Marketplace Item Mapping for {item_code}: {status}")
            else:
                doc = frappe.new_doc("Marketplace Item Mapping")
                doc.item_code = item_code
                doc.marketplace = marketplace
                doc.sync_status = status
                doc.last_sync_time = frappe.utils.now()
                doc.insert(ignore_permissions=True)
                print(f"Created new Marketplace Item Mapping for {item_code}: {status}")
            
            frappe.db.commit()
        except Exception as e:
            print(f"Không thể tạo/cập nhật Marketplace Item Mapping: {str(e)}")
            # Xử lý fallback - chỉ ghi log
            
        if message:
            frappe.log_error(
                message=f"Sync {item_code} ({marketplace}): {message}",
                title=f"Sync Status: {status}"
            )
    except Exception as e:
        print(f"Lỗi khi cập nhật trạng thái cho {item_code}: {str(e)}")
        frappe.log_error(message=f"Lỗi cập nhật trạng thái đồng bộ: {str(e)}", title=f"Sync Error: {item_code}")

def save_variant_mappings_to_custom_marketplace(item_doc, response_data, marketplace="Lazada", shop_name="Lazada"):
    """Save mappings for all variants from Lazada API response to custom_marketplace_item_mapping."""
    try:
        if not response_data or "data" not in response_data:
            print("Invalid response data")
            return
            
        data = response_data["data"]
        item_id = data.get("item_id")
        sku_list = data.get("sku_list", [])
        
        if not item_id:
            print("Missing item_id in response")
            return
            
        # Check if the item has variants
        if item_doc.has_variants:
            # For items with variants, save mappings for each variant
            for sku_data in sku_list:
                seller_sku = sku_data.get("seller_sku")
                sku_id = sku_data.get("sku_id")
                
                if not seller_sku:
                    print(f"Missing seller_sku in sku_data: {sku_data}")
                    continue
                    
                # Find variant item
                try:
                    variant_doc = frappe.get_doc("Item", seller_sku)
                    
                    # Save mapping for variant
                    frappe.db.append("Item", variant_doc.name, "custom_marketplace_item_mapping", {
                        "marketplace": marketplace,
                        "marketplace_product_id": item_id,
                        "marketplace_sku": seller_sku,
                        "sync_status": "Success",
                        "active": 1,
                        "shop_name": shop_name
                    })
                    print(f"Saved mapping for variant {seller_sku}")
                except Exception as e:
                    print(f"Error saving mapping for variant {seller_sku}: {str(e)}")
        else:
            # For items without variants, save the template mapping
            try:
                # Save mapping for the template item
                frappe.db.append("Item", item_doc.name, "custom_marketplace_item_mapping", {
                    "marketplace": marketplace,
                    "marketplace_product_id": item_id,
                    "marketplace_sku": item_doc.item_code,
                    "sync_status": "Success",
                    "active": 1,
                    "shop_name": shop_name
                })
                print(f"Saved mapping for template item {item_doc.name}")
            except Exception as e:
                print(f"Error saving mapping for template item {item_doc.name}: {str(e)}")
                
        frappe.db.commit()
        print(f"Successfully saved mappings for item {item_doc.name}")
    except Exception as e:
        print(f"Error saving variant mappings: {str(e)}")
        frappe.log_error(f"Error saving variant mappings: {str(e)}")
        raise

def prepare_skus(item, marketplace, default_image_url):
    """Prepare SKU data for product."""
    skus = []
    
    if item.has_variants:
        variants = frappe.get_all(
            "Item",
            filters={"variant_of": item.item_code},
            fields=["item_code", "item_name", "opening_stock", "standard_rate", "image", "custom_attach_image"]
        )
        if not variants:
            print(f"No variants found for product {item.name}")
            return None

        # Get sales attributes mapping
        sales_attrs = get_sales_attributes_mapping(marketplace)
        if not sales_attrs:
            print(f"No sales attributes mapping found for marketplace {marketplace}")
            # Tiếp tục với giá trị mặc định
            sales_attrs = {
                "Color": {"id": "1001", "name": "Color"},
                "Size": {"id": "1002", "name": "Size"},
                "Material": {"id": "1003", "name": "Material"}
            }

        # Limit to 3 sales attributes as per Lazada requirements
        sales_attrs = dict(list(sales_attrs.items())[:3])

        seen_combinations = set()
        for variant in variants:
            variant_attrs = frappe.get_all(
                "Item Variant Attribute",
                filters={"parent": variant["item_code"]},
                fields=["attribute", "attribute_value"]
            )
            
            sales_attributes = []
            for attr in variant_attrs:
                if attr["attribute"] in sales_attrs:
                    sales_attributes.append({
                        "id": sales_attrs[attr["attribute"]]["id"],
                        "name": sales_attrs[attr["attribute"]]["name"],
                        "value_name": attr["attribute_value"]
                    })

            if not sales_attributes:
                print(f"No valid sales attributes for variant {variant['item_code']}")
                # Thêm một thuộc tính mặc định nếu không có
                sales_attributes.append({
                    "id": "1001",
                    "name": "Color",
                    "value_name": "Default"
                })

            # Check for duplicate attribute combinations
            attr_key = tuple(sorted((attr["name"], attr["value_name"]) for attr in sales_attributes))
            if attr_key in seen_combinations:
                print(f"Duplicate attribute combination {attr_key} for variant {variant['item_code']}")
                continue
            seen_combinations.add(attr_key)

            # Get variant image
            sku_img_uri = get_variant_image(variant, default_image_url)

            # Lấy giá từ variant
            price = variant.get("standard_rate") or 300000
            
            # Đảm bảo price là string
            price_str = str(price)
            print(f"Using price for variant {variant['item_code']}: {price_str}")

            # Create SKU data
            skus.append({
                "sales_attributes": sales_attributes,
                "seller_sku": variant.get("custom_barcode_data") or variant["item_code"],
                "price": price_str,
                "sku_img": {"uri": sku_img_uri} if sku_img_uri != default_image_url else None,
                "package_weight" : variant.custom_package_weight or 10,
                "package_width": variant.custom_package_width or 10,
                "package_length": variant.custom_package_length or 10,
                "package_height": variant.custom_package_height or 10
            })
    else:
        # Lấy giá từ item
        price = item.standard_rate or 300000
        
        # Đảm bảo price là string
        price_str = str(price)
        print(f"Using price for item {item.item_code}: {price_str}")

        # Create SKU data for main product
        skus.append({
            "seller_sku": item.get("custom_barcode_data") or item.item_code,
            "price": price_str, 
            "package_weight" : item.custom_package_weight or 10,
            "package_width": item.custom_package_width or 10,
            "package_length": item.custom_package_length or 10,
            "package_height": item.custom_package_height or 10
        })

    if not skus:
        print(f"No valid SKUs for product {item.name}")
        return None
    return skus

def get_sales_attributes_mapping(marketplace):
    """Get sales attributes mapping for a marketplace."""
    try:
        sales_attrs = {}
        
        # Kiểm tra xem có mapping nào không
        mappings = frappe.get_all(
            "Item Attribute Marketplace Mapping",
            filters={"marketplace": marketplace},
            fields=["item_attribute", "marketplace_attribute"]
        )
        
        if not mappings:
            print(f"Không tìm thấy mapping cho marketplace {marketplace}")
            # Trả về một số mapping mặc định cho Lazada nếu không tìm thấy
            if marketplace == "Lazada":
                return {
                    "Color": {"id": "1001", "name": "Color"},
                    "Size": {"id": "1002", "name": "Size"},
                    "Material": {"id": "1003", "name": "Material"}
                }
            return {}
            
        for mapping in mappings:
            item_attr = mapping.get("item_attribute")
            marketplace_attr = mapping.get("marketplace_attribute")
            
            if not item_attr or not marketplace_attr:
                continue
                
            # Lấy thông tin marketplace attribute
            marketplace_attr_doc = frappe.get_doc("Marketplace Attribute", marketplace_attr)
            if marketplace_attr_doc and marketplace_attr_doc.type == "Sales_Property":
                sales_attrs[item_attr] = {
                    "id": marketplace_attr_doc.attribute_id,
                    "name": marketplace_attr_doc.attribute_name
                }
                
        # Nếu không tìm thấy mapping nào, trả về một số mapping mặc định cho Lazada
        if not sales_attrs and marketplace == "Lazada":
            return {
                "Color": {"id": "1001", "name": "Color"},
                "Size": {"id": "1002", "name": "Size"},
                "Material": {"id": "1003", "name": "Material"}
            }
            
        return sales_attrs
    except Exception as e:
        print(f"Error getting sales attributes mapping: {str(e)}")
        # Trả về một số mapping mặc định cho Lazada nếu có lỗi
        if marketplace == "Lazada":
            return {
                "Color": {"id": "1001", "name": "Color"},
                "Size": {"id": "1002", "name": "Size"},
                "Material": {"id": "1003", "name": "Material"}
            }
        return {}

def prepare_description(item):
    """Prepare product description."""
    description = item.description or "<p>Vui lòng kiểm tra kích thước trước khi mua hàng.</p>"
    
    # Add specifications if available
    if hasattr(item, "custom_item_specification") and item.custom_item_specification:
        spec_html = "<ul>"
        for spec in item.custom_item_specification:
            spec_html += f"<li>{spec.specification}: {spec.value}</li>"
        spec_html += "</ul>"
        description += spec_html
    
    # Add video if available
    if hasattr(item, "custom_video") and item.custom_video:
        description += f"<p>Video sản phẩm: <a href='{item.custom_video}'>Xem video</a></p>"
    
    return description

@frappe.whitelist()
def bulk_publish_items(items, marketplace, action="create"):
    """Bulk publish or update items to marketplace."""
    try:
        if not items:
            return {"status": "failed", "message": "Không có sản phẩm nào được chọn."}
        
        if not isinstance(items, list):
            items = [items]
        
        success_count = 0
        failed_count = 0
        failed_items = []
        
        for item_name in items:
            try:
                item_doc = frappe.get_doc("Item", item_name)
                
                # Kiểm tra xem sản phẩm đã được đăng bán chưa
                if action == "update":
                    # Kiểm tra xem sản phẩm đã được đăng bán chưa
                    mapping = next(
                        (m for m in (item_doc.custom_marketplace_item_mapping or []) 
                         if m.marketplace == marketplace and m.active),
                        None
                    )
                    
                    if not mapping or not mapping.marketplace_product_id:
                        failed_items.append({
                            "item": item_name,
                            "reason": "Sản phẩm chưa được đăng bán trên marketplace này."
                        })
                        failed_count += 1
                        continue
                
                # Gọi hàm update_or_create để đăng bán hoặc cập nhật sản phẩm
                result = update_or_create(kwargs={"item_doc": item_doc})
                
                if result and result.get("status") == "success":
                    success_count += 1
                else:
                    failed_items.append({
                        "item": item_name,
                        "reason": result.get("message", "Không xác định")
                    })
                    failed_count += 1
            except Exception as e:
                failed_items.append({
                    "item": item_name,
                    "reason": str(e)
                })
                failed_count += 1
        
        # Tạo thông báo kết quả
        message = f"Đã xử lý {len(items)} sản phẩm. "
        message += f"Thành công: {success_count}, Thất bại: {failed_count}. "
        
        if failed_items:
            message += "Chi tiết lỗi: "
            for item in failed_items:
                message += f"\n- {item['item']}: {item['reason']}"
        
        return {
            "status": "success" if success_count > 0 else "failed",
            "message": message
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Lỗi khi xử lý sản phẩm: {str(e)}"
        }
    
def get_category_id(item_group, marketplace):
    """Get category ID from item group for a specific marketplace."""
    try:
        # Tìm category mapping từ item group
        try:
            # Kiểm tra xem DocType 'Item Group Category Mapping' có tồn tại không
            if frappe.db.exists("DocType", "Item Group Category Mapping"):
                category_mapping = frappe.get_all(
                    "Item Group Category Mapping",
                    filters={"parent": item_group, "marketplace": marketplace},
                    fields=["category_id"]
                )
                
                if category_mapping:
                    # Trả về category_id từ mapping
                    return category_mapping[0].category_id
        except Exception as e:
            print(f"Lỗi khi kiểm tra Item Group Category Mapping: {str(e)}")
            # Tiếp tục với các phương pháp khác
            
        # Nếu không tìm thấy mapping, tìm trong custom_ecommerce_platform của Item Group
        try:
            item_group_doc = frappe.get_doc("Item Group", item_group)
            if hasattr(item_group_doc, "custom_ecommerce_platform") and item_group_doc.custom_ecommerce_platform:
                for platform_entry in item_group_doc.custom_ecommerce_platform:
                    if platform_entry.ecommerce_platform == marketplace and platform_entry.marketplace_category:
                        marketplace_category = frappe.get_doc("Marketplace Category", platform_entry.marketplace_category)
                        if marketplace_category and marketplace_category.category_id:
                            print(f"Found category_id {marketplace_category.category_id} from custom_ecommerce_platform for {item_group}")
                            return marketplace_category.category_id
        except Exception as e:
            print(f"Lỗi khi kiểm tra custom_ecommerce_platform: {str(e)}")
            
        # Nếu không tìm thấy mapping, tìm category từ danh mục marketplace
        category = frappe.get_all(
            "Marketplace Category",
            filters={"marketplace": marketplace, "category_name": ["like", f"%{item_group}%"]},
            fields=["category_id"]
        )
        
        if category:
            # Trả về category_id từ danh mục marketplace
            print(f"Found category_id {category[0].category_id} by name match for {item_group}")
            return category[0].category_id
            
        # Nếu không tìm thấy, trả về category mặc định
        default_category = frappe.get_value(
            "Marketplace Category",
            {"marketplace": marketplace, "is_default": 1},
            "category_id"
        )
        
        if default_category:
            print(f"Using default category_id {default_category} for {item_group}")
            return default_category
            
        # Fallback - Trả về category mặc định cho Lazada
        if marketplace == "Lazada":
            print(f"Using hardcoded default Lazada category_id for {item_group}")
            return "11481"  # Category mặc định cho Lazada (Ví dụ: Fashion)
            
        # Nếu không có category mặc định, trả về None
        print(f"No category_id found for {item_group} on {marketplace}")
        return None
    except Exception as e:
        print(f"Error getting category ID for {item_group} on {marketplace}: {str(e)}")
        return None


