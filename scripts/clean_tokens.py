#!/usr/bin/env python3
"""
Clean JWT tokens by removing newlines and updating ~/.zshenv

This script fixes the common issue where JWT tokens have trailing newlines
that cause "Invalid header value" errors in HTTP requests.
"""

import os
import re
from pathlib import Path

def clean_tokens():
    """Clean JWT tokens in ~/.zshenv by removing newlines"""
    zshenv_path = Path.home() / ".zshenv"
    
    if not zshenv_path.exists():
        print("❌ ~/.zshenv not found")
        return False
    
    # Read the file
    content = zshenv_path.read_text()
    
    # Clean each token by removing newlines within the quotes
    token_names = ["RELEX_TEST_JWT", "RELEX_ORG_ADMIN_TEST_JWT", "RELEX_ORG_USER_TEST_JWT"]
    
    for token_name in token_names:
        # Pattern to match: export TOKEN_NAME="...token with possible newlines..."
        pattern = rf'(export {re.escape(token_name)}=")([^"]*?)(")'
        
        def clean_token_value(match):
            prefix = match.group(1)
            token_value = match.group(2)
            suffix = match.group(3)
            
            # Remove all newlines and extra whitespace from token value
            cleaned_token = re.sub(r'\s+', '', token_value)
            
            return f"{prefix}{cleaned_token}{suffix}"
        
        content = re.sub(pattern, clean_token_value, content, flags=re.DOTALL)
    
    # Write back the cleaned content
    zshenv_path.write_text(content)
    print("✅ Cleaned JWT tokens in ~/.zshenv")
    
    # Verify the tokens are clean
    print("\n📋 Token status after cleaning:")
    for token_name in token_names:
        pattern = rf'export {re.escape(token_name)}="([^"]*)"'
        match = re.search(pattern, content)
        if match:
            token_value = match.group(1)
            has_newlines = '\n' in token_value or '\r' in token_value
            print(f"   {token_name}: {len(token_value)} chars, has newlines: {has_newlines}")
        else:
            print(f"   {token_name}: NOT FOUND")
    
    return True

if __name__ == "__main__":
    clean_tokens()
