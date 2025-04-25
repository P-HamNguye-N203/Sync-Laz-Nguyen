# Copyright (c) 2025, spec and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SKUMapping(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		marketplatform: DF.Literal["Lazada", "Tiktok Shop"]
		seller_sku: DF.Link
		shop_sku: DF.Data
		sku_id: DF.Data
	# end: auto-generated types
	pass
