import time
import subprocess
import urllib.request

proc = subprocess.Popen(["python", "app.py"])
try:
    time.sleep(3)
    with urllib.request.urlopen("http://127.0.0.1:8050/", timeout=5) as response:
        status = response.status
        content_type = response.headers.get_content_type()
        data = response.read()
        print(f"HTTP Status: {status}")
        print(f"Content-Type: {content_type}")
        print(f"Data length: {len(data)} bytes")
        assert status == 200
        assert b"NewsPulse" in data
        print("Live server test PASSED successfully!")
finally:
    proc.terminate()
    proc.wait()
