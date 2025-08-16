#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import examples.imessage as im

func = im.get_all_contacts.fn if hasattr(im.get_all_contacts, 'fn') else im.get_all_contacts
# Test with just 2 contacts
result = func(limit=2, offset=0)
print("Pagination:", result.get('pagination'))
print("Contacts:", list(result.get('contacts', {}).keys()))