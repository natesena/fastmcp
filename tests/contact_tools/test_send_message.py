#!/usr/bin/env python3
"""Test sending iMessages"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import examples.imessage as im

def get_func(tool):
    return tool.fn if hasattr(tool, 'fn') else tool

print("=" * 60)
print("Testing send_message function")
print("=" * 60)

# Get user input for testing
print("\nThis test will send a real iMessage.")
print("Please enter the recipient details:\n")

phone = input("Enter phone number or email (or 'skip' to skip test): ").strip()

if phone.lower() != 'skip':
    message = input("Enter message text: ").strip()
    
    print(f"\n🔄 Attempting to send message to: {phone}")
    print(f"   Message: {message}")
    
    func = get_func(im.send_message)
    result = func(phone, message)
    
    if result.get("success"):
        print(f"\n✅ SUCCESS: {result.get('message')}")
    else:
        print(f"\n❌ FAILED: {result.get('error')}")
    
    print("\nFull result:")
    import json
    print(json.dumps(result, indent=2))
else:
    print("\n⏭️ Test skipped")

print("\n" + "=" * 60)