#!/usr/bin/env python3
"""Test sending a message to 7608559652"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import examples.imessage as im
from datetime import datetime

def get_func(tool):
    return tool.fn if hasattr(tool, 'fn') else tool

print("=" * 60)
print("Testing send_message to 7608559652")
print("=" * 60)

phone = "7608559652"
message = f"Test message from FastMCP iMessage server - {datetime.now().strftime('%H:%M:%S')}"

print(f"\n📱 Sending to: {phone}")
print(f"💬 Message: {message}")
print()

func = get_func(im.send_message)
result = func(phone, message)

if result.get("success"):
    print("✅ SUCCESS! Message sent")
else:
    print(f"❌ FAILED: {result.get('error')}")

print("\nFull result:")
import json
print(json.dumps(result, indent=2))