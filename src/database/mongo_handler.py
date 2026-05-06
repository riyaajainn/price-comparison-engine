import os
from pymongo import MongoClient, DESCENDING
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class MongoHandler:
    def __init__(self):
        # Fallback to localhost if MONGO_URI is missing
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self.client = MongoClient(mongo_uri)
        self.db = self.client["test"]
        self.collection = self.db["site_deals"]
        # Ensure temporal sorting is optimized
        try:
            self.collection.create_index([("updated_at", DESCENDING)])
        except Exception as e:
            print(f"[!] Mongo Index Error: {e}")

    def save_deal(self, final_result):
        """Saves or updates a deal without affecting scraper logic."""
        if not final_result or final_result.get("status") == "failed":
            return
        
        try:
            # Prepare document with temporal metadata
            document = {
                **final_result,
                "updated_at": datetime.utcnow()
            }
            
            # Unique identifier to prevent duplicates: Input URL
            input_url = final_result.get("input_product", {}).get("url")
            if not input_url:
                return
                
            query = {"input_product.url": input_url}
            
            # Use upsert=True to create if doesn't exist
            self.collection.update_one(query, {"$set": document}, upsert=True)
            print("[*] Data persisted to 'site_deals' collection.")
        except Exception as e:
            print(f"[-] MongoDB Save Error: {e}")
