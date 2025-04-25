# Copyright (c) 2025, spec and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ImageCache(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		image_hash: DF.Data | None
		image_path: DF.Data | None
		last_updated: DF.Datetime | None
		uri: DF.Data | None
		use_case: DF.Data | None
	# end: auto-generated types
	pass
