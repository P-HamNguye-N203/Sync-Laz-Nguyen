# Copyright (c) 2025, spec and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ECommerceVariant(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		image: DF.AttachImage | None
		item: DF.Link | None
		item_id: DF.Data | None
		item_name: DF.Data | None
		marketplatform: DF.Literal["Lazada", "Tiktok Shop", "Shopee", "Tiki"]
		seller_sku: DF.Data | None
		shop_sku: DF.Data | None
		sku_id: DF.Data | None
	# end: auto-generated types
	pass
