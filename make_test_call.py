#!/usr/bin/env python3
"""
Script to make a test call via Grandstream UCM AMI
"""
import socket
import time
import sys

def send_ami_action(sock, action_data):
    """Send AMI action and receive response"""
    # Send action
    sock.sendall(action_data.encode('utf-8'))

    # Receive response
    response = b''
    sock.settimeout(5.0)
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            # Check if we have complete response (double newline)
            if b'\r\n\r\n' in response:
                break
    except socket.timeout:
        pass

    return response.decode('utf-8', errors='ignore')

def login_ami(host, port, username, password):
    """Login to AMI"""
    print(f"🔌 Connecting to AMI at {host}:{port}...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)

    try:
        sock.connect((host, port))

        # Read welcome message
        welcome = sock.recv(1024).decode('utf-8', errors='ignore')
        print(f"📥 Server: {welcome.strip()}")

        # Login
        print(f"🔐 Logging in as '{username}'...")
        login_action = f"""Action: Login\r
Username: {username}\r
Secret: {password}\r
\r
"""

        response = send_ami_action(sock, login_action)
        print(f"📥 Login Response:\n{response}")

        if "Success" in response or "Authentication accepted" in response:
            print("✅ AMI login successful!")
            return sock
        else:
            print("❌ AMI login failed!")
            sock.close()
            return None

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sock.close()
        return None

def originate_call(sock, extension, destination, context="from-internal"):
    """Originate a call"""
    print(f"\n📞 Initiating call...")
    print(f"   From: PJSIP/{extension}")
    print(f"   To: {destination}")
    print(f"   Context: {context}")

    action_id = f"test_call_{int(time.time())}"

    originate_action = f"""Action: Originate\r
Channel: PJSIP/{extension}\r
Context: {context}\r
Exten: {destination}\r
Priority: 1\r
CallerID: Auto Dialer Test <{extension}>\r
Timeout: 30000\r
Async: true\r
ActionID: {action_id}\r
\r
"""

    response = send_ami_action(sock, originate_action)
    print(f"\n📥 Originate Response:\n{response}")

    if "Success" in response:
        print("✅ Call origination initiated!")
        return action_id
    else:
        print("❌ Call origination failed!")
        return None

def get_channel_status(sock):
    """Get current channel status"""
    print("\n📊 Checking channel status...")

    status_action = """Action: CoreShowChannels\r
\r
"""

    response = send_ami_action(sock, status_action)
    print(f"📥 Channel Status:\n{response}")

def logout_ami(sock):
    """Logout from AMI"""
    print("\n👋 Logging out...")

    logout_action = """Action: Logoff\r
\r
"""

    try:
        response = send_ami_action(sock, logout_action)
        print(f"📥 Logout Response:\n{response}")
    except:
        pass

    sock.close()
    print("✅ Disconnected from AMI")

def main():
    print("=" * 70)
    print("Grandstream UCM Test Call Script")
    print("=" * 70)

    # AMI Configuration
    AMI_HOST = "192.168.150.10"
    AMI_PORT = 7777

    print("\n⚙️  AMI Configuration")
    ami_user = input(f"AMI Username [autodialerami]: ").strip() or "autodialerami"
    ami_pass = input("AMI Password: ").strip()

    if not ami_pass:
        print("❌ Password is required")
        return

    # Call Configuration
    print("\n📞 Call Configuration")
    extension = input("Extension [1005]: ").strip() or "1005"
    destination = input("Destination Number (e.g., 9XXXXXXXXXX): ").strip()

    if not destination:
        print("❌ Destination number is required")
        return

    context = input("Context [from-internal]: ").strip() or "from-internal"

    # Confirm
    print(f"\n📋 Summary:")
    print(f"   AMI: {ami_user}@{AMI_HOST}:{AMI_PORT}")
    print(f"   Channel: PJSIP/{extension}")
    print(f"   Destination: {destination}")
    print(f"   Context: {context}")

    confirm = input("\nProceed with call? (y/N): ").lower()
    if confirm != 'y':
        print("❌ Cancelled")
        return

    # Connect to AMI
    sock = login_ami(AMI_HOST, AMI_PORT, ami_user, ami_pass)
    if not sock:
        return

    try:
        # Originate call
        action_id = originate_call(sock, extension, destination, context)

        if action_id:
            # Wait a bit and check status
            print("\n⏳ Waiting 3 seconds...")
            time.sleep(3)

            get_channel_status(sock)

            print("\n" + "=" * 70)
            print("✅ Test call initiated successfully!")
            print("=" * 70)
            print("\n📝 Next steps:")
            print("1. Check if the extension device rings")
            print("2. Answer the call on the extension")
            print("3. The call will be connected to the destination")
            print("4. Check UCM logs: ssh root@192.168.150.10")
            print("   tail -f /var/log/asterisk/full")

    except Exception as e:
        print(f"\n❌ Error during call: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Logout
        logout_ami(sock)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
