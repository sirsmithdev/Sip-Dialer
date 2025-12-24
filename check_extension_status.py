#!/usr/bin/env python3
"""
Quick script to check extension registration status via AMI
"""
import socket
import sys

def check_ami_connection(host, port, username, password):
    """Check AMI connection and get PJSIP endpoint status"""
    print(f"🔌 Connecting to {host}:{port}...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)

    try:
        sock.connect((host, port))

        # Read welcome
        welcome = sock.recv(1024).decode('utf-8', errors='ignore')
        print(f"✅ Connected: {welcome.strip()}\n")

        # Login
        login_cmd = f"""Action: Login\r
Username: {username}\r
Secret: {password}\r
\r
"""
        sock.sendall(login_cmd.encode('utf-8'))

        response = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if b'\r\n\r\n' in response:
                break

        login_response = response.decode('utf-8', errors='ignore')

        if "Success" not in login_response:
            print(f"❌ Login failed:\n{login_response}")
            sock.close()
            return False

        print(f"✅ AMI Login successful\n")

        # Check PJSIP endpoints
        print("📊 Checking PJSIP endpoints...")

        pjsip_cmd = """Action: PJSIPShowEndpoints\r
\r
"""
        sock.sendall(pjsip_cmd.encode('utf-8'))

        response = b''
        sock.settimeout(5.0)
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b'--END COMMAND--' in response or len(response) > 50000:
                    break
        except socket.timeout:
            pass

        pjsip_response = response.decode('utf-8', errors='ignore')

        # Parse endpoint info
        if "ObjectName" in pjsip_response:
            print("\n📋 PJSIP Endpoints found:")
            lines = pjsip_response.split('\n')
            for i, line in enumerate(lines):
                if 'ObjectName:' in line and '1005' in line:
                    # Print this endpoint and next few lines
                    print(f"\n{'='*60}")
                    for j in range(i, min(i+15, len(lines))):
                        if lines[j].strip():
                            print(f"  {lines[j]}")
                    print(f"{'='*60}\n")
                    break
        else:
            print(f"📥 Response:\n{pjsip_response[:1000]}\n")

        # Logout
        logout_cmd = """Action: Logoff\r
\r
"""
        sock.sendall(logout_cmd.encode('utf-8'))
        sock.close()

        print("✅ Check complete!\n")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 70)
    print("Extension Status Checker")
    print("=" * 70)
    print()

    host = "192.168.150.10"
    port = 7777

    username = input("AMI Username [autodialerami]: ").strip() or "autodialerami"
    password = input("AMI Password: ").strip()

    if not password:
        print("❌ Password required")
        return

    print()
    success = check_ami_connection(host, port, username, password)

    if success:
        print("💡 Tip: To see real-time status, SSH to UCM:")
        print("   ssh root@192.168.150.10")
        print("   asterisk -rvvv")
        print("   pjsip show endpoints")
        print("   pjsip show endpoint 1005")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled")

