# Test Call Instructions

## Quick Test Process

### Step 1: Check Extension Status (Optional but Recommended)

This will verify your AMI connection and check if extension 1005 is registered:

```bash
cd C:\Users\Administrator\Sip-Dialer
python check_extension_status.py
```

**Enter when prompted:**
- AMI Username: `autodialerami` (or your configured username)
- AMI Password: [your AMI password]

**What to expect:**
- ✅ Connected to AMI
- ✅ Login successful
- 📋 Extension 1005 status displayed
- Should show if extension is "Available" or "Unavailable"

### Step 2: Make Test Call

```bash
cd C:\Users\Administrator\Sip-Dialer
python make_test_call.py
```

**Enter when prompted:**
- AMI Username: `autodialerami`
- AMI Password: [your AMI password]
- Extension: `1005`
- Destination: The number to call (e.g., `9XXXXXXXXXX`)
  - Include the outbound route prefix (usually `9`)
  - Example: `91234567890` to dial 1234567890
- Context: `from-internal` (default)

**Important Notes:**
- The destination must match your outbound route pattern
- If unsure about the pattern, check UCM: Call Features → Outbound Routes
- Common patterns:
  - `9NXXXXXXXXX` = 9 + 10-digit US number
  - `NXXXXXXXXX` = Direct 10-digit dialing
  - `011X.` = International (011 + country code + number)

### Step 3: What Happens During the Call

1. **Call Initiation**
   - Script connects to AMI
   - Sends Originate command to extension 1005
   - UCM will ring extension 1005 first

2. **Extension Rings**
   - If you have a phone registered to extension 1005, it will ring
   - Answer the call on extension 1005

3. **Call Connects**
   - After answering extension 1005, UCM will dial the destination
   - You'll hear ringback tone
   - When destination answers, you're connected

4. **During Call**
   - Talk to verify audio quality
   - Test DTMF if needed
   - Hangup when done

## Expected Output

### Successful Call
```
==================================================================
Grandstream UCM Test Call Script
==================================================================

⚙️  AMI Configuration
AMI Username [autodialerami]: autodialerami
AMI Password: ********

📞 Call Configuration
Extension [1005]: 1005
Destination Number (e.g., 9XXXXXXXXXX): 91234567890
Context [from-internal]: from-internal

📋 Summary:
   AMI: autodialerami@192.168.150.10:7777
   Channel: PJSIP/1005
   Destination: 91234567890
   Context: from-internal

Proceed with call? (y/N): y

🔌 Connecting to AMI at 192.168.150.10:7777...
📥 Server: Asterisk Call Manager/5.0.0

🔐 Logging in as 'autodialerami'...
📥 Login Response:
Response: Success
Message: Authentication accepted

✅ AMI login successful!

📞 Initiating call...
   From: PJSIP/1005
   To: 91234567890
   Context: from-internal

📥 Originate Response:
Response: Success
Message: Originate successfully queued

✅ Call origination initiated!

⏳ Waiting 3 seconds...

📊 Checking channel status...
[Channel information displayed]

==================================================================
✅ Test call initiated successfully!
==================================================================
```

### Common Errors and Solutions

#### Error: "Connection refused"
**Problem:** AMI port not accessible
**Solution:**
- Verify UCM is running: `ping 192.168.150.10`
- Check AMI port: `telnet 192.168.150.10 7777`
- Verify firewall allows port 7777

#### Error: "Authentication failed"
**Problem:** Wrong AMI credentials
**Solution:**
- Verify AMI username (must be 8+ characters)
- Check password is correct
- SSH to UCM and verify: `asterisk -rx "manager show users"`

#### Error: "Permission denied"
**Problem:** AMI user lacks originate permission
**Solution:**
- SSH to UCM: `ssh root@192.168.150.10`
- Edit `/etc/asterisk/manager.conf`
- Ensure user has: `write=originate`
- Reload: `asterisk -rx "manager reload"`

#### Error: "No such channel type 'PJSIP'"
**Problem:** Using wrong channel type
**Solution:**
- Ensure using `PJSIP/1005` not `SIP/1005`
- Grandstream UCM uses PJSIP

#### Error: "Extension X is invalid"
**Problem:** Destination doesn't match outbound route
**Solution:**
- Check outbound routes in UCM web GUI
- Verify destination matches a dial pattern
- Try prefixing with 9: `9XXXXXXXXXX`

#### Error: "Originate successfully queued" but no ring
**Problem:** Extension not registered or privilege issue
**Solution:**
1. Check registration:
   ```bash
   ssh root@192.168.150.10
   asterisk -rvvv
   pjsip show endpoints
   ```
2. Verify extension privilege is "International"
3. Check extension has device registered

## Monitoring the Call

### Real-time Asterisk Console
```bash
ssh root@192.168.150.10
asterisk -rvvv

# Inside Asterisk CLI:
core set verbose 5
pjsip set logger on
```

You'll see:
- SIP INVITE messages
- Call setup progress
- Audio codec negotiation
- Call completion

### Check Logs
```bash
ssh root@192.168.150.10

# Full log
tail -f /var/log/asterisk/full

# Messages only
tail -f /var/log/asterisk/messages

# CDR
tail -f /var/log/asterisk/cdr-csv/Master.csv
```

## Troubleshooting Checklist

Before making a call, verify:

- [ ] UCM is reachable: `ping 192.168.150.10`
- [ ] AMI port accessible: `telnet 192.168.150.10 7777`
- [ ] AMI user exists with correct permissions
- [ ] Extension 1005 created in UCM
- [ ] Extension privilege set to "International" (Web GUI)
- [ ] Extension has device registered (or will ring SIP URI)
- [ ] Outbound route configured for destination pattern
- [ ] Trunk registered (if using external trunk)

## Alternative: Direct AMI Commands via Telnet

If the Python script doesn't work, you can test manually:

```bash
telnet 192.168.150.10 7777
```

Then type:
```
Action: Login
Username: autodialerami
Secret: your_password

Action: Originate
Channel: PJSIP/1005
Context: from-internal
Exten: 91234567890
Priority: 1
CallerID: 1005
Timeout: 30000
Async: true

Action: Logoff

```

(Press Enter after each blank line)

## Next Steps After Successful Test

Once the test call works:

1. **Configure Auto-Dialer SIP Settings**
   - Use Web UI at http://localhost:3000
   - Settings → SIP Settings
   - Enter extension credentials

2. **Create a Campaign**
   - Upload contact list
   - Configure IVR flow
   - Set dialing parameters

3. **Monitor Performance**
   - Check call success rate
   - Review call quality
   - Monitor UCM resources

## Need Help?

**Check Extension Status:**
```bash
python check_extension_status.py
```

**View Setup Guide:**
- See: `GRANDSTREAM_SETUP_GUIDE.md`
- See: `SIP_CONNECTION_TEST.md`

**UCM Web Interface:**
- URL: http://192.168.150.10
- Check: Extension/Trunk → Extensions → 1005
- Verify: Green circle (registered)

**AMI Credentials Required:**
- Username must be 8+ characters
- User must have originate permission
- IP access control may need updating
