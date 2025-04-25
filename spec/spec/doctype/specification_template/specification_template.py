# Copyright (c) 2025, spec and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SpecificationTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from spec.spec.doctype.specification_template_line.specification_template_line import SpecificationTemplateLine

		category_id: DF.Data | None
		item_group: DF.Link
		lazada_setting: DF.Link | None
		template_line: DF.Table[SpecificationTemplateLine]
		template_name: DF.Data
	# end: auto-generated types
	pass
