import datetime
from pymongo import MongoClient

class SystemLogger:
    def __init__(self):
        try:
            self.client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
            self.db = self.client["intent_os"]
            self.logs_collection = self.db["logs"]
            # Test connection
            self.client.server_info()
            self.enabled = True
        except Exception as e:
            print(f"[Logger Error] Could not connect to MongoDB: {e}")
            self.enabled = False

    def log_event(self, event_type, command, action, status="completed", details=None):
        if not self.enabled:
            return False
        try:
            log_entry = {
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "event_type": event_type,
                "command": command,
                "action": action,
                "status": status,
                "details": details or {}
            }
            self.logs_collection.insert_one(log_entry)
            return True
        except Exception as e:
            print(f"[Logger Error] Failed to write log: {e}")
            return False

# Singleton instance
logger = SystemLogger()

def log_event(event_type, command, action, status="completed", details=None):
    return logger.log_event(event_type, command, action, status, details)
