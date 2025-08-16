#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import examples.imessage as imessage
import json

# Helper to get underlying function from mcp.tool decorator
def get_func(tool):
    return tool.fn if hasattr(tool, 'fn') else tool

print("=" * 60)
print("Testing All Contact Tools")
print("=" * 60)

# 1. Check permissions
print("\n1. Checking Contacts permission...")
try:
    result = get_func(imessage.check_contacts_permission)()
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Error: {e}")

# 2. Get contacts count
print("\n2. Getting total contacts count...")
try:
    result = get_func(imessage.get_contacts_count)()
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Error: {e}")

# 3. Get first 5 contacts with pagination
print("\n3. Getting first 5 contacts (pagination test)...")
try:
    result = get_func(imessage.get_all_contacts)(limit=5, offset=0)
    if "contacts" in result:
        print(f"Pagination: {result.get('pagination', {})}")
        print(f"Contacts returned: {len(result['contacts'])}")
        for name in list(result["contacts"].keys())[:3]:
            contact = result["contacts"][name]
            print(f"  - {name}: {len(contact.get('phones', []))} phones, {len(contact.get('emails', []))} emails")
    else:
        print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Error: {e}")

# 4. Test finding contact by phone
print("\n4. Testing reverse phone lookup (using Damelo's number)...")
try:
    # Using the phone number we found for Damelo
    result = get_func(imessage.find_contact_by_phone)("14698264814")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Error: {e}")

# 5. Test match_phone_to_contact
print("\n5. Testing match_phone_to_contact...")
try:
    # match_phone_to_contact calls find_contact_by_phone internally
    result = get_func(imessage.match_phone_to_contact)("14698264814")
    print(f"Phone matched to: {result}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)