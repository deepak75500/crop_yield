import os
import time
import socket
import subprocess
import pymongo
import mysql.connector
from mysql.connector import Error
import sys
import textwrap

# ------------------------------------------
# 🔹 Configure Gemini
# ------------------------------------------
API_KEY = ""
if not API_KEY:
    raise EnvironmentError("❌ Missing GEMINI_API_KEY. Set it using setx/export before running.")

from google import genai
from google.genai import types

client = genai.Client(api_key=API_KEY)

# ------------------------------------------
# 🔹 Utility Functions
# ------------------------------------------
def run_command(cmd):
    """Run shell/system commands."""
    print(f"⚙ Executing: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(result.stdout or result.stderr)
    except Exception as e:
        print(f"❌ Command failed: {e}")

def check_port(host, port):
    """Check if port is open."""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception:
        return False

import re
def ask_gemini(error_text, db_type):
    """Ask Gemini to diagnose connection problems and suggest a fix command."""
    prompt = f"""
You are a system assistant diagnosing {db_type} connection issues.
Error: {error_text}

Briefly describe what might be wrong and give one Linux or Windows command to fix it.

⚠️ IMPORTANT:
- Use ONLY standard quotes (single ' or double ").
- Do NOT include backticks (`) or Markdown formatting.
- Keep the command shell-safe and valid for subprocess.run.
- Format strictly as:
Issue: <short issue>
Fix Command: <command>
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
        )
        text = response.text.strip()
        cmd=text
        cmd = cmd.replace("`", "").replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    # Trim whitespace
        cmd = cmd.strip()
        # Remove nested quotes like r"`command`"
        cmd = re.sub(r'r"?`?(.+?)`?"?', r"\1", cmd)
        # Ensure no unbalanced quotes
        if cmd.count('"') % 2 != 0:
            cmd = cmd.replace('"', "'")
        print(f"\n🤖 Gemini Suggestion:\n{cmd}\n")
        fix_cmd = None
        for line in cmd.splitlines():
            if line.lower().startswith("fix command"):
                fix_cmd = line.split(":", 1)[-1].strip()
        return fix_cmd
    except Exception as e:
        print(f"⚠ Gemini API error: {e}")
        return None

def regenerate_and_rerun(fix_cmd):
    """Generate a temporary fix script, execute it, then rerun the main script."""
    script_path = "auto_repair.py"
    script_content = textwrap.dedent(f"""
    import os, subprocess, time

    print("🔧 Applying auto-repair command suggested by Gemini...")
    subprocess.run(r"{fix_cmd}", shell=True)
    print("⏳ Waiting 3 seconds before rechecking connection...")
    time.sleep(3)
    os.system("python {os.path.basename(__file__)}")
    """)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    print(f"🧠 Gemini fix saved in {script_path}, executing now...\n")
    subprocess.run(["python", script_path])
    sys.exit(0)

# ------------------------------------------
# 🔹 Database Connections
# ------------------------------------------
def connect_mysql():
    print("🔍 Checking MySQL (port 3306)...")
    if not check_port("localhost", 3306):
        print("⚠ MySQL port closed or not running.")
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="root", database="test")
        if conn.is_connected():
            print("✅ MySQL connected successfully.")
            return conn
    except Error as e:
        print(f"❌ MySQL Error: {e}")
        fix_cmd = ask_gemini(str(e), "MySQL")
        if fix_cmd:
            regenerate_and_rerun(fix_cmd)
    return None

def connect_mongodb():
    print("🔍 Checking MongoDB (port 27017)...")
    if not check_port("localhost", 27017):
        print("⚠ MongoDB port closed or not running.")
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
        client.server_info()
        print("✅ MongoDB connected successfully.")
        return client["testdb"]
    except Exception as e:
        print(f"❌ MongoDB Error: {e}")
        fix_cmd = ask_gemini(str(e), "MongoDB")
        if fix_cmd:
            regenerate_and_rerun(fix_cmd)
    return None

# ------------------------------------------
# 🔹 Auto Detection & Healing
# ------------------------------------------
def auto_connect():
    print("🔍 Detecting which database is running...\n")
    mysql_up = check_port("localhost", 3306)
    mongo_up = check_port("localhost", 27017)

    if mysql_up and mongo_up:
        print("✅ Both MySQL and MongoDB detected. Prioritizing MySQL.\n")
        return connect_mysql() or connect_mongodb()
    elif mysql_up:
        print("✅ MySQL detected.\n")
        return connect_mysql()
    elif mongo_up:
        print("✅ MongoDB detected.\n")
        return connect_mongodb()
    else:
        print("❌ No database detected. Asking Gemini for help...")
        fix_cmd = ask_gemini("Neither MySQL nor MongoDB reachable.", "System")
        if fix_cmd:
            regenerate_and_rerun(fix_cmd)

# ------------------------------------------
# 🔹 Main
# ------------------------------------------
if __name__ == "__main__":
    print("⚙ Starting Gemini-Powered DB Auto-Connector...\n")
    db_conn = auto_connect()
    if db_conn:
        print("🎯 Successfully connected to local database!")
    else:
        print("❌ Could not connect to any database even after retries.")