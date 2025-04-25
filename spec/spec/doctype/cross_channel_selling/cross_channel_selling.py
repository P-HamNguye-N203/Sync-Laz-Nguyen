# Copyright (c) 2025, spec and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CrossChannelSelling(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from spec.spec.doctype.platform_attributes_value.platform_attributes_value import PLatformAttributesValue

		item_code: DF.Link
		lazada: DF.Check
		lazada_attributes: DF.Table[PLatformAttributesValue]
		lazada_category: DF.Link | None
		package_height: DF.Data
		package_length: DF.Data
		package_weight: DF.Data
		package_width: DF.Data
		shopee: DF.Check
		shopee_attributes: DF.Data | None
		tiki: DF.Check
		tiki_attributes: DF.Data | None
		tiktok_attribute: DF.Table[PLatformAttributesValue]
		tiktok_shop: DF.Check
		tiktok_shop_category: DF.Link | None
	# end: auto-generated types
	pass

