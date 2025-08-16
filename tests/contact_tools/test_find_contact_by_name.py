#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import examples.imessage as im

func = im.find_contact_by_name.fn if hasattr(im.find_contact_by_name, 'fn') else im.find_contact_by_name
result = func("Damelo", limit=5)
print("Result:", result)