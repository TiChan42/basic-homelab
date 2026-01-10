#!/usr/bin/env python3
import os
import sys
import yaml

# --- CONFIGURATION SCHEMA DEFITION ---
# This tree structure defines all required and optional fields.
CONFIG_SCHEMA = {
    "system": {
        "required": True,
        "type": dict,
        "children": {
            "root_password": {"required": True, "type": str},
            "admin_user": {"required": False, "type": str},
            "admin_password": {"required": False, "type": str},
            "timezone": {"required": False, "type": str},
            "locale": {"required": False, "type": str},
            "keyboard_layout": {"required": False, "type": str},
            "ssh_authorized_keys": {"required": False, "type": list},
            "network": {
                "required": True,
                "type": dict,
                "children": {
                    "hostname": {"required": False, "type": str},
                    "prefer_wifi": {"required": False, "type": bool},
                    "wifi_ssid": {"required": False, "type": str},
                    "wifi_password": {"required": False, "type": str},
                }
            }
        }
    },
    "services": {
        "required": True,
        "type": list,
        "item_schema": {
            # Schema for each item in the list
            "name": {"required": True, "type": str},
            "playbook": {"required": True, "type": str},
            "hostname": {"required": False, "type": str},
            "enabled": {"required": False, "type": bool},
            "allocations": {"required": False, "type": dict},
            "variables": {"required": False, "type": dict},
        }
    },
    "backup": {
        "required": False,
        "type": dict,
        "children": {
             "connections": {"required": False, "type": list}
        }
    }
}

def load_config(config_file):
    if not os.path.exists(config_file):
        return None, [f"Configuration file '{config_file}' not found. Copy 'config.yml.example' to 'config.yml'."]
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f) or {}
            return config, []
    except Exception as e:
        return None, [f"Error reading '{config_file}': {e}"]

def validate_structure(data, schema, parent_path=""):
    """
    Recursively validates data against the schema tree.
    """
    errors = []
    
    if not isinstance(schema, dict):
        return errors
        
    for key, rules in schema.items():
        current_path = f"{parent_path}.{key}" if parent_path else key
        
        # 1. Existence Check
        if key not in data:
            if rules.get("required", False):
                errors.append(f"Missing required key: '{current_path}'")
            continue
            
        value = data[key]
        expected_type = rules.get("type")
        
        # 2. Type Check
        if expected_type and not isinstance(value, expected_type):
            errors.append(f"Invalid type for '{current_path}': Expected {expected_type.__name__}, got {type(value).__name__}")
            continue
            
        # 3. Recurse for Dictionary Children
        if isinstance(value, dict) and "children" in rules:
             errors.extend(validate_structure(value, rules["children"], current_path))
             
        # 4. Iterative Check for List Items
        if isinstance(value, list) and "item_schema" in rules:
            item_schema = rules["item_schema"]
            for idx, item in enumerate(value):
                item_path = f"{current_path}[{idx}]"
                if not isinstance(item, dict):
                    errors.append(f"Item at {item_path} must be a dictionary")
                    continue
                # Validate the item against the item_schema (which behaves like a children dict)
                errors.extend(validate_structure(item, item_schema, item_path))

    return errors

def validate_config(config_file="config.yml"):
    config, load_errors = load_config(config_file)
    
    if load_errors:
        print("\n".join([f"ERROR: {e}" for e in load_errors]))
        return False
        
    # Run recursive validation
    errors = validate_structure(config, CONFIG_SCHEMA)

    if errors:
        print(f"\nVALIDATION FAILED: Found {len(errors)} errors in '{config_file}':")
        for err in errors:
            print(f" - {err}")
        return False

    print(f"SUCCESS: '{config_file}' is valid.")
    return True

if __name__ == "__main__":
    if not validate_config():
        sys.exit(1)
    sys.exit(0)
