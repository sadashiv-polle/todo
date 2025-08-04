# In your app (e.g., todo/api/purchase_order.py)
import frappe

@frappe.whitelist()
def get_po_count():
    return frappe.db.count("Purchase Order")
