# SIP Connection Test Guide

## Test Results - 2025-12-18

### Network Connectivity Tests

✅ **UCM Reachability**
- IP: 192.168.150.10
- Ping: SUCCESS (0% packet loss, <1ms latency)
- Status: UCM is online and responding

✅ **SIP Port (5060/UDP)**
- Test: SUCCESS
- Port is open and accepting connections

✅ **AMI Port (7777/TCP)**
- Test: SUCCESS
- Port is open and accepting connections

### Prerequisites Checklist

Before testing the SIP connection, ensure these are completed on the UCM:

#### 1. Extension Configuration (via SSH or Web GUI)
- [ ] Extension 1005 created
- [ ] Transport: PJSIP
- [ ] Password set (16+ characters recommended)
- [ ] Privilege set to "International" (MUST be done via Web GUI)
- [ ] IP ACL configured (optional but recommended)

#### 2. AMI User Configuration (via SSH or Web GUI)
- [ ] AMI user created (username must be 8+ characters)
- [ ] Password set (16+ characters recommended)
- [ ] Permissions: read,write,originate
- [ ] IP ACL configured (optional but recommended)

#### 3. Outbound Routes
- [ ] At least one outbound route configured
- [ ] Route privilege ≤ extension privilege
- [ ] Trunk configured and registered (if needed)

## Quick Setup Commands (Run on UCM)

If you haven't set up the extension and AMI user yet, use these commands:

### SSH into UCM
```bash
ssh root@192.168.150.10
```

### Create Extension 1005 (via Asterisk)
```bash
# Generate random password
EXT_PASS=$(openssl rand -base64 16)
echo "Extension Password: $EXT_PASS"

# Create PJSIP endpoint configuration
cat >> /etc/asterisk/pjsip.conf << EOF

[1005]
type=endpoint
context=from-internal
disallow=all
allow=ulaw,alaw,g722
transport=transport-udp
auth=1005
aors=1005
callerid=Auto Dialer <1005>

[1005]
type=auth
auth_type=userpass
password=$EXT_PASS
username=1005

[1005]
type=aor
max_contacts=1
remove_existing=yes

EOF

# Reload PJSIP
asterisk -rx "module reload res_pjsip.so"
asterisk -rx "pjsip reload"
```

### Create AMI User
```bash
# Generate random password
AMI_PASS=$(openssl rand -base64 16)
echo "AMI Password: $AMI_PASS"

# Create AMI user
cat >> /etc/asterisk/manager.conf << EOF

[autodialerami]
secret=$AMI_PASS
deny=0.0.0.0/0.0.0.0
permit=192.168.150.0/255.255.255.0
read=system,call,log,verbose,command,agent,user,originate
write=system,call,log,verbose,command,agent,user,originate

EOF

# Reload AMI
asterisk -rx "manager reload"
```

### Verify Configuration
```bash
# Check PJSIP endpoint
asterisk -rx "pjsip show endpoints"
asterisk -rx "pjsip show endpoint 1005"

# Check AMI users
asterisk -rx "manager show users"
```

## Testing SIP Connection

### Option 1: Using the Python Test Script

```bash
cd C:\Users\Administrator\Sip-Dialer
python test_sip_connection.py
```

Follow the prompts to:
1. Login with your auto-dialer credentials
2. Enter SIP settings (server, extension, password)
3. Enter AMI settings (host, username, password)
4. Test the connection

### Option 2: Manual Configuration via Web UI

1. **Access Auto-Dialer**
   ```
   URL: http://localhost:3000
   ```

2. **Navigate to Settings**
   - Login with your credentials
   - Click "Settings" in sidebar
   - Go to "SIP Settings" tab

3. **Configure SIP Extension**
   ```
   SIP Server: 192.168.150.10
   Port: 5060
   Username: 1005
   Password: [your extension password]
   Transport: UDP
   Registration Required: Yes
   Register Expires: 300
   Keepalive Enabled: Yes
   Keepalive Interval: 30
   ```

4. **Configure Codecs**
   ```
   Select: PCMU, PCMA, G722 (in this order)
   ```

5. **Configure RTP**
   ```
   RTP Port Start: 10000
   RTP Port End: 20000
   ```

6. **Configure AMI**
   ```
   AMI Host: 192.168.150.10
   AMI Port: 7777
   AMI Username: autodialerami
   AMI Password: [your AMI password]
   ```

7. **Test Connection**
   - Click "Test Connection" button
   - Should show: ✅ Connection successful

8. **Save Settings**
   - Click "Save" button
   - Settings will be persisted to database

## Verification Steps

### 1. Check Extension Registration on UCM

**Via Web GUI:**
```
1. Open: http://192.168.150.10
2. Login with admin credentials
3. Navigate to: Extension/Trunk → Extensions
4. Find extension 1005
5. Look for green circle (registered)
6. Verify IP address shows auto-dialer IP
```

**Via SSH:**
```bash
ssh root@192.168.150.10
asterisk -rvvv

# Check endpoints
pjsip show endpoints

# Check specific endpoint
pjsip show endpoint 1005

# Check contacts
pjsip show contacts
```

Expected output when registered:
```
Endpoint:  1005/1005                                            Available     1 of 1
...
Contact:  1005/sip:1005@192.168.150.x:5060                      Available
```

### 2. Check AMI Connection

**Test from auto-dialer server:**
```bash
telnet 192.168.150.10 7777
```

Should see:
```
Asterisk Call Manager/5.0.0
```

Then test login:
```
Action: Login
Username: autodialerami
Secret: [your AMI password]

```

Should receive:
```
Response: Success
Message: Authentication accepted
```

### 3. Test Call Origination

**Via AMI (telnet):**
```
Action: Originate
Channel: PJSIP/1005
Context: from-internal
Exten: 9XXXXXXXXXX
Priority: 1
CallerID: 1005
Timeout: 30000
Async: true

```

Replace `9XXXXXXXXXX` with:
- 9 (or your outbound route prefix)
- Followed by destination number

### 4. Check Asterisk Logs

**View real-time logs:**
```bash
ssh root@192.168.150.10
tail -f /var/log/asterisk/full
```

Look for:
- Registration messages
- AMI authentication
- Call origination events

## Troubleshooting

### Extension Won't Register

**Check 1: Verify credentials**
```bash
# On UCM
asterisk -rx "pjsip show endpoint 1005"
```

**Check 2: Look for auth failures**
```bash
tail -100 /var/log/asterisk/messages | grep -i "auth\|1005"
```

**Check 3: Network/Firewall**
```bash
# From auto-dialer
ping 192.168.150.10
telnet 192.168.150.10 5060
```

### AMI Connection Fails

**Check 1: Verify AMI user exists**
```bash
asterisk -rx "manager show users"
```

**Check 2: Check AMI is listening**
```bash
netstat -tuln | grep 7777
ss -tuln | grep 7777
```

**Check 3: Test basic connectivity**
```bash
telnet 192.168.150.10 7777
```

### Registration Succeeds but Calls Fail

**Check 1: Extension privilege**
- Must be set to "International" via Web GUI
- Cannot be set via configuration files

**Check 2: Outbound routes**
```bash
asterisk -rx "dialplan show from-internal"
```

**Check 3: Trunk status**
- Web GUI → Extension/Trunk → VoIP Trunks
- Verify trunk is registered

## Common Issues

### Issue: "Authentication failed"
**Solution:**
- Verify password is correct
- Check username is exactly "1005"
- Ensure no typos in password

### Issue: "Network unreachable"
**Solution:**
- Verify UCM IP: 192.168.150.10
- Check firewall allows UDP 5060
- Verify auto-dialer can reach UCM network

### Issue: "Registration timeout"
**Solution:**
- Check UCM is running: `ping 192.168.150.10`
- Verify SIP port: `telnet 192.168.150.10 5060`
- Check UCM not overloaded

### Issue: "Calls not routing"
**Solution:**
1. Set extension privilege to "International" (Web GUI only)
2. Verify outbound route exists
3. Check dial pattern matches destination
4. Verify trunk is registered

### Issue: "One-way or no audio"
**Solution:**
- Check RTP ports 10000-20000 are open (UDP)
- Verify NAT settings on UCM
- Check codec compatibility (use PCMU/PCMA)

## Security Notes

### Recommended Password Strength
- **SIP Password**: 16+ characters, mixed case, numbers, symbols
- **AMI Password**: 16+ characters, mixed case, numbers, symbols

Example generation:
```bash
openssl rand -base64 16
```

### IP Access Control
Configure IP ACL on UCM to restrict access:
- Extension 1005: Allow only auto-dialer IP
- AMI user: Allow only auto-dialer IP

Format: `192.168.150.100/32` (single IP)

### Monitoring
- Enable failed authentication alerts
- Monitor CDR for unusual patterns
- Review AMI logs regularly

## Next Steps After Successful Connection

1. **Create a Campaign**
   - Navigate to: Campaigns → New Campaign
   - Select IVR flow (once IVR builder is tested)
   - Upload contact list
   - Configure dialing settings

2. **Test Single Call**
   - Use campaign to dial one test number
   - Verify call connects
   - Check audio quality
   - Test IVR interactions

3. **Monitor Performance**
   - Check call success rate
   - Monitor registration stability
   - Review call quality metrics

## Summary

✅ Network connectivity verified
✅ SIP port accessible (5060)
✅ AMI port accessible (7777)
⏳ Extension configuration (pending)
⏳ AMI user configuration (pending)
⏳ SIP registration test (pending)
⏳ Call origination test (pending)

**Ready to proceed with:**
1. Setting up extension 1005 on UCM
2. Setting up AMI user on UCM
3. Configuring auto-dialer SIP settings
4. Testing registration and calls

**Questions?**
- Check GRANDSTREAM_SETUP_GUIDE.md for detailed procedures
- Review UCM documentation
- Check Asterisk logs for errors
