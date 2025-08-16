#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import examples.imessage as im

func = im.find_contact_by_phone.fn if hasattr(im.find_contact_by_phone, 'fn') else im.find_contact_by_phone
print("Testing simplified find_contact_by_phone (searches up to 1000 contacts)...")
result = func("14698264814")
print("Result:", result)