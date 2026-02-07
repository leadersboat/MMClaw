import json
from pathlib import Path

class ConfigManager:
    # We force the model to speak ONLY in JSON. 
    # This is universal for both API and CLI tools.
    SYSTEM_PROMPT = (
        "You are PipClaw, an autonomous AI agent. "
        "You MUST always respond with a SINGLE valid JSON object. "
        "Do not include any text outside the JSON block.\n\n"
        "IMPORTANT: When you use 'tools', you MUST STOP your response immediately after the JSON block. "
        "Do not simulate the tool output. Wait for the system to provide the result.\n\n"
        "Structure:\n"
        "{\n"
        "  \"thought\": \"your reasoning\",\n"
        "  \"tools\": [\n"
        "    {\"name\": \"tool_name\", \"args\": {\"arg1\": \"val1\"}}\n"
        "  ],\n"
        "  \"content\": \"message to user\"\n"
        "}\n\n"
        "Available Tools:\n"
        "- shell_execute(command)\n"
        "- file_read(path)\n"
        "- file_write(path, content)\n"
        "- file_upload(path)"
    )

    DEFAULT_CONFIG = {
        "engine_type": "deepseek",
        "model": "deepseek-chat",
        "api_key": "sk-your-key-here",
        "base_url": "https://api.deepseek.com",
        "telegram_token": "your-bot-token-here",
        "authorized_user_id": 0,
        "whatsapp_token": "your-whatsapp-token-here",
        "whatsapp_phone_number_id": "your-phone-id-here",
        "whatsapp_verify_token": "your-verify-token-here",
        "whatsapp_web_session": "~/.pipclaw/wa_session",
        "preferred_mode": "terminal"
    }
    CONFIG_DIR = Path.home() / ".pipclaw"
    CONFIG_FILE = CONFIG_DIR / "pipclaw.json"

    @classmethod
    def load(cls):
        if not cls.CONFIG_DIR.exists():
            cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        return json.load(open(cls.CONFIG_FILE, "r", encoding="utf-8")) if cls.CONFIG_FILE.exists() else None

    @classmethod
    def save(cls, config):
        config.pop("system_prompt", None)
        with open(cls.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        print(f"[*] Config saved to {cls.CONFIG_FILE}")
