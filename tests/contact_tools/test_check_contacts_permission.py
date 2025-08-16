#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import examples.imessage as im

func = im.check_contacts_permission.fn if hasattr(im.check_contacts_permission, 'fn') else im.check_contacts_permission
result = func()
print("Result:", result)