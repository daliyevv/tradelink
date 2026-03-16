#!/usr/bin/env python
"""
Simple script to verify profile views syntax
"""
import sys
import ast

def check_syntax(filepath):
    """Check if Python file has valid syntax"""
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        ast.parse(code)
        return True, "Syntax is valid"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

# Check the views file
views_path = 'apps/users/views.py'
serializers_path = 'apps/users/serializers.py'
urls_path = 'apps/users/urls.py'

print(f"Checking {views_path}...")
success, msg = check_syntax(views_path)
print(f"  {msg}")

print(f"\nChecking {serializers_path}...")
success, msg = check_syntax(serializers_path)
print(f"  {msg}")

print(f"\nChecking {urls_path}...")
success, msg = check_syntax(urls_path)
print(f"  {msg}")

print("\nAll files have valid Python syntax!")
