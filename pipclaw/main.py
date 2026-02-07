import os
from .config import ConfigManager
from .kernel import PipClaw
from .connectors import TelegramConnector, TerminalConnector, WhatsAppConnector, WhatsAppWebConnector

def setup_wizard():
    print("\n--- 🐈 PipClaw Setup Wizard ---")
    config = ConfigManager.DEFAULT_CONFIG.copy()

    # 1. LLM Configuration
    print("\n[1/3] LLM Engine Setup")
    api_key = input("Enter your OpenAI/DeepSeek API Key: ").strip()
    if api_key:
        config["api_key"] = api_key
    
    base_url = input("Enter Base URL (default: https://api.deepseek.com): ").strip()
    if base_url:
        config["base_url"] = base_url

    # 2. Mode Selection
    print("\n[2/3] Interaction Mode")
    print("1. Terminal Mode")
    print("2. Telegram Mode")
    print("3. WhatsApp Cloud API (Requires Meta Dev Account)")
    print("4. WhatsApp Web (Requires QR Scan + Playwright)")
    choice = input("Select mode (1, 2, 3, or 4): ").strip()

    if choice == "2":
        config["preferred_mode"] = "telegram"
        print("\n--- 🛠 Telegram Setup ---")
        config["telegram_token"] = input("Bot API Token: ").strip()
        user_id = input("Your User ID: ").strip()
        config["authorized_user_id"] = int(user_id) if user_id.isdigit() else 0
    elif choice == "3":
        config["preferred_mode"] = "whatsapp"
        print("\n--- 🛠 WhatsApp Cloud Setup ---")
        config["whatsapp_token"] = input("Permanent Access Token: ").strip()
        config["whatsapp_phone_number_id"] = input("Phone Number ID: ").strip()
        config["whatsapp_verify_token"] = input("Webhook Verify Token: ").strip()
    elif choice == "4":
        config["preferred_mode"] = "whatsapp_web"
        print("\n--- 🛠 WhatsApp Web Setup ---")
        print("[*] No tokens needed. You will scan a QR code on first run.")
    else:
        config["preferred_mode"] = "terminal"

    # 3. Save
    ConfigManager.save(config)
    return config

def main():
    config = ConfigManager.load()
    
    if not config:
        config = setup_wizard()

    # Mode Dispatch
    mode = config.get("preferred_mode")
    if mode == "telegram":
        connector = TelegramConnector(config["telegram_token"], config["authorized_user_id"])
    elif mode == "whatsapp":
        connector = WhatsAppConnector(
            config["whatsapp_token"], 
            config["whatsapp_phone_number_id"], 
            config["whatsapp_verify_token"]
        )
    elif mode == "whatsapp_web":
        connector = WhatsAppWebConnector(config.get("whatsapp_web_session"))
    else:
        connector = TerminalConnector()

    if config["api_key"] == "sk-your-key-here":
        print(f"\n[❌] API Key missing. Please run again or edit {ConfigManager.CONFIG_FILE}")
        return
    
    app = PipClaw(config, connector, system_prompt=ConfigManager.SYSTEM_PROMPT)
    app.run()

if __name__ == "__main__":
    main()
