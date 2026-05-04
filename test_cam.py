import cv2

print("Testing camera APIs and indices...")
working_cams = []

apis = {
    "CAP_ANY": cv2.CAP_ANY,
    "CAP_DSHOW": cv2.CAP_DSHOW,
    "CAP_MSMF": cv2.CAP_MSMF
}

for i in range(5):
    for api_name, api_code in apis.items():
        cap = cv2.VideoCapture(i, api_code)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"[SUCCESS] Index {i} with API {api_name} works and reads frames!")
                working_cams.append((i, api_code))
            else:
                print(f"[WARN] Index {i} with API {api_name} opens, but cannot read frames.")
            cap.release()
        else:
            pass # Failed

if not working_cams:
    print("\n[FAILURE] Exhausted all common indices and APIs.")
    print("This means either:")
    print("1. Your camera is in use by another program (Zoom, Teams, etc.).")
    print("2. Windows Privacy Settings are blocking your app from accessing the camera (Check Settings -> Privacy -> Camera).")
    print("3. You don't have a camera connected to this device.")
    print("4. You need to restart your laptop.")
else:
    print(f"\n[OK] Found working configurations: {working_cams}")
