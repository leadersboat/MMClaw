import os
import argparse
import urllib.request
import urllib.parse
import json
import base64
import time
from .config import ConfigManager
from .kernel import MMClaw
from .connectors import TelegramConnector, TerminalConnector, WhatsAppConnector, FeishuConnector

def run_setup(existing_config=None):
    
    need_auth = False
    
    print("\n--- 🐈 MMClaw Setup Wizard ---")
    config = existing_config.copy() if existing_config else ConfigManager.DEFAULT_CONFIG.copy()
    
    # Ensure nested dicts exist
    if "engines" not in config:
        config["engines"] = ConfigManager.DEFAULT_CONFIG["engines"].copy()
    if "connectors" not in config:
        config["connectors"] = ConfigManager.DEFAULT_CONFIG["connectors"].copy()

    def ask(prompt, key, default_val, nested_engine=None, nested_connector=None):
        if nested_engine:
            current = config["engines"][nested_engine].get(key, default_val)
        elif nested_connector:
            current = config["connectors"][nested_connector].get(key, default_val)
        else:
            current = config.get(key, default_val)
            
        if existing_config:
            user_input = input(f"{prompt} [{current}]: ").strip()
            return user_input if user_input else current
        else:
            user_input = input(f"{prompt}: ").strip()
            return user_input if user_input else default_val

    # 1. LLM Configuration
    if not existing_config or input("\n[1/3] Configure LLM Engine? (y/N): ").strip().lower() == 'y':
        print("\n[1/3] LLM Engine Setup")
        
        PROVIDERS = [
            {"id": "openai", "name": "OpenAI", "url": "https://api.openai.com/v1", "models": ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini"]},
            {"id": "codex", "name": "OpenAI Codex (OAuth)", "url": "https://api.openai.com/v1", "models": ["gpt-5.3-codex", "gpt-5.3-codex-spark", "gpt-5.2-codex", "gpt-5.2", "gpt-5.1-codex-max", "gpt-5.1", "gpt-5.1-codex", "gpt-5-codex", "gpt-5-codex-mini", "gpt-5"]},
            {"id": "google", "name": "Google Gemini", "url": "https://generativelanguage.googleapis.com/v1beta/openai", "models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"]},
            {"id": "deepseek", "name": "DeepSeek", "url": "https://api.deepseek.com", "models": ["deepseek-chat", "deepseek-reasoner"]},
            {"id": "openrouter", "name": "OpenRouter", "url": "https://openrouter.ai/api/v1", "models": ["anthropic/claude-3.5-sonnet", "google/gemini-flash-1.5"]},
            {"id": "kimi", "name": "Kimi (Moonshot AI)", "url": "https://api.moonshot.cn/v1", "models": ["kimi-k2.5"]},
            {"id": "openai_compatible", "name": "OpenAI-Compatible SDK (Custom URL)", "url": None, "models": []}
        ]

        print("Select Provider:")
        for i, p in enumerate(PROVIDERS, 1):
            print(f"{i}. {p['name']}")
        
        current_engine_id = config.get("engine_type", "openai")
        current_idx = 1
        for i, p in enumerate(PROVIDERS, 1):
            if p["id"] == current_engine_id:
                current_idx = i
                break

        p_choice = input(f"Choice (1-{len(PROVIDERS)}) [Current: {current_idx}]: ").strip()
        idx = int(p_choice) - 1 if p_choice.isdigit() and 1 <= int(p_choice) <= len(PROVIDERS) else (current_idx - 1)
        provider = PROVIDERS[idx]
        engine_id = provider["id"]
        config["engine_type"] = engine_id
        
        if engine_id not in config["engines"]:
            config["engines"][engine_id] = {}

        if engine_id == "codex":
            CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
            BASE_URL  = "https://auth.openai.com/api/accounts"
            UA_HEADER = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            
            do_oauth = True
            if config["engines"].get("codex", {}).get("api_key"):
                if input("Existing Codex session found. Reuse it? (Y/n): ").strip().lower() != 'n':
                    do_oauth = False
                    print("[✓] Reusing existing session.")

            if do_oauth:
                print(f"[*] Requesting device code...")
                try:
                    data = json.dumps({"client_id": CLIENT_ID}).encode()
                    req = urllib.request.Request(f"{BASE_URL}/deviceauth/usercode", data=data, headers={**UA_HEADER, "Content-Type": "application/json"}, method="POST")
                    with urllib.request.urlopen(req) as resp:
                        res_data = json.loads(resp.read().decode())
                except Exception as e:
                    print(f"[❌] Device code request failed: {e}")
                    return config, False

                device_auth_id = res_data["device_auth_id"]
                user_code      = res_data["user_code"]
                interval       = int(res_data.get("interval", 5))

                print("\n--- 🔐 OpenAI Codex (Device Code) Remote Setup ---")
                print("[*] Finish signing in via your browser")
                print("[*] 1. Open this link in your browser and sign in:")
                print(f"\n    https://auth.openai.com/codex/device\n")
                print("[*] 2. Enter this one-time code after you are signed in:")
                print(f"\n    {user_code}\n")
                print("    ⚠️  Device codes are a common phishing target. Never share this code.")
                print("    (Press Ctrl+C to cancel)\n")

                print("[*] Waiting for authorization...")
                while True:
                    time.sleep(interval)
                    try:
                        data = json.dumps({"device_auth_id": device_auth_id, "user_code": user_code}).encode()
                        req = urllib.request.Request(f"{BASE_URL}/deviceauth/token", data=data, headers={**UA_HEADER, "Content-Type": "application/json"}, method="POST")
                        
                        try:
                            with urllib.request.urlopen(req) as resp:
                                login_data = json.loads(resp.read().decode())
                        except urllib.error.HTTPError as e:
                            if e.code in [403, 404]: continue
                            raise

                        print("\n[*] Authorization received! Exchanging for access token...")
                        exchange_data = urllib.parse.urlencode({
                            "grant_type":    "authorization_code",
                            "client_id":     CLIENT_ID,
                            "code":          login_data["authorization_code"],
                            "code_verifier": login_data["code_verifier"],
                            "redirect_uri":  "https://auth.openai.com/deviceauth/callback",
                        }).encode()
                        
                        req = urllib.request.Request("https://auth.openai.com/oauth/token", data=exchange_data, headers={**UA_HEADER, "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
                        with urllib.request.urlopen(req) as resp:
                            token_data = json.loads(resp.read().decode())

                        config["engines"][engine_id]["api_key"] = token_data["access_token"]
                        if "refresh_token" in token_data:
                            config["engines"][engine_id]["refresh_token"] = token_data["refresh_token"]
                        
                        if "id_token" in token_data:
                            try:
                                payload_b64 = token_data["id_token"].split('.')[1]
                                payload_b64 += '=' * (-len(payload_b64) % 4)
                                payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
                                account_id = payload.get("https://api.openai.com/auth", {}).get("chatgpt_account_id")
                                if account_id:
                                    config["engines"][engine_id]["account_id"] = account_id
                                    print(f"[*] Account ID linked: {account_id}")
                            except: pass
                        
                        print("\n[✓] OAuth Login Successful!")
                        break
                    except KeyboardInterrupt: return config, False
                    except Exception as e:
                        print(f"\n[❌] Setup failed: {e}")
                        return config, False

            config["engines"][engine_id]["base_url"] = provider["url"]
        else:
            if provider["url"]:
                config["engines"][engine_id]["base_url"] = provider["url"]
                print(f"[*] Base URL set to: {config['engines'][engine_id]['base_url']}")
            else:
                config["engines"][engine_id]["base_url"] = ask("Enter Base URL", "base_url", "http://localhost:11434/v1", nested_engine=engine_id)

            config["engines"][engine_id]["api_key"] = ask(f"Enter {provider['name']} API Key", "api_key", "sk-xxx", nested_engine=engine_id)

        # Dynamic Model Fetching
        engine_config = config["engines"][engine_id]
        models = provider["models"]
        if engine_id != "codex" and engine_config["api_key"] and engine_config["api_key"] != "sk-xxx":
            print(f"[*] Fetching live models from {provider['name']}...")
            try:
                req = urllib.request.Request(
                    f"{engine_config['base_url']}/models", 
                    headers={"Authorization": f"Bearer {engine_config['api_key']}"}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    fetched = [m["id"] for m in data.get("data", [])]
                    if fetched:
                        if "openai.com" in engine_config["base_url"]:
                            fetched = [m for m in fetched if m.startswith(("gpt-", "o1-"))]
                        
                        models = list(set(fetched + models))
                        FEATURED = ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "deepseek-chat", "deepseek-reasoner", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp", "kimi-k2.5"]
                        def sort_key(name):
                            try: return (FEATURED.index(name), name)
                            except ValueError: return (len(FEATURED), name)
                        models.sort(key=sort_key)
                        print(f"[✓] Successfully fetched {len(fetched)} models.")
            except:
                print("[!] Could not fetch live models, using default list.")

        if models:
            print(f"\nSelect {provider['name']} Model:")
            for i, m in enumerate(models, 1):
                print(f"{i}. {m}")
            print(f"{len(models)+1}. Enter Manually")
            
            current_model = engine_config.get('model', models[0])
            m_choice = input(f"Choice (1-{len(models)+1}) [Current: {current_model}]: ").strip()
            
            if m_choice.isdigit():
                idx_m = int(m_choice)
                if 1 <= idx_m <= len(models): engine_config["model"] = models[idx_m-1]
                elif idx_m == len(models) + 1: engine_config["model"] = input("Enter Model Name manually: ").strip()
            elif not m_choice and existing_config: pass
            else: engine_config["model"] = models[0]
        else:
            engine_config["model"] = ask("Enter Model Name", "model", "llama3", nested_engine=engine_id)

    # 2. Mode Selection
    if not existing_config or input("\n[2/3] Configure Connector (Interaction Mode)? (y/N): ").strip().lower() == 'y':
        print("\n[2/3] Interaction Mode")
        print("1. Terminal Mode\n2. Telegram Mode\n3. WhatsApp Mode\n4. Feishu (飞书) Mode")
        choice = input(f"Select mode [Current: {config.get('connector_type', 'terminal')}]: ").strip()

        if choice == "4":
            config["connector_type"] = "feishu"
            config["connectors"]["feishu"]["app_id"] = ask("App ID", "app_id", "", nested_connector="feishu")
            config["connectors"]["feishu"]["app_secret"] = ask("App Secret", "app_secret", "", nested_connector="feishu")
            if not config["connectors"]["feishu"].get("authorized_id"): need_auth = True
        elif choice == "2":
            config["connector_type"] = "telegram"
            config["connectors"]["telegram"]["token"] = ask("Bot API Token", "token", "", nested_connector="telegram")
            user_id = ask("Your User ID", "authorized_user_id", "0", nested_connector="telegram")
            config["connectors"]["telegram"]["authorized_user_id"] = int(user_id) if str(user_id).isdigit() else 0
        elif choice == "3":
            config["connector_type"] = "whatsapp"
            if not os.path.exists(os.path.join(os.path.expanduser("~"), ".mmclaw", "wa_auth")):
                need_auth = True
        elif choice == "1":
            config["connector_type"] = "terminal"

    ConfigManager.save(config)
    return config, need_auth

def main():
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)

    parser = argparse.ArgumentParser(description="MMClaw: Your autonomous multimodal AI agent.")
    parser.add_argument("command", nargs="?", help="Command to run (run, config)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    config = ConfigManager.load()
    if args.command == "config":
        config, need_auth = run_setup(config)
        if not need_auth: return
    elif args.command not in [None, "run"]:
        parser.print_help()
        return

    if not config: config, _ = run_setup()
    config["debug"] = args.debug

    mode = config.get("connector_type")
    connectors_config = config.get("connectors", {})
    if mode == "telegram":
        tg = connectors_config.get("telegram", {})
        connector = TelegramConnector(tg.get("token"), tg.get("authorized_user_id", 0))
    elif mode == "whatsapp": connector = WhatsAppConnector(config=config)
    elif mode == "feishu":
        fs = connectors_config.get("feishu", {})
        connector = FeishuConnector(fs.get("app_id"), fs.get("app_secret"), config=config)
    else: connector = TerminalConnector()

    engine_type = config.get("engine_type", "openai")
    active_engine = config.get("engines", {}).get(engine_type, {})
    if not active_engine.get("api_key") or "your-key-here" in active_engine.get("api_key", ""):
        print(f"\n[❌] API Key missing for {engine_type}. Run 'mmclaw config'.")
        return
    
    app = MMClaw(config, connector, system_prompt=ConfigManager.get_full_prompt(mode=mode))
    app.run(stop_on_auth=(args.command == "config"))

if __name__ == "__main__":
    main()
