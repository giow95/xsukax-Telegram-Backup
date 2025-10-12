from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.tl.functions.contacts import GetContactsRequest
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
import threading
import queue
import time
import hashlib

app = Flask(__name__)
CORS(app)

log_queue = queue.Queue()
progress_queue = queue.Queue()
client_lock = asyncio.Lock()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>xsukax Telegram Backup</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; background: #0d1117; color: #c9d1d9; line-height: 1.6; }
.container { max-width: 900px; margin: 0 auto; padding: 20px; }
.header { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 24px; margin-bottom: 20px; text-align: center; }
.header h1 { color: #58a6ff; font-size: 28px; margin-bottom: 8px; }
.header .tagline { color: #8b949e; font-size: 14px; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 20px; margin-bottom: 20px; }
.card h2 { color: #c9d1d9; font-size: 18px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #21262d; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; color: #8b949e; font-size: 14px; margin-bottom: 6px; }
.form-group input { width: 100%; padding: 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; font-size: 14px; }
.form-group input[type="number"] { width: 100px; }
.form-group input:focus { outline: none; border-color: #58a6ff; }
.checkbox-group { display: flex; align-items: center; margin-bottom: 12px; }
.checkbox-group input[type="checkbox"] { width: 18px; height: 18px; margin-right: 8px; cursor: pointer; }
.checkbox-group label { color: #c9d1d9; font-size: 14px; cursor: pointer; flex: 1; }
.btn { padding: 10px 20px; background: #238636; color: white; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; font-weight: 600; }
.btn:hover { background: #2ea043; }
.btn:disabled { background: #21262d; color: #484f58; cursor: not-allowed; }
.backup-options { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 16px; }
.backup-btn { padding: 16px; background: #0d1117; border: 2px solid #30363d; border-radius: 6px; cursor: pointer; text-align: center; transition: all 0.2s; }
.backup-btn:hover { border-color: #58a6ff; background: #161b22; }
.backup-btn .icon { font-size: 24px; margin-bottom: 8px; }
.backup-btn .title { color: #c9d1d9; font-weight: 600; margin-bottom: 4px; }
.backup-btn .desc { color: #8b949e; font-size: 12px; }
.console { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 16px; height: 300px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 13px; }
.console-line { margin-bottom: 4px; color: #8b949e; }
.console-line.success { color: #3fb950; }
.console-line.error { color: #f85149; }
.console-line.info { color: #58a6ff; }
.progress-container { margin-top: 16px; display: none; }
.progress-bar { width: 100%; height: 24px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #238636, #2ea043); transition: width 0.3s; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: 600; }
.step { display: none; }
.step.active { display: block; }
.filter-section { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 16px; margin-top: 16px; display: none; }
.filter-section h3 { color: #58a6ff; font-size: 16px; margin-bottom: 12px; }
.filter-grid { display: grid; gap: 12px; }
.section-title { color: #8b949e; font-size: 13px; font-weight: 600; margin-top: 12px; margin-bottom: 8px; border-bottom: 1px solid #21262d; padding-bottom: 4px; }
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>🚀 xsukax Telegram Backup</h1>
<div class="tagline">Secure, Fast, and Easy Telegram Backup Tool</div>
</div>

<div class="card step active" id="step1">
<h2>Step 1: API Credentials</h2>
<div class="form-group">
<label>API ID</label>
<input type="text" id="api_id" placeholder="Enter your API ID">
</div>
<div class="form-group">
<label>API Hash</label>
<input type="text" id="api_hash" placeholder="Enter your API Hash">
</div>
<div class="form-group">
<label>Phone Number</label>
<input type="text" id="phone" placeholder="+1234567890">
</div>
<button class="btn" onclick="sendCode()">Send Verification Code</button>
</div>

<div class="card step" id="step2">
<h2>Step 2: Verification Code</h2>
<div class="form-group">
<label>Enter the code sent to your Telegram</label>
<input type="text" id="otp_code" placeholder="12345">
</div>
<button class="btn" onclick="verifyCode()">Verify Code</button>
</div>

<div class="card step" id="step3">
<h2>Step 3: Two-Step Verification</h2>
<div class="form-group">
<label>Enter your 2FA password</label>
<input type="password" id="password_2fa" placeholder="Your password">
</div>
<button class="btn" onclick="verify2FA()">Verify Password</button>
</div>

<div class="card step" id="step4">
<h2>✅ Connected | Select Backup Option</h2>
<div style="background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; margin-bottom: 16px; display: none;" id="userInfo">
<div style="color: #58a6ff; font-size: 14px; font-weight: 600;" id="userName">👤 User</div>
<div style="color: #8b949e; font-size: 12px; margin-top: 4px;" id="userPhone">📱 Phone</div>
</div>
<div class="backup-options">
<div class="backup-btn" onclick="startBackup('contacts_html')">
<div class="icon">📄</div>
<div class="title">Contacts HTML</div>
<div class="desc">Searchable web page</div>
</div>
<div class="backup-btn" onclick="startBackup('contacts_vcf')">
<div class="icon">📇</div>
<div class="title">Contacts VCF</div>
<div class="desc">Import to phone</div>
</div>
<div class="backup-btn" onclick="showFilters()">
<div class="icon">💬</div>
<div class="title">Backup Chats</div>
<div class="desc">Configure & backup</div>
</div>
</div>
<div class="filter-section" id="filterSection">
<h3>⚙️ Chat Backup Options</h3>
<div class="filter-grid">
<div class="section-title">📥 Download Media Types</div>
<div class="checkbox-group">
<input type="checkbox" id="download_images" checked>
<label for="download_images">Download images (.jpg, .png, .gif, .webp)</label>
</div>
<div class="checkbox-group">
<input type="checkbox" id="download_videos">
<label for="download_videos">Download videos (.mp4, .mov, .avi, .mkv)</label>
</div>
<div class="checkbox-group">
<input type="checkbox" id="download_documents">
<label for="download_documents">Download documents (.pdf, .doc, .xls, .zip, etc.)</label>
</div>
<div class="checkbox-group">
<input type="checkbox" id="download_voice">
<label for="download_voice">Download voice messages & audio files</label>
</div>

<div class="section-title">🎯 File Size Limits</div>
<div class="checkbox-group">
<input type="checkbox" id="skip_large_files" checked>
<label for="skip_large_files">Skip files larger than <input type="number" id="max_file_size" value="50" min="1" max="2000" style="width:70px;"> MB</label>
</div>

<div class="section-title">📅 Date Range</div>
<div class="checkbox-group">
<input type="checkbox" id="date_limit">
<label for="date_limit">Only backup messages from last <input type="number" id="days_limit" value="180" min="1" max="3650" style="width:70px;"> days</label>
</div>

<div class="section-title">💾 Quick Presets</div>
<div style="display: flex; gap: 8px; margin-top: 8px;">
<button class="btn" onclick="setPreset('text')" style="background: #21262d;">Text Only</button>
<button class="btn" onclick="setPreset('images')" style="background: #21262d;">Images Only</button>
<button class="btn" onclick="setPreset('full')" style="background: #21262d;">Full Backup</button>
</div>
</div>
<button class="btn" style="margin-top:16px; width: 100%;" onclick="startChatBackup()">🚀 Start Chat Backup</button>
</div>
<div class="progress-container" id="progressContainer">
<div class="progress-bar">
<div class="progress-fill" id="progressFill">0%</div>
</div>
</div>
</div>

<div class="card">
<h2>📟 Console Output</h2>
<div class="console" id="console"></div>
</div>
</div>

<script>
let sessionData = {};

window.addEventListener('DOMContentLoaded', function() {
    checkExistingSession();
});

async function checkExistingSession() {
    addLog('Checking for existing session...', 'info');
    
    try {
        const response = await fetch('/api/check_session');
        const data = await response.json();
        
        if (data.success) {
            addLog('Found existing session!', 'success');
            addLog(`Welcome back, ${data.user.name || data.user.phone}!`, 'success');
            
            document.getElementById('userInfo').style.display = 'block';
            document.getElementById('userName').textContent = '👤 ' + (data.user.name || 'User');
            document.getElementById('userPhone').textContent = '📱 ' + (data.user.phone || 'No phone');
            
            showStep(4);
        } else {
            addLog('No existing session found. Please login.', 'info');
        }
    } catch (error) {
        addLog('No existing session. Please login.', 'info');
    }
}

function showStep(step) {
    document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
    document.getElementById('step' + step).classList.add('active');
}

function addLog(message, type = 'info') {
    const console = document.getElementById('console');
    const line = document.createElement('div');
    line.className = 'console-line ' + type;
    line.textContent = new Date().toLocaleTimeString() + ' | ' + message;
    console.appendChild(line);
    console.scrollTop = console.scrollHeight;
}

async function sendCode() {
    const api_id = document.getElementById('api_id').value;
    const api_hash = document.getElementById('api_hash').value;
    const phone = document.getElementById('phone').value;
    
    if (!api_id || !api_hash || !phone) {
        addLog('Please fill all fields', 'error');
        return;
    }
    
    sessionData = { api_id, api_hash, phone };
    addLog('Connecting to Telegram...', 'info');
    
    try {
        const response = await fetch('/api/send_code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sessionData)
        });
        const data = await response.json();
        
        if (data.success) {
            addLog('Verification code sent!', 'success');
            showStep(2);
        } else {
            addLog('Error: ' + data.error, 'error');
        }
    } catch (error) {
        addLog('Error: ' + error.message, 'error');
    }
}

async function verifyCode() {
    const otp_code = document.getElementById('otp_code').value;
    
    if (!otp_code) {
        addLog('Please enter the code', 'error');
        return;
    }
    
    sessionData.otp_code = otp_code;
    addLog('Verifying code...', 'info');
    
    try {
        const response = await fetch('/api/verify_code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sessionData)
        });
        const data = await response.json();
        
        if (data.success) {
            addLog('Successfully logged in!', 'success');
            
            document.getElementById('userInfo').style.display = 'block';
            document.getElementById('userName').textContent = '👤 ' + sessionData.phone;
            document.getElementById('userPhone').textContent = '📱 ' + sessionData.phone;
            
            showStep(4);
        } else if (data.needs_password) {
            addLog('2FA is enabled. Please enter your password', 'info');
            showStep(3);
        } else {
            addLog('Error: ' + data.error, 'error');
        }
    } catch (error) {
        addLog('Error: ' + error.message, 'error');
    }
}

async function verify2FA() {
    const password = document.getElementById('password_2fa').value;
    
    if (!password) {
        addLog('Please enter your password', 'error');
        return;
    }
    
    sessionData.password = password;
    addLog('Verifying 2FA password...', 'info');
    
    try {
        const response = await fetch('/api/verify_2fa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sessionData)
        });
        const data = await response.json();
        
        if (data.success) {
            addLog('Successfully logged in!', 'success');
            
            document.getElementById('userInfo').style.display = 'block';
            document.getElementById('userName').textContent = '👤 ' + sessionData.phone;
            document.getElementById('userPhone').textContent = '📱 ' + sessionData.phone;
            
            showStep(4);
        } else {
            addLog('Error: ' + data.error, 'error');
        }
    } catch (error) {
        addLog('Error: ' + error.message, 'error');
    }
}

function showFilters() {
    document.getElementById('filterSection').style.display = 'block';
    document.getElementById('filterSection').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function setPreset(type) {
    if (type === 'text') {
        document.getElementById('download_images').checked = false;
        document.getElementById('download_videos').checked = false;
        document.getElementById('download_documents').checked = false;
        document.getElementById('download_voice').checked = false;
        addLog('Preset: Text only (fastest)', 'info');
    } else if (type === 'images') {
        document.getElementById('download_images').checked = true;
        document.getElementById('download_videos').checked = false;
        document.getElementById('download_documents').checked = false;
        document.getElementById('download_voice').checked = false;
        addLog('Preset: Images only', 'info');
    } else if (type === 'full') {
        document.getElementById('download_images').checked = true;
        document.getElementById('download_videos').checked = true;
        document.getElementById('download_documents').checked = true;
        document.getElementById('download_voice').checked = true;
        document.getElementById('skip_large_files').checked = false;
        document.getElementById('date_limit').checked = false;
        addLog('Preset: Full backup (slowest)', 'info');
    }
}

function startChatBackup() {
    const filters = {
        download_images: document.getElementById('download_images').checked,
        download_videos: document.getElementById('download_videos').checked,
        download_documents: document.getElementById('download_documents').checked,
        download_voice: document.getElementById('download_voice').checked,
        skip_large_files: document.getElementById('skip_large_files').checked,
        max_file_size: parseInt(document.getElementById('max_file_size').value) || 50,
        date_limit: document.getElementById('date_limit').checked,
        days_limit: parseInt(document.getElementById('days_limit').value) || 180
    };
    startBackup('chats', filters);
}

async function startBackup(type, filters = {}) {
    addLog('Starting backup: ' + type, 'info');
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressFill').textContent = '0%';
    
    try {
        const response = await fetch('/api/backup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, filters })
        });
        const data = await response.json();
        
        if (data.success) {
            addLog('Backup started successfully!', 'success');
            pollProgress();
        } else {
            addLog('Error: ' + data.error, 'error');
        }
    } catch (error) {
        addLog('Error: ' + error.message, 'error');
    }
}

function pollProgress() {
    const interval = setInterval(async () => {
        try {
            const response = await fetch('/api/progress');
            const data = await response.json();
            
            if (data.logs && data.logs.length > 0) {
                data.logs.forEach(log => addLog(log.message, log.type));
            }
            
            if (data.progress !== undefined) {
                const percent = Math.round(data.progress);
                document.getElementById('progressFill').style.width = percent + '%';
                document.getElementById('progressFill').textContent = percent + '%';
            }
            
            if (data.completed) {
                clearInterval(interval);
                addLog('Backup completed! ✅', 'success');
                document.getElementById('progressFill').style.width = '100%';
                document.getElementById('progressFill').textContent = '100%';
            }
        } catch (error) {
            console.error('Error polling:', error);
        }
    }, 500);
}

addLog('Welcome to xsukax Telegram Backup!', 'success');
</script>
</body>
</html>
"""

class TelegramBackupWeb:
    def __init__(self):
        self.client = None
        self.phone = None
        self.output_dir = Path('xsukax_TB')
        self.output_dir.mkdir(exist_ok=True)
        self.user_colors = {}
        self.completed_chats = 0
        self.total_chats = 0
        self.downloaded_files = 0
        
    def get_user_color(self, user_id, username):
        if user_id not in self.user_colors:
            seed = str(user_id) + (username or '')
            hash_obj = hashlib.md5(seed.encode())
            hash_hex = hash_obj.hexdigest()
            
            hue = int(hash_hex[:8], 16) % 360
            colors = [
                f'hsl({hue}, 70%, 60%)',
                f'hsl({(hue + 30) % 360}, 70%, 60%)',
                f'hsl({(hue + 60) % 360}, 70%, 60%)',
                f'hsl({(hue + 90) % 360}, 70%, 60%)',
                f'hsl({(hue + 120) % 360}, 70%, 60%)',
                f'hsl({(hue + 150) % 360}, 70%, 60%)',
            ]
            self.user_colors[user_id] = colors[user_id % len(colors)]
        
        return self.user_colors[user_id]
    
    def detect_rtl(self, text):
        if not text:
            return False
        rtl_ranges = [
            (0x0600, 0x06FF),
            (0x0750, 0x077F),
            (0x08A0, 0x08FF),
            (0xFB50, 0xFDFF),
            (0xFE70, 0xFEFF),
        ]
        for char in text[:100]:
            code = ord(char)
            if any(start <= code <= end for start, end in rtl_ranges):
                return True
        return False
    
    async def connect_existing_session(self):
        try:
            async with client_lock:
                session_file = 'session_xsukax'
                if not Path(f"{session_file}.session").exists():
                    return False, None
                
                self.client = TelegramClient(session_file, 0, '')
                await self.client.connect()
                
                if await self.client.is_user_authorized():
                    me = await self.client.get_me()
                    return True, {
                        'name': f"{me.first_name or ''} {me.last_name or ''}".strip(),
                        'phone': me.phone or '',
                        'username': me.username or ''
                    }
                else:
                    await self.client.disconnect()
                    return False, None
        except Exception:
            return False, None
    
    async def connect(self, api_id, api_hash, phone):
        async with client_lock:
            self.phone = phone
            session_file = 'session_xsukax'
            self.client = TelegramClient(session_file, api_id, api_hash)
            await self.client.connect()
            return self.client
    
    async def send_code(self):
        async with client_lock:
            await self.client.send_code_request(self.phone)
    
    async def sign_in(self, code):
        async with client_lock:
            try:
                await self.client.sign_in(self.phone, code)
                return True, False
            except SessionPasswordNeededError:
                return False, True
            except PhoneCodeInvalidError:
                raise Exception("Invalid verification code")
    
    async def sign_in_password(self, password):
        async with client_lock:
            await self.client.sign_in(password=password)
    
    async def backup_contacts_html(self):
        log_queue.put({"message": "Fetching contacts...", "type": "info"})
        async with client_lock:
            result = await self.client(GetContactsRequest(hash=0))
        contacts = result.users
        log_queue.put({"message": f"Found {len(contacts)} contacts", "type": "success"})
        
        contacts_data = []
        for contact in contacts:
            contacts_data.append({
                'first_name': contact.first_name or '',
                'last_name': contact.last_name or '',
                'username': contact.username or '',
                'phone': contact.phone or '',
            })
        
        contacts_data.sort(key=lambda x: (x['first_name'].lower(), x['last_name'].lower()))
        html_content = self.generate_contacts_html(contacts_data)
        
        output_file = self.output_dir / "contacts_backup.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        log_queue.put({"message": f"Contacts saved to {output_file}", "type": "success"})
        progress_queue.put(100)
        return output_file
    
    async def backup_contacts_vcf(self):
        log_queue.put({"message": "Fetching contacts...", "type": "info"})
        async with client_lock:
            result = await self.client(GetContactsRequest(hash=0))
        contacts = result.users
        log_queue.put({"message": f"Found {len(contacts)} contacts", "type": "success"})
        
        output_file = self.output_dir / "contacts_backup.vcf"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for contact in contacts:
                full_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip() or "Unknown"
                phone = contact.phone or ''
                username = contact.username or ''
                
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:{full_name}\n")
                
                if contact.first_name or contact.last_name:
                    f.write(f"N:{contact.last_name or ''};{contact.first_name or ''};;;\n")
                
                if phone:
                    f.write(f"TEL;TYPE=CELL:+{phone}\n")
                
                if username:
                    f.write(f"X-TELEGRAM:@{username}\n")
                    f.write(f"URL:https://t.me/{username}\n")
                
                f.write("END:VCARD\n\n")
        
        log_queue.put({"message": f"Contacts saved to {output_file}", "type": "success"})
        progress_queue.put(100)
        return output_file
    
    async def backup_chats(self, filters=None):
        if filters is None:
            filters = {}
        
        chat_dir = self.output_dir / "Chats"
        chat_dir.mkdir(exist_ok=True)
        
        has_media = any([
            filters.get('download_images'),
            filters.get('download_videos'),
            filters.get('download_documents'),
            filters.get('download_voice')
        ])
        
        if has_media:
            media_dir = chat_dir / "media"
            media_dir.mkdir(exist_ok=True)
        
        log_queue.put({"message": "Fetching conversations...", "type": "info"})
        async with client_lock:
            dialogs = await self.client.get_dialogs()
            me = await self.client.get_me()
        
        my_id = me.id
        self.total_chats = len(dialogs)
        self.completed_chats = 0
        
        log_queue.put({"message": f"Found {self.total_chats} conversations", "type": "success"})
        log_queue.put({"message": f"Settings: {self.format_filters(filters)}", "type": "info"})
        log_queue.put({"message": "Processing chats sequentially for stability...", "type": "info"})
        
        date_limit = None
        if filters.get('date_limit'):
            days = filters.get('days_limit', 180)
            date_limit = datetime.now(tz=None).replace(tzinfo=None) - timedelta(days=days)
            log_queue.put({"message": f"Date filter: Messages from last {days} days", "type": "info"})
        
        # Process each chat sequentially to avoid event loop issues
        for dialog in dialogs:
            try:
                chat_name = dialog.name or "Unknown"
                safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in chat_name)
                
                log_queue.put({"message": f"📥 Starting: {chat_name}", "type": "info"})
                
                messages = []
                media_messages = []
                
                # Fetch all messages for this chat
                async with client_lock:
                    async for message in self.client.iter_messages(dialog):
                        msg_date = message.date.replace(tzinfo=None) if message.date else datetime.now().replace(tzinfo=None)
                        
                        if date_limit and msg_date < date_limit:
                            break
                        
                        sender_name = await self.get_sender_name(message)
                        sender_id = message.sender_id or 0
                        is_me = sender_id == my_id
                        
                        msg_data = {
                            'date': message.date,
                            'sender': sender_name,
                            'sender_id': sender_id,
                            'is_me': is_me,
                            'text': message.text or '',
                            'media': None,
                            'message': message
                        }
                        
                        if has_media and message.media and self.should_download_media(message, filters):
                            media_messages.append(msg_data)
                        
                        messages.append(msg_data)
                
                # Download media for this chat
                if has_media and media_messages:
                    log_queue.put({
                        "message": f"📥 {chat_name}: Downloading {len(media_messages)} files...",
                        "type": "info"
                    })
                    
                    for idx, msg_data in enumerate(media_messages):
                        try:
                            await self.download_single_media(msg_data, safe_name, chat_dir)
                            self.downloaded_files += 1
                            
                            if (idx + 1) % 10 == 0:
                                log_queue.put({
                                    "message": f"📊 {chat_name}: {idx + 1}/{len(media_messages)} files",
                                    "type": "info"
                                })
                        except Exception:
                            pass
                
                # Clean up message objects
                for msg in messages:
                    if 'message' in msg:
                        del msg['message']
                
                # Generate HTML
                messages.reverse()
                html_content = self.generate_chat_html(chat_name, messages)
                
                output_file = chat_dir / f"{safe_name}.html"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # Update progress
                self.completed_chats += 1
                progress = (self.completed_chats / self.total_chats) * 100
                progress_queue.put(progress)
                
                media_count = len([m for m in messages if m['media']])
                log_queue.put({
                    "message": f"✅ {chat_name} ({len(messages)} messages, {media_count} media)",
                    "type": "success"
                })
                
            except Exception as e:
                log_queue.put({"message": f"❌ {dialog.name}: {str(e)}", "type": "error"})
        
        progress_queue.put(100)
        log_queue.put({"message": f"✅ Backup complete! Total files: {self.downloaded_files}", "type": "success"})
    
    def format_filters(self, filters):
        parts = []
        media_types = []
        if filters.get('download_images'):
            media_types.append("Images")
        if filters.get('download_videos'):
            media_types.append("Videos")
        if filters.get('download_documents'):
            media_types.append("Docs")
        if filters.get('download_voice'):
            media_types.append("Audio")
        
        if media_types:
            parts.append(f"Media: {', '.join(media_types)}")
        else:
            parts.append("Text only")
        
        if filters.get('skip_large_files'):
            parts.append(f"Max {filters.get('max_file_size', 50)}MB")
        
        return " | ".join(parts) if parts else "Default settings"
    
    def should_download_media(self, message, filters):
        if not message.media:
            return False
        
        is_photo = isinstance(message.media, MessageMediaPhoto)
        is_document = isinstance(message.media, MessageMediaDocument)
        
        if is_photo:
            return filters.get('download_images', False)
        
        if is_document and message.file:
            mime = message.file.mime_type or ''
            
            if 'video' in mime:
                if not filters.get('download_videos', False):
                    return False
            elif 'audio' in mime or 'ogg' in mime:
                if not filters.get('download_voice', False):
                    return False
            else:
                if not filters.get('download_documents', False):
                    return False
            
            if filters.get('skip_large_files'):
                max_size = filters.get('max_file_size', 50) * 1024 * 1024
                if hasattr(message.file, 'size') and message.file.size:
                    if message.file.size > max_size:
                        return False
            
            return True
        
        return False
    
    async def download_single_media(self, msg_data, chat_name, base_dir):
        try:
            message = msg_data['message']
            media_dir = base_dir / "media" / chat_name
            media_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"msg_{message.id}"
            
            if isinstance(message.media, MessageMediaPhoto):
                filename += ".jpg"
            elif isinstance(message.media, MessageMediaDocument):
                if message.file and message.file.ext:
                    filename += f".{message.file.ext}"
                else:
                    filename += ".bin"
            
            file_path = media_dir / filename
            
            if not file_path.exists() or file_path.stat().st_size == 0:
                async with client_lock:
                    await message.download_media(file_path)
            
            msg_data['media'] = f"media/{chat_name}/{filename}"
        except Exception:
            pass
    
    async def get_sender_name(self, message):
        if message.sender:
            if hasattr(message.sender, 'first_name'):
                name = message.sender.first_name or ''
                if hasattr(message.sender, 'last_name') and message.sender.last_name:
                    name += ' ' + message.sender.last_name
                return name or 'Unknown'
            elif hasattr(message.sender, 'title'):
                return message.sender.title
        return 'Unknown'
    
    def generate_contacts_html(self, contacts_data):
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>xsukax Contacts Backup</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; background: #0d1117; color: #c9d1d9; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
.header {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 20px; margin-bottom: 20px; }}
.header h1 {{ color: #58a6ff; font-size: 24px; }}
.contact {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; margin-bottom: 12px; }}
.contact-name {{ color: #58a6ff; font-weight: 600; font-size: 16px; }}
.contact-details {{ color: #8b949e; font-size: 13px; margin-top: 4px; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>👥 xsukax Contacts Backup</h1>
<p style="color: #8b949e; margin-top: 8px;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {len(contacts_data)} contacts</p>
</div>
"""
        
        for contact in contacts_data:
            full_name = f"{contact['first_name']} {contact['last_name']}".strip() or "Unknown"
            username = f"@{contact['username']}" if contact['username'] else ''
            phone = f"+{contact['phone']}" if contact['phone'] else ''
            
            html += f"""
<div class="contact">
<div class="contact-name">{full_name}</div>
<div class="contact-details">{username} {phone}</div>
</div>
"""
        
        html += """
</div>
</body>
</html>"""
        return html
    
    def generate_chat_html(self, chat_name, messages):
        is_rtl = any(self.detect_rtl(msg['text']) for msg in messages if msg['text'])
        direction = 'rtl' if is_rtl else 'ltr'
        
        html = f"""<!DOCTYPE html>
<html lang="en" dir="{direction}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{chat_name} - xsukax Backup</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; background: #0d1117; color: #c9d1d9; direction: {direction}; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
.header {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 20px; margin-bottom: 20px; text-align: center; }}
.header h1 {{ color: #58a6ff; }}
.message {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; margin-bottom: 12px; border-left: 4px solid; }}
.message.me {{ background: #1a2332; border-left-color: #238636; }}
.sender {{ font-weight: 600; font-size: 14px; margin-bottom: 4px; }}
.date {{ color: #8b949e; font-size: 11px; margin-bottom: 8px; }}
.text {{ color: #c9d1d9; white-space: pre-wrap; word-wrap: break-word; line-height: 1.5; unicode-bidi: plaintext; }}
.media {{ margin-top: 12px; }}
.media img {{ max-width: 100%; border-radius: 6px; border: 1px solid #30363d; }}
.media a {{ color: #58a6ff; text-decoration: none; display: inline-block; padding: 8px 12px; background: #21262d; border-radius: 6px; }}
.media a:hover {{ background: #30363d; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>{chat_name}</h1>
<p style="color: #8b949e; margin-top: 8px;">xsukax Telegram Backup | {len(messages)} messages</p>
</div>
"""
        
        for msg in messages:
            date_str = msg['date'].strftime('%Y-%m-%d %H:%M:%S')
            user_color = self.get_user_color(msg['sender_id'], msg['sender'])
            me_class = 'me' if msg['is_me'] else ''
            
            media_html = ''
            if msg['media']:
                ext = Path(msg['media']).suffix.lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    media_html = f'<div class="media"><img src="{msg["media"]}" alt="Image"></div>'
                else:
                    media_html = f'<div class="media"><a href="{msg["media"]}">📎 {Path(msg["media"]).name}</a></div>'
            
            text_content = msg['text'].replace('<', '&lt;').replace('>', '&gt;') if msg['text'] else ''
            
            html += f"""
<div class="message {me_class}" style="border-left-color: {user_color};">
<div class="sender" style="color: {user_color};">{msg['sender']}</div>
<div class="date">{date_str}</div>
<div class="text">{text_content}</div>
{media_html}
</div>
"""
        
        html += """
</div>
</body>
</html>"""
        return html

backup_instance = TelegramBackupWeb()
backup_thread = None
backup_completed = False
event_loop = None
loop_thread = None

def start_event_loop():
    global event_loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    event_loop.run_forever()

def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, event_loop).result()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/check_session', methods=['GET'])
def check_session():
    try:
        is_valid, user_info = run_async(backup_instance.connect_existing_session())
        
        if is_valid:
            return jsonify({"success": True, "user": user_info})
        else:
            return jsonify({"success": False})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/send_code', methods=['POST'])
def send_code():
    try:
        data = request.json
        api_id = data['api_id']
        api_hash = data['api_hash']
        phone = data['phone']
        
        run_async(backup_instance.connect(api_id, api_hash, phone))
        run_async(backup_instance.send_code())
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/verify_code', methods=['POST'])
def verify_code():
    try:
        data = request.json
        code = data['otp_code']
        
        success, needs_password = run_async(backup_instance.sign_in(code))
        
        if success:
            return jsonify({"success": True})
        elif needs_password:
            return jsonify({"success": False, "needs_password": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/verify_2fa', methods=['POST'])
def verify_2fa():
    try:
        data = request.json
        password = data['password']
        
        run_async(backup_instance.sign_in_password(password))
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/backup', methods=['POST'])
def start_backup():
    global backup_thread, backup_completed
    
    try:
        data = request.json
        backup_type = data['type']
        filters = data.get('filters', {})
        
        backup_completed = False
        backup_instance.downloaded_files = 0
        
        def run_backup():
            try:
                if backup_type == 'contacts_html':
                    run_async(backup_instance.backup_contacts_html())
                elif backup_type == 'contacts_vcf':
                    run_async(backup_instance.backup_contacts_vcf())
                elif backup_type == 'chats':
                    run_async(backup_instance.backup_chats(filters=filters))
            except Exception as e:
                log_queue.put({"message": f"Error: {str(e)}", "type": "error"})
            finally:
                global backup_completed
                backup_completed = True
        
        backup_thread = threading.Thread(target=run_backup)
        backup_thread.start()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/progress', methods=['GET'])
def get_progress():
    logs = []
    while not log_queue.empty():
        logs.append(log_queue.get())
    
    progress = 0
    if not progress_queue.empty():
        progress = progress_queue.get()
    
    return jsonify({
        "logs": logs,
        "progress": progress,
        "completed": backup_completed
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 xsukax Telegram Backup WebUI")
    print("=" * 60)
    print("Server starting on http://localhost:5000")
    print("Open your browser and navigate to http://localhost:5000")
    print("=" * 60)
    
    loop_thread = threading.Thread(target=start_event_loop, daemon=True)
    loop_thread.start()
    time.sleep(0.5)
    
    app.run(debug=False, host='0.0.0.0', port=5000)