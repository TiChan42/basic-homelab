"""
ISO Download Manager
===================

Handles the retrieval of Proxmox VE ISO images.
Includes functionality to scrape the official website for the latest version
and download large files with a progress indicator.
"""

import os
import sys
import urllib.request
import urllib.error
import re

PROXMOX_DOWNLOAD_PAGE = "https://www.proxmox.com/en/downloads/proxmox-virtual-environment/iso"

def get_latest_iso_url():
    """
    Scrapes the Proxmox website for the latest ISO download link.
    
    Returns:
        str: The direct download URL for the latest ISO.
    """
    print("Fetching latest Proxmox VE ISO download link...")
    try:
        # 1. Setup request headers to mimic a browser
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(PROXMOX_DOWNLOAD_PAGE, headers=headers)
        
        # 2. Fetch page content
        with urllib.request.urlopen(req) as response:
            page_content = response.read().decode('utf-8')
            
        # 3. Search for ISO link pattern
        match = re.search(r'https://enterprise\.proxmox\.com/iso/[^"]*\.iso', page_content)
        if match:
            return match.group(0)
            
    except Exception as e:
        print(f"Warning: Could not scrape Proxmox site: {e}")
    
    # 4. Fallback to manual input
    return input("Could not determine URL automatically. Please enter URL manually: ").strip()

def _progress_hook(count, block_size, total_size):
    """Callback for urllib.urlretrieve to show download progress."""
    percent = int(count * block_size * 100 / total_size)
    sys.stdout.write(f"\rDownloading... {percent}%")
    sys.stdout.flush()

def download_file(url, destination):
    """
    Downloads a file from a URL to a local destination with a progress bar.

    Args:
        url (str): The source URL.
        destination (str): The local file path.
    """
    # 1. Check if file already exists
    if os.path.exists(destination):
        print(f"File {destination} already exists.")
        if input("Re-download? [y/N]: ").lower() != 'y':
            return

    print(f"Downloading {url}...")
    try:
        # 2. Perform download with progress hook
        urllib.request.urlretrieve(url, destination, reporthook=_progress_hook)
        print("\nDownload complete.")
        
    except Exception as e:
        print(f"\nError downloading file: {e}")
        sys.exit(1)
