import frappe
from frappe.model.document import Document

class CrossChannelSelling(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from spec.spec.doctype.item_info.item_info import ItemInfo
        from spec.spec.doctype.platform_attributes_value.platform_attributes_value import PLatformAttributesValue

        brand: DF.Data
        description: DF.Text | None
        item_code: DF.Link
        item_info: DF.Table[ItemInfo]
        item_name: DF.Data
        lazada: DF.Check
        lazada_attributes: DF.Table[PLatformAttributesValue]
        lazada_category: DF.Link | None
        package_height: DF.Data
        package_length: DF.Data
        package_weight: DF.Data
        package_width: DF.Data
        quantity: DF.Data | None
        shopee: DF.Check
        shopee_attributes: DF.Data | None
        tiki: DF.Check
        tiki_attributes: DF.Data | None
        tiktok_attribute: DF.Table[PLatformAttributesValue]
        tiktok_shop: DF.Check
        tiktok_shop_category: DF.Link | None
    # end: auto-generated types
    
    def after_save(self):
        """Sau khi lưu document, tự động đăng sản phẩm lên các sàn thương mại điện tử đã được chọn"""
        super().after_save()  # Gọi hàm after_save của class cha (Document)
        
        if not self.item_code:
            return
            
        # Lấy thông tin sản phẩm
        item_doc = frappe.get_doc("Item", self.item_code)
        print("đang đăng ")
        # Kiểm tra và đăng lên Lazada nếu được chọn
        if self.lazada:
            self._publish_to_lazada(item_doc)
            
        # Thêm các sàn khác ở đây nếu cần
        # if self.shopee:
        #     self._publish_to_shopee(item_doc)
        # if self.tiki:
        #     self._publish_to_tiki(item_doc)
        # if self.tiktok_shop:
        #     self._publish_to_tiktok(item_doc)
            
    def on_submit(self):
        """Khi document được submit, tự động đăng sản phẩm lên các sàn thương mại điện tử đã được chọn"""
        if not self.item_code:
            frappe.throw("Vui lòng chọn sản phẩm cần đăng lên sàn")
            
        # Lấy thông tin sản phẩm
        item_doc = frappe.get_doc("Item", self.item_code)
        
        # Kiểm tra và đăng lên Lazada nếu được chọn
        if self.lazada:
            self._publish_to_lazada(item_doc)
            
        # Thêm các sàn khác ở đây nếu cần
        # if self.shopee:
        #     self._publish_to_shopee(item_doc)
        # if self.tiki:
        #     self._publish_to_tiki(item_doc)
            
    def _publish_to_lazada(self, item_doc):
        """Đăng sản phẩm lên Lazada"""
        try:
            # Chuẩn bị dữ liệu cho API
            kwargs = {
                "item_doc": item_doc,
                "marketplace": "Lazada",
                "item_name": self.item_name  # Sử dụng item_name thay vì document_name
            }
            
            # Nếu có category được chọn, thêm vào kwargs
            if self.lazada_category:
                kwargs["category_id"] = frappe.db.get_value("Market Category", self.lazada_category, "category_id")
                
            # Nếu có các thuộc tính Lazada được chọn, thêm vào kwargs
            if self.lazada_attributes:
                kwargs["attributes"] = {}
                for attr in self.lazada_attributes:
                    if attr.attribute_id and attr.attribute_value:
                        kwargs["attributes"][attr.attribute_id] = attr.attribute_value
            
            # Thêm thông tin kích thước và trọng lượng nếu có
            if self.package_length:
                kwargs["package_length"] = self.package_length
            if self.package_width:
                kwargs["package_width"] = self.package_width
            if self.package_height:
                kwargs["package_height"] = self.package_height
            if self.package_weight:
                kwargs["package_weight"] = self.package_weight
                
            # Thêm thông tin item_info nếu có
            if self.item_info:
                kwargs["item_info"] = []
                for info in self.item_info:
                    if info.name1 and info.price:
                        kwargs["item_info"].append({
                            "name": info.name1,
                            "price": info.price,
                            "currency": info.currency if hasattr(info, "currency") else "VND"
                        })
            
            # Gọi API để đăng sản phẩm
            from spec.spec.lazada.lazada_product import update_or_create
            
            # Gọi hàm update_or_create với kwargs
            result = update_or_create(kwargs=kwargs)
            
            if result and result.get("status") == "success":
                frappe.msgprint(f"Đã đăng sản phẩm lên Lazada thành công: {result.get('message')}")
            else:
                error_message = result.get("message") if result else "Không xác định"
                frappe.msgprint(f"Lỗi khi đăng sản phẩm lên Lazada: {error_message}", alert=True)
                
        except Exception as e:
            frappe.log_error(f"Lỗi khi đăng sản phẩm lên Lazada: {str(e)}", "Cross Channel Selling")
            frappe.msgprint(f"Lỗi khi đăng sản phẩm lên Lazada: {str(e)}", alert=True)

    def on_update(self):
        """Override on_update to add custom logic."""
        print("on_update called for CrossChannelSelling")
        # Không gọi super().on_update() vì Document không có phương thức này
        # Thay vào đó, chúng ta sẽ xử lý logic trong after_save
        
        # Thêm log để kiểm tra
        print(f"Document name: {self.item_name}")
        print(f"Document status: {self.docstatus}")
        print(f"Item code: {self.item_code}")
        print(f"Lazada: {self.lazada}")
        print(f"Shopee: {self.shopee}")
        print(f"Tiki: {self.tiki}")
        print(f"Tiktok Shop: {self.tiktok_shop}")
        
        # Kiểm tra các điều kiện cần thiết
        if not self.item_code:
            print("No item_code found, skipping...")
            return
            
        # Kiểm tra xem có ít nhất một marketplace được chọn không
        if not (self.lazada or self.shopee or self.tiki or self.tiktok_shop):
            print("No marketplace selected, skipping...")
            return
            
        # Kiểm tra category cho từng marketplace được chọn
        if self.lazada and not self.lazada_category:
            print("Lazada selected but no category found, skipping...")
            return
            
        if self.shopee and not self.shopee_category:
            print("Shopee selected but no category found, skipping...")
            return
            
        if self.tiki and not self.tiki_category:
            print("Tiki selected but no category found, skipping...")
            return
            
        if self.tiktok_shop and not self.tiktok_shop_category:
            print("Tiktok Shop selected but no category found, skipping...")
            return
            
        # Nếu tất cả điều kiện đều thỏa mãn, tiếp tục xử lý
        print("All conditions met, proceeding with processing...")
        
        # Lấy thông tin kích thước gói hàng
        package_length = self.package_length
        package_width = self.package_width
        package_height = self.package_height
        package_weight = self.package_weight
        
        print(f"Package dimensions: {package_length}x{package_width}x{package_height}, weight: {package_weight}")
        
        # Lấy thông tin item_info
        item_info = []
        if hasattr(self, "item_info") and self.item_info:
            print(f"Found item_info with {len(self.item_info)} entries")
            for info in self.item_info:
                print(f"Item info entry: {info}")
                item_info.append({
                    "name": info.name1,
                    "price": info.price,
                    "currency": info.currency if hasattr(info, "currency") else "VND"
                })
        else:
            print(f"No item_info found in document {self.name}")
                
        print(f"Item info: {item_info}")
        
        # Lấy thông tin custom attributes
        custom_attributes = {}
        if hasattr(self, "custom_attributes") and self.custom_attributes:
            for attr in self.custom_attributes:
                custom_attributes[attr.attribute_id] = attr.attribute_value
                
        print(f"Custom attributes: {custom_attributes}")
        
        # Lấy thông tin item
        try:
            item_doc = frappe.get_doc("Item", self.item_code)
            print(f"Successfully retrieved item document: {item_doc.name}")
        except Exception as e:
            print(f"Error retrieving item document: {str(e)}")
            return
            
        # Xử lý theo marketplace
        if self.lazada:
            print(f"Processing for Lazada marketplace")
            try:
                from spec.spec.lazada.lazada_product import update_or_create
                
                # Lấy category_id từ Market Category
                category_id = None
                if self.lazada_category:
                    category_id = frappe.db.get_value("Market Category", self.lazada_category, "category_id")
                    print(f"Retrieved category_id from Market Category: {category_id}")
                
                # Chuẩn bị dữ liệu cho hàm update_or_create
                kwargs = {
                    "item_doc": item_doc,
                    "item_name": self.item_name,
                    "category_id": category_id,
                    "attributes": custom_attributes,
                    "package_length": package_length,
                    "package_width": package_width,
                    "package_height": package_height,
                    "package_weight": package_weight,
                    "item_info": item_info
                }
                
                print(f"Calling update_or_create with kwargs: {kwargs}")
                
                # Gọi hàm update_or_create
                result = update_or_create(kwargs=kwargs)
                
                print(f"Result from update_or_create: {result}")
                
                if result and result.get("status") == "success":
                    print(f"Successfully updated/created product on Lazada")
                    frappe.msgprint(f"Successfully updated/created product on Lazada")
                else:
                    error_message = result.get("message", "Unknown error") if result else "No response from update_or_create"
                    print(f"Error updating/creating product on Lazada: {error_message}")
                    frappe.msgprint(f"Error updating/creating product on Lazada: {error_message}")
            except Exception as e:
                print(f"Error processing for Lazada: {str(e)}")
                frappe.log_error(f"Error processing Cross Channel Selling for Lazada: {str(e)}", "Cross Channel Selling Error")
                frappe.msgprint(f"Error processing for Lazada: {str(e)}")
        else:
            print(f"Lazada not selected, skipping...")
            
        print(f"=== Completed on_update for Cross Channel Selling ===\n")

@frappe.whitelist()
def get_lazada_category_from_item_group(item_group):
	"""Get Lazada market category from Item Group's custom_ecommerce_platform child table."""
	try:
		# Get the Item Group document
		item_group_doc = frappe.get_doc("Item Group", item_group)
		print(item_group_doc)
		# Check if custom_ecommerce_platform exists
		if hasattr(item_group_doc, "custom_ecommerce_platform") and item_group_doc.custom_ecommerce_platform:
			# Find the entry for Lazada
			for entry in item_group_doc.custom_ecommerce_platform:
				if entry.ecommerce_platform == "Lazada" and entry.marketplace_category:
					return {"marketplace_category": entry.marketplace_category}
		
		# If not found, try to find the correct child table name
		for field in frappe.get_meta("Item Group").get_table_fields():
			child_table = frappe.get_all(field.options, 
										filters={"parent": item_group, "ecommerce_platform": "Lazada"},
										fields=["marketplace_category"])
			if child_table:
				
				return {"marketplace_category": child_table[0].marketplace_category}
		
		return {"marketplace_category": None}
	except Exception as e:
		frappe.log_error(f"Error getting Lazada category from Item Group: {str(e)}", "Cross Channel Selling")
		return {"marketplace_category": None, "error": str(e)}

@frappe.whitelist()
def get_template_items(doctype, txt, searchfield, start, page_len, filters):
	"""
	Lấy danh sách các item là Template (has_variants = 1) hoặc không phải là variant của item khác
	"""
	try:
		# Tạo query để lấy các item là Template hoặc không phải là variant
		query = """
			SELECT name, item_name, item_group
			FROM tabItem
			WHERE (has_variants = 1 OR variant_of IS NULL OR variant_of = '')
			AND is_sales_item = 1
			AND disabled = 0
		"""
		
		# Thêm điều kiện tìm kiếm nếu có
		if txt:
			query += f" AND (name LIKE '%{txt}%' OR item_name LIKE '%{txt}%')"
		
		# Thêm điều kiện phân trang
		query += f" LIMIT {start}, {page_len}"
		
		# Thực hiện query
		items = frappe.db.sql(query, as_dict=1)
		
		# Trả về kết quả
		return [(item.name, f"{item.item_name} ({item.item_group})") for item in items]
	except Exception as e:
		frappe.log_error(f"Error in get_template_items: {str(e)}", "Cross Channel Selling")
		return []

@frappe.whitelist()
def get_item_details(item_code):
	"""Get item details including variants and their prices"""
	try:
		# Import hàm get_item_price từ lazada_product
		from spec.spec.lazada.lazada_product import get_item_price
		
		# Get the main item
		item = frappe.get_doc("Item", item_code)
		
		# Prepare response
		response = {
			"item_name": item.item_name,
			"brand": 'No Brand',
			"quantity": 10,
			"item_info": []
		}
		
		# Check if item has variants
		if item.has_variants:
			# Get all variants
			variants = frappe.get_all("Item", 
				filters={"variant_of": item_code},
				fields=["name", "item_name"]
			)
			
			# Add variant info
			for variant in variants:
				# Lấy giá từ Item Price
				price, currency = get_item_price(variant.name)
				
				response["item_info"].append({
					"name": variant.name,
					"price": price if price else 0,
					"currency": currency if currency else "VND"
				})
		else:
			# Lấy giá từ Item Price cho item chính
			price, currency = get_item_price(item_code)
			
			# Add main item info
			response["item_info"].append({
				"name": item.name,
				"price": price if price else 0,
				"currency": currency if currency else "VND"
			})
			
		return response
		
	except Exception as e:
		frappe.log_error(f"Error getting item details: {str(e)}")
		return None