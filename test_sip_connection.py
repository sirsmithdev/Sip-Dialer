#!/usr/bin/env python3
"""
Test script for SIP connection to Grandstream UCM
"""
import requests
import json
from getpass import getpass

# API Configuration
API_BASE = "http://localhost:8000/api/v1"

def login(email, password):
    """Login and get access token"""
    response = requests.post(
        f"{API_BASE}/auth/login",
        data={"username": email, "password": password}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.text}")
        return None

def get_sip_settings(token):
    """Get current SIP settings"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE}/settings/sip", headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        print("No SIP settings found - will create new")
        return None
    else:
        print(f"Error getting SIP settings: {response.text}")
        return None

def create_sip_settings(token, settings):
    """Create or update SIP settings"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Try to create
    response = requests.post(
        f"{API_BASE}/settings/sip",
        headers=headers,
        json=settings
    )

    if response.status_code in [200, 201]:
        print("✅ SIP settings saved successfully")
        return response.json()
    else:
        print(f"❌ Error saving SIP settings: {response.text}")
        return None

def test_sip_connection(token):
    """Test SIP connection"""
    headers = {"Authorization": f"Bearer {token}"}
    print("\n🔄 Testing SIP connection...")
    response = requests.post(f"{API_BASE}/settings/sip/test", headers=headers)

    if response.status_code == 200:
        result = response.json()
        if result["success"]:
            print(f"✅ Connection successful!")
            print(f"   Message: {result['message']}")
            if result.get("timing_ms"):
                print(f"   Response time: {result['timing_ms']}ms")
            if result.get("resolved_ip"):
                print(f"   Resolved IP: {result['resolved_ip']}")
            return True
        else:
            print(f"❌ Connection failed: {result['message']}")
            if result.get("diagnostic_hint"):
                print(f"   Hint: {result['diagnostic_hint']}")
            return False
    else:
        print(f"❌ Test request failed: {response.text}")
        return False

def main():
    print("=" * 60)
    print("SIP Connection Test for Grandstream UCM")
    print("=" * 60)

    # Login
    print("\n📝 Login to auto-dialer API")
    email = input("Email: ")
    password = getpass("Password: ")

    token = login(email, password)
    if not token:
        print("❌ Login failed. Exiting.")
        return

    print("✅ Logged in successfully\n")

    # Get current settings
    current = get_sip_settings(token)
    if current:
        print("📋 Current SIP Settings:")
        print(f"   Server: {current.get('sip_server')}")
        print(f"   Port: {current.get('sip_port')}")
        print(f"   Username: {current.get('sip_username')}")
        print(f"   Transport: {current.get('sip_transport')}")
        print(f"   Status: {current.get('connection_status')}")
        print()

        update = input("Update settings? (y/N): ").lower()
        if update != 'y':
            # Just test current settings
            test_sip_connection(token)
            return

    # Configure new settings
    print("\n⚙️  Configure SIP Extension for Grandstream UCM")
    print("   (Press Enter to use default values)")
    print()

    sip_server = input("SIP Server [192.168.150.10]: ") or "192.168.150.10"
    sip_port = input("SIP Port [5060]: ") or "5060"
    sip_username = input("Extension [1005]: ") or "1005"
    sip_password = getpass("SIP Password: ")

    if not sip_password:
        print("❌ Password is required")
        return

    sip_transport = input("Transport [UDP]: ").upper() or "UDP"

    # AMI Settings
    print("\n⚙️  Configure AMI (Asterisk Manager Interface)")
    ami_host = input("AMI Host [192.168.150.10]: ") or "192.168.150.10"
    ami_port = input("AMI Port [7777]: ") or "7777"
    ami_username = input("AMI Username [autodialerami]: ") or "autodialerami"
    ami_password = getpass("AMI Password: ")

    if not ami_password:
        print("❌ AMI Password is required")
        return

    # Build settings object
    settings = {
        "sip_server": sip_server,
        "sip_port": int(sip_port),
        "sip_username": sip_username,
        "sip_password": sip_password,
        "sip_transport": sip_transport,
        "registration_required": True,
        "register_expires": 300,
        "keepalive_enabled": True,
        "keepalive_interval": 30,
        "rtp_port_start": 10000,
        "rtp_port_end": 20000,
        "codecs": ["PCMU", "PCMA", "G722"],
        "ami_host": ami_host,
        "ami_port": int(ami_port),
        "ami_username": ami_username,
        "ami_password": ami_password,
        "default_caller_id": sip_username,
        "caller_id_name": "Auto Dialer"
    }

    print("\n📤 Saving SIP settings...")
    result = create_sip_settings(token, settings)

    if result:
        print("\n🧪 Testing connection...")
        test_sip_connection(token)

        print("\n" + "=" * 60)
        print("✅ Configuration Complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Check UCM web GUI for extension registration")
        print("   URL: http://192.168.150.10")
        print("   Path: Extension/Trunk → Extensions")
        print("   Extension: 1005 should show green circle")
        print()
        print("2. Verify extension privilege is set to 'International'")
        print()
        print("3. Test making a call from the auto-dialer")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
