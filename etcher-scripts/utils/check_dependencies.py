"""
Dependency Checker
=================

Verifies the presence of required system tools and Python modules.
Provides OS-specific installation instructions if dependencies are missing.
"""

import shutil
import sys
import platform
import importlib.util
import argparse
import subprocess
import re

# Defined centralized dependencies here
REQUIRED_TOOLS = ["curl", "dd"]
REQUIRED_MODULES = ["yaml"]
# Note: OS specific tools are added in verify_dependencies

def check_command(cmd):
    """Check if a command-line tool exists in PATH."""
    return shutil.which(cmd) is not None

def check_python_module(module_name):
    """Check if a python module is installed."""
    return importlib.util.find_spec(module_name) is not None

def get_install_command_linux(missing_tools, missing_modules):
    """Generate install commands for Linux (Debian/Ubuntu based)."""
    cmds = []
    
    # Simple heuristic: assume apt for now
    pkgs = list(missing_tools)
    
    # Map common tools to package names if needed
    # e.g. python3 is usually python3, curl is curl
    
    # Python modules
    # In many distros, python packages are named python3-<pypi_name>
    # or one might prefer pip. Let's suggest apt where possible, then pip.
    
    pip_pkgs = []
    
    for mod in missing_modules:
        if mod == "yaml": 
            # try to suggest system package first
            pkgs.append("python3-yaml")
        else:
            # default to pip if we don't know the system package
            pip_pkgs.append(mod)
            
    if pkgs:
        cmds.append(f"sudo apt update && sudo apt install -y {' '.join(pkgs)}")
        
    if pip_pkgs:
        cmds.append(f"pip3 install {' '.join(pip_pkgs)} --break-system-packages")

    if not cmds:
        return "# Could not determine install commands automatically."
        
    return " && ".join(cmds)

def get_install_command_macos(missing_tools, missing_modules):
    """Generate install commands for macOS (using brew)."""
    cmds = []
    if missing_tools:
        cmds.append(f"brew install {' '.join(missing_tools)}")
    if missing_modules:
        cmds.append(f"pip3 install {' '.join(missing_modules)}")
    return " && ".join(cmds)

def get_install_command(os_name, missing_tools, missing_modules):
    """Dispatch to OS-specific install command generators."""
    if os_name == "Darwin": # macOS
        return get_install_command_macos(missing_tools, missing_modules)
    elif os_name == "Linux":
         return get_install_command_linux(missing_tools, missing_modules)
    else:
        return f"# Manual installation required for OS: {os_name}"

def verify_dependencies(extra_tools=None, extra_modules=None):
    """
    Checks dependencies and prints instructions if missing. 
    Returns True if all met.
    
    Args:
        extra_tools (list, optional): Additional system tools to check.
        extra_modules (list, optional): Additional python modules to check.
    """
    if extra_tools is None: extra_tools = []
    if extra_modules is None: extra_modules = []

    # 1. Merge hardcoded requirements with extras
    tools_to_check = REQUIRED_TOOLS + extra_tools
    modules_to_check = REQUIRED_MODULES + extra_modules
    
    # 2. Add OS specific requirements
    if platform.system() == "Darwin":
        tools_to_check.append("diskutil")
    elif platform.system() == "Linux":
        tools_to_check.append("lsblk")

    missing_tools = []
    missing_modules = []

    # 3. Check System Tools
    for tool in tools_to_check:
        if not check_command(tool):
            missing_tools.append(tool)

    # 4. Check Python Modules
    for mod in modules_to_check:
        if not check_python_module(mod):
            missing_modules.append(mod)

    # 5. Report results
    if not missing_tools and not missing_modules:
        print("Success: All dependencies met.")
        return True

    print("ERROR: Missing dependencies found!")
    
    os_name = platform.system()
    install_cmd = get_install_command(os_name, missing_tools, missing_modules)

    if missing_tools:
        print(f"Missing System Tools: {', '.join(missing_tools)}")
    if missing_modules:
        print(f"Missing Python Modules: {', '.join(missing_modules)}")

    print("\nTo fix this, try running:\n")
    print(f"  {install_cmd}\n")
    
    return False

def main():
    parser = argparse.ArgumentParser(description="Check for required dependencies.")
    parser.add_argument("--tools", nargs="*", default=[], help="Additional system commands to check")
    parser.add_argument("--modules", nargs="*", default=[], help="Additional python modules to check")
    
    args = parser.parse_args()
    
    if not verify_dependencies(args.tools, args.modules):
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
