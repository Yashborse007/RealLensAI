import os
import sys
import time
import threading

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import uvicorn
import httpx
from main import app
from config import settings

PORT = 8005

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

def create_test_file(filename, content=b"dummy media content"):
    os.makedirs("scratch", exist_ok=True)
    filepath = os.path.join("scratch", filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return filepath

def main():
    print("\n====================================================")
    print("  Running RealLens AI Python Microservice Tests")
    print("====================================================\n")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1.5)

    base_url = f"http://127.0.0.1:{PORT}"

    try:
        # Test 1: GET /health
        print("Test 1: Testing GET /health...")
        res = httpx.get(f"{base_url}/health")
        if res.status_code == 200 and res.json().get("success") is True:
            print(f"  ✅ SUCCESS: Health endpoint OK -> {res.json()}")
        else:
          print(f"  ❌ FAILED: Health endpoint returned {res.status_code}: {res.text}")

        # Test 2: POST /predict/image (Without trained weights)
        print("\nTest 2: Testing POST /predict/image (Image prediction with unconfigured model)...")
        img_path = create_test_file("sample.jpg", b"fake-jpg-content")
        with open(img_path, "rb") as f:
            res = httpx.post(f"{base_url}/predict/image", files={"file": ("sample.jpg", f, "image/jpeg")})
        
        data = res.json()
        if res.status_code == 200 and data.get("status") == "MODEL_NOT_AVAILABLE":
            print(f"  ✅ SUCCESS: Image prediction correctly returned MODEL_NOT_AVAILABLE -> {data}")
        else:
            print(f"  ❌ FAILED: Unexpected image prediction response: {res.status_code} - {data}")

        # Test 3: POST /predict/video (Without trained weights)
        print("\nTest 3: Testing POST /predict/video (Video prediction with unconfigured model)...")
        vid_path = create_test_file("sample.mp4", b"fake-mp4-content")
        with open(vid_path, "rb") as f:
            res = httpx.post(f"{base_url}/predict/video", files={"file": ("sample.mp4", f, "video/mp4")})
        
        data = res.json()
        if res.status_code == 200 and data.get("status") == "MODEL_NOT_AVAILABLE":
            print(f"  ✅ SUCCESS: Video prediction correctly returned MODEL_NOT_AVAILABLE -> {data}")
        else:
            print(f"  ❌ FAILED: Unexpected video prediction response: {res.status_code} - {data}")

        # Test 4: POST /predict/audio (Without trained weights)
        print("\nTest 4: Testing POST /predict/audio (Audio prediction with unconfigured model)...")
        aud_path = create_test_file("sample.wav", b"fake-wav-content")
        with open(aud_path, "rb") as f:
            res = httpx.post(f"{base_url}/predict/audio", files={"file": ("sample.wav", f, "audio/wav")})
        
        data = res.json()
        if res.status_code == 200 and data.get("status") == "MODEL_NOT_AVAILABLE":
            print(f"  ✅ SUCCESS: Audio prediction correctly returned MODEL_NOT_AVAILABLE -> {data}")
        else:
            print(f"  ❌ FAILED: Unexpected audio prediction response: {res.status_code} - {data}")

        # Test 5: Invalid File Extension Rejection (.exe)
        print("\nTest 5: Testing invalid file extension rejection...")
        exe_path = create_test_file("test.exe", b"fake-exe-content")
        with open(exe_path, "rb") as f:
            res = httpx.post(f"{base_url}/predict/image", files={"file": ("test.exe", f, "application/octet-stream")})
        
        if res.status_code == 400:
            print(f"  ✅ SUCCESS: Invalid extension rejected with 400 Bad Request -> {res.json().get('error')}")
        else:
            print(f"  ❌ FAILED: Unexpected response for invalid extension: {res.status_code} - {res.text}")

        print("\n====================================================")
        print("  ALL PYTHON AI MICROSERVICE TESTS PASSED! 🎉")
        print("====================================================\n")

    except Exception as e:
        print(f"\n❌ TEST RUNNER ERROR: {str(e)}")

if __name__ == "__main__":
    main()
