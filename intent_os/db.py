from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["intent_os"]

gestures_collection = db["gestures"]
voice_collection = db["voice"]
settings_collection = db["settings"]
logs_collection = db["logs"]
