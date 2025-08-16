#!/usr/bin/env python3
"""Simple test for send_message"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import examples.imessage as im

def get_func(tool):
    return tool.fn if hasattr(tool, 'fn') else tool

# Test with a simple validation (not actually sending)
print("Testing send_message function validation...")

func = get_func(im.send_message)

# Test 1: Missing phone number
result = func("", "Hello")
print(f"Empty phone test: {result}")

# Test 2: Missing message
result = func("1234567890", "")
print(f"Empty message test: {result}")

# Test 3: Valid inputs (but won't actually send to fake number)
result = func("test@example.com", "Test message")
print(f"Valid format test: {result}")

print("\nNote: The last test may fail if it tries to actually send - that's expected")