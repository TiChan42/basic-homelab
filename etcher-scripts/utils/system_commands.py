"""
System Command Utilities
=======================

This module provides wrapper functions for executing system commands
via subprocess, handling stdout/stderr capture and error reporting consistently.
"""

import subprocess
import sys

def run_command(cmd, shell=False, check=True, capture_output=True):
    """
    Executes a shell command using subprocess.run.

    Args:
        cmd (list or str): The command to run. List of strings (recommended) or string.
        shell (bool, optional): Whether to use the shell. Defaults to False.
        check (bool, optional): Whether to raise an exception on non-zero exit. Defaults to True.
        capture_output (bool, optional): Whether to capture and return stdout. Defaults to True.

    Returns:
        str: The standard output of the command (stripped) if capture_output is True, else empty string.

    Raises:
        subprocess.CalledProcessError: If the command fails and check is True.
    """
    try:
        # 1. Execute the command
        result = subprocess.run(
            cmd, 
            shell=shell, 
            check=check, 
            stdout=subprocess.PIPE if capture_output else None, 
            stderr=subprocess.PIPE if capture_output else None,
            text=True
        )
        # 2. Return stdout if captured
        return result.stdout.strip() if capture_output else ""
        
    except subprocess.CalledProcessError as e:
        # 3. Handle errors
        print(f"Error running command: {e}")
        if capture_output and e.stderr:
            print(f"Stderr: {e.stderr}")
        raise
