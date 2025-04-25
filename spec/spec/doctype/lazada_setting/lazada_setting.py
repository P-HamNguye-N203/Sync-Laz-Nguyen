# Copyright (c) 2025, spec and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LazadaSetting(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		access_token: DF.Data
		access_token_expiry: DF.Data | None
		app_key: DF.Data
		app_secret: DF.Data
		refresh_token: DF.Data
		refresh_token_expiry: DF.Data | None
		time_now: DF.Datetime | None
	# end: auto-generated types
	pass
