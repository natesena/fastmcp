#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the module and access the underlying function
import examples.imessage as imessage

# The @mcp.tool decorator wraps the function, so we need to access the actual function
# Try to get the underlying function
if hasattr(imessage.find_contact_by_name, 'fn'):
    find_func = imessage.find_contact_by_name.fn
else:
    # If it's not wrapped, use it directly
    find_func = imessage.find_contact_by_name

# Search for Damelo
print("Searching for 'Damelo'...")
try:
    result = find_func("Damelo")
    import json
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Error: {e}")