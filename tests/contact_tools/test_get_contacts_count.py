#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import examples.imessage as im

func = im.get_contacts_count.fn if hasattr(im.get_contacts_count, 'fn') else im.get_contacts_count
result = func()
print("Result:", result)