# import frappe
# import json

# @frappe.whitelist()
# def get_data_with_linked_doc_fields(doctype, fields, linked_doctypes=None, filters=None, order_by=None, limit_page_length=20, page=1):
#     try:
#         if not doctype or not fields:
#             frappe.throw("`doctype` and `fields` must be provided")

#         fields = json.loads(fields)
#         linked_doctypes = json.loads(linked_doctypes) if linked_doctypes else None
#         filters = json.loads(filters) if filters else []

#         start = (int(page) - 1) * int(limit_page_length)

#         records = frappe.get_all(doctype,
#                                  fields=fields,
#                                  filters=filters,
#                                  order_by=order_by,
#                                  limit_start=start,
#                                  limit_page_length=int(limit_page_length))

#         if linked_doctypes:
#             for link_field, link_info in linked_doctypes.items():
#                 linked_names = list({r.get(link_field) for r in records if r.get(link_field)})
#                 linked_map = {}

#                 if linked_names:
#                     linked_docs = frappe.get_all(link_info["linked_doctype"],
#                                                 filters={"name": ["in", linked_names]},
#                                                 fields=["name"])

#                     linked_map = {doc["name"]: [] for doc in linked_docs}

#                     child_records = frappe.get_all(link_info["child_table"],
#                                                   filters={link_info["child_parent_field"]: ["in", linked_names]},
#                                                   fields=[link_info["child_parent_field"], link_info["child_role_field"]])

#                     for child in child_records:
#                         parent = child[link_info["child_parent_field"]]
#                         role_value = child[link_info["child_role_field"]]
#                         linked_map.setdefault(parent, []).append(role_value)

#                 for rec in records:
#                     lk = rec.get(link_field)
#                     rec[link_info.get("target_fieldname", f"{link_field}_linked")] = linked_map.get(lk, []) if lk else []

#         return records
#     except Exception as e:
#         frappe.log_error(message=str(e), title="get_data_with_linked_doc_fields error")
#         raise

import frappe

@frappe.whitelist()
def get_users_with_roles(filters=None, order_by="creation desc", limit_page_length=20, page=1):
    import json
    filters = json.loads(filters) if filters else []
    start = (int(page)-1) * int(limit_page_length)
    users = frappe.get_all(
        "User",
        fields=["name", "username", "email", "enabled", "first_name", "last_name"],
        filters=filters,
        order_by=order_by,
        limit_start=start,
        limit_page_length=limit_page_length
    )
    for user in users:
        user['roles'] = [
            d.role for d in frappe.get_all("Has Role", filters={"parent": user["name"]}, fields=["role"])
        ]
    return users

#User details API
@frappe.whitelist()
def get_user_details(user_name):
    if not user_name:
        frappe.throw("User name is required")

    user = frappe.get_doc("User", user_name)

    # Get roles as a list
    roles = [r.role for r in frappe.get_all("Has Role", filters={"parent": user.name}, fields=["role"])]

    # Compose the data dict
    data = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": getattr(user, "phone", ""),          # If field exists
        "company": getattr(user, "company", ""),      # If field exists
        "supplier_code": getattr(user, "supplier_code", ""),  # If field exists
        "role": roles[0] if roles else "",
        "roles": roles,
        "updated_by": getattr(user, "modified_by", ""),
        "updated_at": str(user.modified),
        "enabled": user.enabled,
        "notify": getattr(user, "send_welcome_email", 0) or 0,
        "status": "ACTIVE" if user.enabled else "INACTIVE"
    }
    # Password is never returned for security reasons. If needed, set as masked string.
    data["password"] = "**********"

    return data