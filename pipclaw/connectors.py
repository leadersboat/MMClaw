import telebot
import os
import json
import urllib.request
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

class TerminalConnector:
    def listen(self, callback):
        print("\n--- PipClaw Kernel Active (Terminal Mode) ---")
        while True:
            try:
                text = input("👤 You: ").strip()
                if text.lower() in ["exit", "quit"]: break
                if text: callback(text) 
            except KeyboardInterrupt: break

    def send(self, message):
        print(f"\r🐈 PipClaw: {message}\n👤 You: ", end="", flush=True)

    def send_file(self, path):
        # Expand ~ to home directory if present
        full_path = os.path.expanduser(path)
        print(f"\r🐈 PipClaw: [FILE SENT] {os.path.abspath(full_path)}\n👤 You: ", end="", flush=True)

class TelegramConnector:
    def __init__(self, token, authorized_user_id):
        self.bot = telebot.TeleBot(token)
        self.authorized_user_id = int(authorized_user_id)
        
    def listen(self, callback):
        print(f"\n--- PipClaw Kernel Active (Telegram Mode) ---")
        print(f"[*] Listening for messages from User ID: {self.authorized_user_id}")
        
        @self.bot.message_handler(func=lambda message: message.from_user.id == self.authorized_user_id)
        def handle_message(message):
            callback(message.text)
            
        @self.bot.message_handler(func=lambda message: message.from_user.id != self.authorized_user_id)
        def unauthorized(message):
            self.bot.reply_to(message, "🚫 Unauthorized. I only respond to my master.")

        self.bot.infinity_polling()

    def send(self, message):
        try:
            self.bot.send_message(self.authorized_user_id, f"🐈 {message}")
        except Exception as e:
            print(f"[!] Telegram Send Error: {e}")

    def send_file(self, path):
        # Expand ~ to home directory if present
        path = os.path.expanduser(path)
        try:
            with open(path, 'rb') as f:
                self.bot.send_document(self.authorized_user_id, f)
        except Exception as e:
            self.send(f"Error sending file: {str(e)}")

class WhatsAppConnector:
    """
    WhatsApp Cloud API Connector (Zero-Dependency)
    """
    def __init__(self, token, phone_number_id, verify_token, port=8080):
        self.token = token
        self.phone_number_id = phone_number_id
        self.verify_token = verify_token
        self.port = port
        self.callback = None
        self.active_recipient = None

    def listen(self, callback):
        self.callback = callback
        connector = self

        class WhatsAppWebhookHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(self.path).query)
                hub_mode = query.get('hub.mode', [''])[0]
                hub_token = query.get('hub.verify_token', [''])[0]
                hub_challenge = query.get('hub.challenge', [''])[0]

                if hub_mode == 'subscribe' and hub_token == connector.verify_token:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(hub_challenge.encode())
                else:
                    self.send_response(403)
                    self.end_headers()

            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                try:
                    payload = json.loads(post_data.decode('utf-8'))
                    entry = payload.get('entry', [{}])[0]
                    changes = entry.get('changes', [{}])[0].get('value', {})
                    if 'messages' in changes:
                        msg = changes['messages'][0]
                        sender_id = msg['from']
                        text = msg.get('text', {}).get('body', '')
                        connector.active_recipient = sender_id
                        if connector.callback and text:
                            connector.callback(text)
                except Exception as e:
                    print(f"[!] WhatsApp Webhook Parse Error: {e}")
                self.send_response(200)
                self.end_headers()

            def log_message(self, format, *args): return

        self.server = HTTPServer(('', self.port), WhatsAppWebhookHandler)
        print(f"\n--- PipClaw Kernel Active (WhatsApp Cloud Mode) ---")
        print(f"[*] Webhook listening on port {self.port}")
        
        server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        server_thread.start()
        server_thread.join()

    def send(self, message):
        if not self.active_recipient:
            print("[!] WhatsApp Error: No active recipient ID found.")
            return

        url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "to": self.active_recipient,
            "type": "text",
            "text": {"body": message}
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print(f"[!] WhatsApp Send Error: {e}")

    def send_file(self, path):
        path = os.path.expanduser(path)
        self.send(f"📦 [File Attachment]: {os.path.abspath(path)}")

class WhatsAppWebConnector:
    """
    WhatsApp Web Connector (Optional Dependency: playwright)
    Requires: pip install playwright && playwright install chromium
    """
    def __init__(self, session_dir=".pipclaw/wa_session"):
        self.session_dir = os.path.expanduser(session_dir)
        self.page = None
        self.callback = None

    def listen(self, callback):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("\n[!] WhatsApp Web requires 'playwright'.")
            print("[*] Please run: pip install playwright && playwright install chromium")
            return

        self.callback = callback
        print(f"\n--- PipClaw Kernel Active (WhatsApp Web Mode) ---")
        print(f"[*] Session stored in: {self.session_dir}")
        print("[*] Please scan the QR code if prompted.")
        
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=False
            )
            self.page = browser.pages[0]
            self.page.goto("https://web.whatsapp.com")
            
            last_msg_id = None
            while True:
                try:
                    messages = self.page.query_selector_all("div.message-in")
                    if messages:
                        last_msg = messages[-1]
                        text_element = last_msg.query_selector("span.selectable-text")
                        if text_element:
                            text = text_element.inner_text()
                            msg_id = last_msg.get_attribute("data-id")
                            if msg_id != last_msg_id:
                                last_msg_id = msg_id
                                if self.callback:
                                    self.callback(text)
                except Exception: pass
                time.sleep(2)

    def send(self, message):
        if not self.page: return
        try:
            input_selector = "div[contenteditable='true'][data-tab='10']"
            self.page.fill(input_selector, message)
            self.page.press(input_selector, "Enter")
        except Exception as e:
            print(f"[!] WhatsApp Web Send Error: {e}")

    def send_file(self, path):
        self.send(f"📦 [File Attachment]: {os.path.abspath(os.path.expanduser(path))}")