#!/usr/bin/env python3
"""Minimal test - start with 1 contact"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import examples.imessage as imessage
import json

# Helper to get underlying function
def get_func(tool):
    return tool.fn if hasattr(tool, 'fn') else tool

print("Testing with minimal data...")

# Test 1: Get just 1 contact
print("\n1. Get just 1 contact:")
try:
    result = get_func(imessage.get_all_contacts)(limit=1, offset=0)
    if "error" in result:
        print(f"   Error: {result['error']}")
    else:
        print(f"   Success! Got {len(result.get('contacts', {}))} contact")
        for name, details in result.get('contacts', {}).items():
            print(f"   - {name}")
except Exception as e:
    print(f"   Failed: {e}")

# Test 2: Try 2 contacts
print("\n2. Get 2 contacts:")
try:
    result = get_func(imessage.get_all_contacts)(limit=2, offset=0)
    if "error" in result:
        print(f"   Error: {result['error']}")
    else:
        print(f"   Success! Got {len(result.get('contacts', {}))} contacts")
except Exception as e:
    print(f"   Failed: {e}")

# Test 3: Try 5 contacts
print("\n3. Get 5 contacts:")
try:
    result = get_func(imessage.get_all_contacts)(limit=5, offset=0)
    if "error" in result:
        print(f"   Error: {result['error']}")
    else:
        print(f"   Success! Got {len(result.get('contacts', {}))} contacts")
except Exception as e:
    print(f"   Failed: {e}")

# Test 4: Try phone lookup with limit of 1
print("\n4. Test phone lookup (limit search to first 100 contacts):")
try:
    # Let's try a simpler approach - just check if it works at all
    result = get_func(imessage.find_contact_by_phone)("14698264814")
    print(f"   Result: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"   Failed: {e}")