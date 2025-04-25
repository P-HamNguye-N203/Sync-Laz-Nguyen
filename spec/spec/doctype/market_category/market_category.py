# Copyright (c) 2025, spec and contributors
# For license information, please see license.txt

# import frappe
from frappe.utils.nestedset import NestedSet


class MarketCategory(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		category_id: DF.Data | None
		category_name: DF.Data | None
		is_group: DF.Check
		is_leaf_category: DF.Check
		lft: DF.Int
		market_platform: DF.Literal["lazada", "tiktok shop"]
		name_view: DF.Data | None
		old_parent: DF.Link | None
		parent_market_category: DF.Link | None
		premission_status: DF.Data | None
		rgt: DF.Int
	# end: auto-generated types
	pass
