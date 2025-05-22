#!/usr/bin/env python3
"""
Setup script for Firebase token automation

This script helps you set up automated token refresh by:
1. Guiding you through Firebase service account setup
2. Helping you find your test user UIDs
3. Creating a cron job for automatic token refresh

Usage:
    python scripts/setup_token_automation.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_step(step_num, title):
    """Print a formatted step"""
    print(f"\n🔧 Step {step_num}: {title}")
    print("-" * 40)

def check_dependencies():
    """Check if required dependencies are installed"""
    print_step(1, "Checking Dependencies")
    
    missing = []
    try:
        import firebase_admin
        print("✅ firebase-admin is installed")
    except ImportError:
        missing.append("firebase-admin")
    
    try:
        import requests
        print("✅ requests is installed")
    except ImportError:
        missing.append("requests")
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    return True

def setup_service_account():
    """Guide user through service account setup"""
    print_step(2, "Firebase Service Account Setup")
    
    service_account_path = Path("firebase-service-account-key.json")
    
    if service_account_path.exists():
        print("✅ Service account key already exists")
        return True
    
    print("📋 To set up the service account key:")
    print("1. Go to Firebase Console: https://console.firebase.google.com/")
    print("2. Select your project (relexro)")
    print("3. Go to Project Settings (gear icon)")
    print("4. Click on 'Service accounts' tab")
    print("5. Click 'Generate new private key'")
    print("6. Save the downloaded JSON file as 'firebase-service-account-key.json' in the project root")
    
    input("\nPress Enter when you've downloaded and saved the service account key...")
    
    if service_account_path.exists():
        print("✅ Service account key found!")
        return True
    else:
        print("❌ Service account key not found. Please try again.")
        return False

def find_user_uids():
    """Help user find their test user UIDs"""
    print_step(3, "Finding Test User UIDs")
    
    print("📋 To find your test user UIDs:")
    print("1. Go to Firebase Console: https://console.firebase.google.com/")
    print("2. Select your project (relexro)")
    print("3. Go to Authentication > Users")
    print("4. Find your 3 test users and copy their UIDs")
    print()
    print("You need UIDs for:")
    print("- Regular test user (for RELEX_TEST_JWT)")
    print("- Organization admin user (for RELEX_ORG_ADMIN_TEST_JWT)")
    print("- Organization staff user (for RELEX_ORG_USER_TEST_JWT)")
    
    uids = {}
    
    print("\nEnter the UIDs for each user:")
    uids["RELEX_TEST_JWT"] = input("Regular test user UID: ").strip()
    uids["RELEX_ORG_ADMIN_TEST_JWT"] = input("Organization admin UID: ").strip()
    uids["RELEX_ORG_USER_TEST_JWT"] = input("Organization staff UID: ").strip()
    
    return uids

def update_refresh_script(uids):
    """Update the refresh script with actual UIDs"""
    print_step(4, "Updating Refresh Script")
    
    script_path = Path("scripts/refresh_tokens.py")
    
    if not script_path.exists():
        print("❌ refresh_tokens.py not found")
        return False
    
    # Read the script
    content = script_path.read_text()
    
    # Update UIDs
    for token_name, uid in uids.items():
        if token_name == "RELEX_TEST_JWT":
            content = content.replace('"test-user-uid"', f'"{uid}"')
        elif token_name == "RELEX_ORG_ADMIN_TEST_JWT":
            content = content.replace('"org-admin-uid"', f'"{uid}"')
        elif token_name == "RELEX_ORG_USER_TEST_JWT":
            content = content.replace('"org-user-uid"', f'"{uid}"')
    
    # Write back
    script_path.write_text(content)
    print("✅ Updated refresh_tokens.py with your UIDs")
    return True

def test_token_generation():
    """Test the token generation"""
    print_step(5, "Testing Token Generation")
    
    try:
        result = subprocess.run([sys.executable, "scripts/refresh_tokens.py"], 
                              capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("✅ Token generation test successful!")
            print("Output:", result.stdout)
            return True
        else:
            print("❌ Token generation test failed!")
            print("Error:", result.stderr)
            return False
    except Exception as e:
        print(f"❌ Failed to run test: {e}")
        return False

def setup_cron_job():
    """Set up a cron job for automatic token refresh"""
    print_step(6, "Setting Up Automatic Refresh (Optional)")
    
    setup_cron = input("Do you want to set up automatic token refresh every 45 minutes? (y/n): ").lower()
    
    if setup_cron != 'y':
        print("⏭️  Skipping cron setup")
        return True
    
    # Get current directory
    current_dir = Path.cwd().absolute()
    script_path = current_dir / "scripts" / "refresh_tokens.py"
    
    # Create cron command
    cron_command = f"*/45 * * * * cd {current_dir} && {sys.executable} {script_path} >> /tmp/token_refresh.log 2>&1"
    
    print(f"📋 Add this line to your crontab (run 'crontab -e'):")
    print(f"   {cron_command}")
    print()
    print("This will refresh tokens every 45 minutes and log to /tmp/token_refresh.log")
    
    auto_add = input("Do you want me to add this to your crontab automatically? (y/n): ").lower()
    
    if auto_add == 'y':
        try:
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_crontab = result.stdout if result.returncode == 0 else ""
            
            # Add new job if not already present
            if cron_command not in current_crontab:
                new_crontab = current_crontab + f"\n{cron_command}\n"
                
                # Write new crontab
                process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
                process.communicate(input=new_crontab)
                
                if process.returncode == 0:
                    print("✅ Cron job added successfully!")
                else:
                    print("❌ Failed to add cron job")
            else:
                print("✅ Cron job already exists")
                
        except Exception as e:
            print(f"❌ Failed to set up cron job: {e}")
            print("Please add it manually using 'crontab -e'")
    
    return True

def create_manual_refresh_script():
    """Create a simple manual refresh script"""
    print_step(7, "Creating Manual Refresh Script")
    
    script_content = """#!/bin/bash
# Manual token refresh script
# Usage: ./refresh_tokens.sh

echo "🔄 Refreshing Firebase tokens..."
cd "$(dirname "$0")/.."
python scripts/refresh_tokens.py

if [ $? -eq 0 ]; then
    echo "✅ Tokens refreshed successfully!"
    echo "💡 Loading new tokens..."
    source ~/.zshenv
    echo "✅ Environment updated!"
else
    echo "❌ Token refresh failed!"
    exit 1
fi
"""
    
    script_path = Path("refresh_tokens.sh")
    script_path.write_text(script_content)
    script_path.chmod(0o755)  # Make executable
    
    print(f"✅ Created manual refresh script: {script_path}")
    print("Usage: ./refresh_tokens.sh")
    
    return True

def main():
    """Main setup function"""
    print_header("Firebase Token Automation Setup")
    
    print("This script will help you set up automated token refresh for all 3 JWT tokens:")
    print("- RELEX_TEST_JWT (regular user)")
    print("- RELEX_ORG_ADMIN_TEST_JWT (organization admin)")
    print("- RELEX_ORG_USER_TEST_JWT (organization staff)")
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Setup service account
    if not setup_service_account():
        return False
    
    # Find user UIDs
    uids = find_user_uids()
    if not all(uids.values()):
        print("❌ All UIDs are required")
        return False
    
    # Update script
    if not update_refresh_script(uids):
        return False
    
    # Test token generation
    if not test_token_generation():
        print("⚠️  Token generation test failed, but continuing...")
    
    # Setup cron job
    setup_cron_job()
    
    # Create manual script
    create_manual_refresh_script()
    
    print_header("Setup Complete!")
    print("✅ Token automation is now set up!")
    print()
    print("📋 Next steps:")
    print("1. Run './refresh_tokens.sh' to manually refresh tokens")
    print("2. Run 'source ~/.zshenv' to load new tokens")
    print("3. Your tokens will auto-refresh if you set up the cron job")
    print()
    print("💡 Tips:")
    print("- Tokens are valid for 1 hour")
    print("- Check /tmp/token_refresh.log for automatic refresh logs")
    print("- Run 'python scripts/refresh_tokens.py' anytime to refresh manually")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
