#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import examples.imessage as im

func = im.match_phone_to_contact.fn if hasattr(im.match_phone_to_contact, 'fn') else im.match_phone_to_contact
result = func("14698264814")
print("Result:", result)