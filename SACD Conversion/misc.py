import sys
from pathlib import Path
from datetime import datetime

def log_to_file(message):
    log_file = Path.home() / "Desktop" / "Conversion Log.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp}: {message}\n")

def main():
    if len(sys.argv) != 2:
        print("Invalid number of arguments passed.")
        return

    message = sys.argv[1]
    
    log_to_file(message)