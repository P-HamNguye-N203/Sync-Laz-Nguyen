// Copyright (c) 2025, spec and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Cross Channel Selling", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Cross Channel Selling", {
	refresh(frm) {
		// Add any refresh functionality here
		
		// Lọc và hiển thị các thuộc tính Lazada
		if (frm.fields_dict["lazada_attributes"]) {
			// Lọc attribute_id trong bảng lazada_attributes
			frm.fields_dict["lazada_attributes"].grid.get_field("attribute_id").get_query = function(doc, cdt, cdn) {
				// Lấy category hiện tại
				let category = frm.doc.lazada_category;
				
				// Nếu không có category, trả về tất cả các thuộc tính Lazada
				if (!category) {
					return {
						query: "spec.spec.doctype.marketplace_attribute.marketplace_attribute.get_marketplace_attributes",
						filters: {
							"marketplace": "Lazada"
						}
					};
				}
				
				// Lấy category_id từ Market Category
				return {
					query: "spec.spec.doctype.marketplace_attribute.marketplace_attribute.get_marketplace_attributes",
					filters: {
						"marketplace": "Lazada",
						"category": category
					}
				};
			};
			
			// Tùy chỉnh hiển thị của trường attribute_id để hiển thị tên thay vì ID
			frm.fields_dict["lazada_attributes"].grid.get_field("attribute_id").formatter = function(value, row, column, data, default_formatter) {
				if (value && data && data.label) {
					return data.label;
				}
				return default_formatter(value, row, column, data);
			};
		}
		frm.set_query('item_code', function() {
			return {
				query: "spec.spec.overrides.cross_channel_selling.get_template_items",
				filters: {}
			};
		});
	},
	
	item_code: function(frm) {
		if (frm.doc.item_code) {
			console.log("Item selected:", frm.doc.item_code);
			
			// Fetch item details to get the item group
			frappe.db.get_value('Item', frm.doc.item_code, 'item_group')
				.then(r => {
					if (r.message && r.message.item_group) {
						// Store the item group for later use
						frm.doc._item_group = r.message.item_group;
						console.log("Item group found:", frm.doc._item_group);
						
						// If Lazada is already checked, fetch the category
						if (frm.doc.lazada) {
							console.log("Lazada already checked, fetching category");
							fetch_lazada_category(frm);
						}
					} else {
						console.log("No item group found for item:", frm.doc.item_code);
					}
				})
				.catch(err => {
					console.error("Error fetching item group:", err);
				});
				
			// Fetch item details to auto-fill item information
			frappe.call({
				method: "spec.spec.overrides.cross_channel_selling.get_item_details",
				args: {
					item_code: frm.doc.item_code
				},
				callback: function(r) {
					if (r.message) {
						console.log("Item details fetched:", r.message);
						
						// Set item_name and brand
						frm.set_value("item_name", r.message.item_name);
						frm.set_value("brand", r.message.brand);
						
						// Set quantity if available
						if (r.message.quantity) {
							frm.set_value("quantity", r.message.quantity);
						}
						
						// Clear existing item_info entries
						frm.clear_table("item_info");
						
						// Add item_info entries for variants or the item itself
						if (r.message.item_info && r.message.item_info.length > 0) {
							r.message.item_info.forEach(function(info) {
								let row = frm.add_child("item_info");
								row.name1 = info.name;
								row.price = info.price;
							});
							frm.refresh_field("item_info");
						}
					}
				}
			});
		}
	},
	
	lazada: function(frm) {
		if (frm.doc.lazada && frm.doc.item_code) {
			console.log("Lazada checkbox checked, fetching category");
			fetch_lazada_category(frm);
		}
	},
	
	lazada_category: function(frm) {
		// Khi category thay đổi, làm mới lưới lazada_attributes
		if (frm.doc.lazada_category && frm.fields_dict["lazada_attributes"]) {
			console.log("Lazada category changed, refreshing attributes grid");
			
			// Lấy category_id từ Market Category
			frappe.db.get_value('Market Category', frm.doc.lazada_category, 'category_id')
				.then(r => {
					if (r.message && r.message.category_id) {
						console.log("Category ID:", r.message.category_id);
						
						// Lấy các thuộc tính của category hiện tại
						frappe.call({
							method: 'spec.spec.lazada.lazada_attributes.get_category_attributes',
							args: {
								category_id: r.message.category_id
							},
							callback: function(response) {
								if (response.message) {
									console.log("Category attributes:", response.message);
									
									// Lưu danh sách attribute_id của category hiện tại
									frm.doc._category_attribute_ids = [];
									if (Array.isArray(response.message)) {
										response.message.forEach(attr => {
											if (attr.id) {
												// Chuyển đổi id thành chuỗi để đảm bảo so sánh đúng
												frm.doc._category_attribute_ids.push(String(attr.id));
											}
										});
									} else if (typeof response.message === 'object') {
										Object.values(response.message).forEach(attr => {
											if (attr.id) {
												// Chuyển đổi id thành chuỗi để đảm bảo so sánh đúng
												frm.doc._category_attribute_ids.push(String(attr.id));
											}
										});
									}
									
									console.log("Category attribute IDs:", frm.doc._category_attribute_ids);
									
									// Làm mới lưới lazada_attributes
									frm.fields_dict["lazada_attributes"].grid.refresh();
									
									// Kiểm tra và xóa các attribute không thuộc category hiện tại
									if (frm.doc.lazada_attributes && frm.doc.lazada_attributes.length > 0) {
										let validAttributes = [];
										frm.doc.lazada_attributes.forEach(attr => {
											// Chuyển đổi attribute_id thành chuỗi để so sánh
											if (frm.doc._category_attribute_ids.includes(String(attr.attribute_id))) {
												validAttributes.push(attr);
											}
										});
										
										if (validAttributes.length !== frm.doc.lazada_attributes.length) {
											frm.set_value('lazada_attributes', validAttributes);
										}
									}
								}
							}
						});
					} else {
						console.log("No category_id found for category:", frm.doc.lazada_category);
					}
				})
				.catch(err => {
					console.error("Error fetching category_id:", err);
				});
		}
	}
});

function fetch_lazada_category(frm) {
	if (!frm.doc._item_group) {
		console.log("Item group not found, fetching it first");
		// If item group is not yet fetched, get it
		frappe.db.get_value('Item', frm.doc.item_code, 'item_group')
			.then(r => {
				if (r.message && r.message.item_group) {
					frm.doc._item_group = r.message.item_group;
					console.log("Item group fetched:", frm.doc._item_group);
					get_lazada_category(frm);
				} else {
					console.log("No item group found for item:", frm.doc.item_code);
				}
			})
			.catch(err => {
				console.error("Error fetching item group:", err);
			});
	} else {
		console.log("Using existing item group:", frm.doc._item_group);
		get_lazada_category(frm);
	}
}

function get_lazada_category(frm) {
	console.log("Fetching Item Group document:", frm.doc._item_group);
	
	// Try using server-side method to get the market category
	frappe.call({
		method: 'spec.spec.overrides.cross_channel_selling.get_lazada_category_from_item_group',
		args: {
			item_group: frm.doc._item_group
		},
		callback: function(r) {
			console.log("Server response:", r);
			if (r.message && r.message.marketplace_category) {
				console.log("Setting lazada_category to:", r.message.marketplace_category);
				frm.set_value('lazada_category', r.message.marketplace_category);
			} else {
				console.log("No market category found from server method");
				
				// Fallback to client-side method
				get_lazada_category_client_side(frm);
			}
		},
		error: function(err) {
			console.error("Error calling server method:", err);
			// Fallback to client-side method
			get_lazada_category_client_side(frm);
		}
	});
}

function get_lazada_category_client_side(frm) {
	// Try using get_value instead of get_doc
	frappe.db.get_value('Item Group', frm.doc._item_group, 'name')
		.then(r => {
			console.log("Item Group name check:", r);
			if (r.message && r.message.name) {
				console.log("Item Group exists, trying to get custom_ecommerce_platform");
				
				// Try to get the custom_ecommerce_platform directly
				frappe.db.get_list('custom_ecommerce_platform', {
					filters: [
						['parent', '=', frm.doc._item_group],
						['marketplace', '=', 'Lazada']
					],
					fields: ['marketplace_category']
				})
				.then(r => {
					console.log("custom_ecommerce_platform list:", r);
					if (r.message && r.message.length > 0 && r.message[0].marketplace_category) {
						console.log("Setting lazada_category to:", r.message[0].marketplace_category);
						frm.set_value('lazada_category', r.message[0].marketplace_category);
					} else {
						console.log("No market category found in custom_ecommerce_platform");
					}
				})
				.catch(err => {
					console.error("Error fetching custom_ecommerce_platform:", err);
				});
			} else {
				console.log("Item Group does not exist:", frm.doc._item_group);
			}
		})
		.catch(err => {
			console.error("Error checking Item Group:", err);
		});
}

// Thêm sự kiện cho lazada_attributes
frappe.ui.form.on('PLatform Attributes Value', {
	form_render: function(frm, cdt, cdn) {
		// Hiển thị label thay vì ID trong lazada_attributes
		let row = frappe.get_doc(cdt, cdn);
		if (row.attribute_id) {
			frappe.db.get_value('Marketplace Attribute', row.attribute_id, 'attribute_name')
				.then(r => {
					if (r.message && r.message.attribute_name) {
						row.label = r.message.attribute_name;
						frm.refresh_field('lazada_attributes');
					}
				});
		}
	},
	
	attribute_id: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (row.attribute_id) {
			// Kiểm tra xem attribute_id có thuộc category hiện tại không
			if (frm.doc._category_attribute_ids && frm.doc._category_attribute_ids.length > 0) {
				console.log("Category attribute IDs:", frm.doc._category_attribute_ids);
				console.log("Selected attribute ID:", row.attribute_id, "Type:", typeof row.attribute_id);
				
				// Chuyển đổi attribute_id thành chuỗi để so sánh
				const attributeIdStr = String(row.attribute_id);
				if (!frm.doc._category_attribute_ids.includes(attributeIdStr)) {
					console.log("Attribute ID not in category:", attributeIdStr);
					// Nếu không thuộc category hiện tại, xóa attribute_id
					frappe.model.set_value(cdt, cdn, 'attribute_id', '');
					frappe.msgprint('Thuộc tính này không thuộc danh mục hiện tại. Vui lòng chọn thuộc tính khác.');
					return;
				}
			}
			
			// Lấy attribute_name từ Marketplace Attribute
			frappe.db.get_value('Marketplace Attribute', row.attribute_id, 'attribute_name')
				.then(r => {
					if (r.message && r.message.attribute_name) {
						// Tự động điền attribute_name
						frappe.model.set_value(cdt, cdn, 'attribute_name', r.message.attribute_name);
						row.attribute_name = r.message.attribute_name;
						frm.refresh_field('lazada_attributes');
					}
				});
		}
	}
});

// Đảm bảo lưới làm mới khi thêm dòng mới
frappe.ui.form.on('Cross Channel Selling', 'lazada_attributes_add', function(frm) {
	if (frm.fields_dict["lazada_attributes"]) {
		frm.fields_dict["lazada_attributes"].grid.refresh();
	}
});
