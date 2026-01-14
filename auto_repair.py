
import os, subprocess, time

print("🔧 Applying auto-repair command suggested by Gemini...")
subprocess.run(r"mysqladmin -u oot -p passwod 'new_passwod", shell=True)
print("⏳ Waiting 3 seconds before rechecking connection...")
time.sleep(3)
os.system("python app3.py")
