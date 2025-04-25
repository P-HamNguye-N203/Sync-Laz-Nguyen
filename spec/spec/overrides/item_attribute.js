frappe.ui.form.on("Item Attribute", {
    refresh: function(frm) {
        console.log(frm)
        // Lọc "marketplace_attribute" trong bảng "marketplace_mappings" dựa trên "marketplace"
        frm.fields_dict["custom_item_attribute_marketplace_mapping"].grid.get_field("marketplace_attribute").get_query = function(doc, cdt, cdn) {
            let row = frappe.get_doc(cdt, cdn); // Lấy dòng hiện tại trong bảng con
            return {
                query: "spec.spec.doctype.marketplace_attribute.marketplace_attribute.get_marketplace_attributes",
                filters: {
                    // Lọc Marketplace Attribute dựa trên marketplace người dùng chọn
                    "marketplace": row.marketplace,
                    // Chỉ hiển thị thuộc tính SALES_PROPERTY
                    // "type": "SALES_PROPERTY",
                    // Chỉ hiển thị thuộc tính có thể tùy chỉnh
                    // "is_customizable": 1
                }
            };
        };
        
        // Tùy chỉnh hiển thị của trường marketplace_attribute để hiển thị tên thay vì ID
        frm.fields_dict["custom_item_attribute_marketplace_mapping"].grid.get_field("marketplace_attribute").formatter = function(value, row, column, data, default_formatter) {
            if (value && data && data.label) {
                return data.label;
            }
            return default_formatter(value, row, column, data);
        };
    },

    // (Tùy chọn) Đảm bảo lưới làm mới khi thêm dòng mới
    marketplace_mappings_add: function(frm, cdt, cdn) {
        frm.fields_dict["custom_item_attribute_marketplace_mapping"].grid.refresh();
    }
});