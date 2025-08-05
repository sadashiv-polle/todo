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
import re
from frappe.utils.password import update_password

@frappe.whitelist()
def get_users_with_roles(filters=None, order_by="creation desc", limit_page_length=20, page=1):
    import json
    filters = json.loads(filters) if filters else []
    start = (int(page) - 1) * int(limit_page_length)
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


@frappe.whitelist()
def get_user_details(name):
    if not name:
        frappe.throw("User name is required")

    user = frappe.get_doc("User", name)

    roles = [r.role for r in frappe.get_all("Has Role", filters={"parent": user.name}, fields=["role"])]

    data = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": getattr(user, "phone", ""),
        "company": getattr(user, "company", ""),
        "supplier_code": getattr(user, "supplier_code", ""),
        "role": roles[0] if roles else "",
        "roles": roles,
        "updated_by": getattr(user, "modified_by", ""),
        "updated_at": str(user.modified),
        "enabled": user.enabled,
        "notify": getattr(user, "send_welcome_email", 0) or 0,
        "status": "ACTIVE" if user.enabled else "INACTIVE",
        "password": "**********"
    }

    return data


@frappe.whitelist()
def update_user_details(name, username=None, email=None, password=None, phone=None, role=None):
    if not name:
        frappe.throw("User name (email) is required")

    # Check if the current user has the required role
    allowed_roles = ["System Manager", "HR Manager", "Admin"]
    current_user = frappe.session.user
    user_roles = frappe.get_roles(current_user)

    if not any(role in allowed_roles for role in user_roles):
        frappe.throw("You do not have permission to update user details.")

    # Restrict role updates
    if role in ["Admin", "Guest"] and role not in user_roles:
        frappe.throw(f"You cannot assign the role '{role}'.")

    try:
        user = frappe.get_doc("User", name)
        changes_made = False

        # Update username if it has changed
        if username and username != user.username:
            user.username = username
            changes_made = True

        # Update email if it has changed
        if email and email != user.email:
            user.email = email
            changes_made = True

        # Update phone if it has changed
        if phone and phone != user.phone:
            user.phone = phone
            changes_made = True

        # Update roles if the role has changed
        if role:
            existing_roles = [r.role for r in user.get("roles", [])]
            if role not in existing_roles:
                # Clear existing roles and add the new role
                user.set("roles", [])
                user.append("roles", {"role": role})
                changes_made = True

        # Update password if provided
        if password:
            update_password(user.name, password)
            changes_made = True

        # Save changes if any were made
        if changes_made:
            user.save()
            frappe.db.commit()

        return {
            "message": "User details updated successfully" if changes_made else "No changes were made",
            "username": user.username,
            "email": user.email,
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_user_details")
        frappe.throw(f"Failed to update user details: {str(e)}")


@frappe.whitelist()
def rename_user(old_user_name, new_user_name):
    """
    Rename the user document.
    NOTE: new_user_name must be a valid email address, as enforced by Frappe.
    """
    if not old_user_name or not new_user_name:
        frappe.throw("Both old and new user names are required")

    # Validate new name as email
    if not re.match(r"[^@]+@[^@]+\.[^@]+", new_user_name):
        frappe.throw("New user name must be a valid email address")

    try:
        frappe.rename_doc("User", old_user_name, new_user_name, force=True)
        frappe.db.commit()
        return {"message": f"User renamed from {old_user_name} to {new_user_name} successfully"}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "rename_user")
        frappe.throw(f"Failed to rename user: {str(e)}")

