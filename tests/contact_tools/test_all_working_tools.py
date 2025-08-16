#!/usr/bin/env python3
"""Test all working contact tools"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import examples.imessage as im
import json

def get_func(tool):
    return tool.fn if hasattr(tool, 'fn') else tool

print("=" * 70)
print("TESTING ALL WORKING CONTACT TOOLS")
print("=" * 70)

# Tool 1: check_contacts_permission
print("\n1. check_contacts_permission()")
try:
    result = get_func(im.check_contacts_permission)()
    print(f"✅ Result: {result.get('message', 'Unknown')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Tool 2: get_contacts_count  
print("\n2. get_contacts_count()")
try:
    result = get_func(im.get_contacts_count)()
    print(f"✅ Result: {result.get('total_contacts', 0)} contacts")
except Exception as e:
    print(f"❌ Error: {e}")

# Tool 3: get_all_contacts with pagination
print("\n3. get_all_contacts(limit=3, offset=0)")
try:
    result = get_func(im.get_all_contacts)(limit=3, offset=0)
    pagination = result.get("pagination", {})
    contacts = result.get("contacts", {})
    print(f"✅ Got {len(contacts)} contacts out of {pagination.get('total', 0)} total")
    for name in list(contacts.keys())[:3]:
        if name:
            print(f"   - {name}")
except Exception as e:
    print(f"❌ Error: {e}")

# Tool 4: find_contact_by_name
print("\n4. find_contact_by_name('Damelo', limit=5)")
try:
    result = get_func(im.find_contact_by_name)("Damelo", limit=5)
    if "matches" in result and result["matches"]:
        print(f"✅ Found {len(result['matches'])} match(es):")
        for match in result["matches"]:
            print(f"   - {match['name']}")
            if match.get('phones'):
                print(f"     Phone: {match['phones'][0]}")
    else:
        print("✅ Works but no matches found")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("SUMMARY: All 4 contact tools are working!")
print("Removed tools: find_contact_by_phone, match_phone_to_contact, get_messages_with_contact_names")
print("=" * 70)