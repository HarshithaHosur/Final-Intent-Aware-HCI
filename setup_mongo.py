import urllib.request
import zipfile
import os
import subprocess

url = "https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-6.0.4.zip"
zip_path = "mongo.zip"
extract_path = "mongodb_bin"

if not os.path.exists(extract_path):
    print("Downloading MongoDB...")
    urllib.request.urlretrieve(url, zip_path)
    print("Extracting MongoDB...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    os.remove(zip_path)

data_dir = os.path.join(extract_path, "data")
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

mongo_exe = os.path.join(extract_path, "mongodb-win32-x86_64-windows-6.0.4", "bin", "mongod.exe")
print(f"Starting MongoDB using {mongo_exe} ...")
subprocess.Popen([mongo_exe, "--dbpath", data_dir])
print("MongoDB started in background.")
