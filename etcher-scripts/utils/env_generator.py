"""
Environment Config Generator
===========================

Transforms the structured YAML configuration into a flat key=value .env format
suitable for sourcing in shell scripts during installation.
"""

import yaml
import textwrap

def generate_env_content(config_path):
    """
    Reads config.yml and returns the .env file content as a string.
    
    Args:
        config_path (str): Path to the source YAML config file.
        
    Returns:
        str: The generated content for the .env file.
        
    Raises:
        Exception: If reading or parsing fails.
    """
    try:
        # 1. Load YAML structure
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        system = config.get("system", {})
        network = system.get("network", {})
        
        # 2. Map to flat ENV variables
        env_content = textwrap.dedent(f"""
            ROOT_PASSWORD={system.get("root_password", "")}
            TIMEZONE={system.get("timezone", "UTC")}
            LOCALE={system.get("locale", "en_US.UTF-8")}
            KEYMAP={system.get("keyboard_layout", "us")}
            PREFER_WIFI_CONNECTION={str(network.get("prefer_wifi", False)).lower()}
            WIFI_SSID={network.get("wifi_ssid", "")}
            WIFI_PASSWORD={network.get("wifi_password", "")}
        """)
        return env_content.strip()
        
    except Exception as e:
        raise Exception(f"Error generating .env content: {e}")
