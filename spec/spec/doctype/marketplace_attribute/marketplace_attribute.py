# Copyright (c) 2025, spec and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MarketplaceAttribute(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		attribute_id: DF.Data | None
		attribute_name: DF.Data | None
		is_customizable: DF.Check
		is_variants: DF.Check
		label: DF.Data | None
		marketplace: DF.Literal["TikTok Shop", "Lazada", "Shopee"]
		type: DF.Literal["Sales Property", "Product Property"]
	# end: auto-generated types
	pass


@frappe.whitelist()
def get_marketplace_attributes(doctype, txt, searchfield, start, page_len, filters):
    """
    Server-side function to fetch marketplace attributes with their names.
    This function is used by the link field to display attribute names instead of IDs.
    """
    query = """
        SELECT 
            name, 
            attribute_id, 
            label
        FROM 
            `tabMarketplace Attribute`
        WHERE 
            marketplace = %(marketplace)s
    """
    
    if txt:
        query += " AND (label LIKE %(txt)s OR attribute_id LIKE %(txt)s)"
    
    query += " ORDER BY label LIMIT %(start)s, %(page_len)s"
    
    return frappe.db.sql(query, {
        "marketplace": filters.get("marketplace"),
        "txt": f"%{txt}%",
        "start": start,
        "page_len": page_len
    })
