"""
HotelBench Memory Module
Redis session and history store with TTL management
"""

import json
import hashlib
from typing import Any, Optional
import redis
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_TTL


class MemoryStore:
    """Redis-backed memory store for agent sessions."""
    
    def __init__(self, host: str = REDIS_HOST, port: int = REDIS_PORT, db: int = REDIS_DB):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.ttl = REDIS_TTL
    
    def save_run(self, run_id: str, state_dict: dict) -> bool:
        """Save a run's state to Redis with TTL."""
        try:
            key = f"hotelbench:run:{run_id}"
            self.redis.setex(key, self.ttl, json.dumps(state_dict))
            return True
        except Exception as e:
            print(f"Error saving run {run_id}: {e}")
            return False
    
    def get_run(self, run_id: str) -> Optional[dict]:
        """Retrieve a run's state from Redis."""
        try:
            key = f"hotelbench:run:{run_id}"
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Error getting run {run_id}: {e}")
            return None
    
    def update_status(self, run_id: str, status: str, result: Optional[dict] = None) -> bool:
        """Update the status of a run."""
        try:
            run_data = self.get_run(run_id)
            if run_data:
                run_data["status"] = status
                if result is not None:
                    run_data["result"] = result
                return self.save_run(run_id, run_data)
            return False
        except Exception as e:
            print(f"Error updating status for run {run_id}: {e}")
            return False
    
    def append_screenshot(self, run_id: str, base64_png: str) -> bool:
        """Append a screenshot to a run's screenshot list."""
        try:
            key = f"hotelbench:screenshots:{run_id}"
            self.redis.rpush(key, base64_png)
            self.redis.expire(key, self.ttl)
            return True
        except Exception as e:
            print(f"Error appending screenshot for run {run_id}: {e}")
            return False
    
    def get_screenshots(self, run_id: str) -> list[str]:
        """Get all screenshots for a run."""
        try:
            key = f"hotelbench:screenshots:{run_id}"
            return self.redis.lrange(key, 0, -1) or []
        except Exception as e:
            print(f"Error getting screenshots for run {run_id}: {e}")
            return []
    
    def check_idempotency(self, run_id: str, action_hash: str) -> bool:
        """Check if an action has already been performed (returns True if exists)."""
        try:
            key = f"hotelbench:actions:{run_id}"
            return self.redis.sismember(key, action_hash)
        except Exception as e:
            print(f"Error checking idempotency for run {run_id}: {e}")
            return False
    
    def mark_action_done(self, run_id: str, action_hash: str) -> bool:
        """Mark an action as completed for idempotency tracking."""
        try:
            key = f"hotelbench:actions:{run_id}"
            self.redis.sadd(key, action_hash)
            self.redis.expire(key, self.ttl)
            return True
        except Exception as e:
            print(f"Error marking action done for run {run_id}: {e}")
            return False
    
    def append_action_history(self, run_id: str, action: dict) -> bool:
        """Append an action to the run's action history."""
        try:
            run_data = self.get_run(run_id)
            if run_data:
                if "action_history" not in run_data:
                    run_data["action_history"] = []
                run_data["action_history"].append(action)
                return self.save_run(run_id, run_data)
            return False
        except Exception as e:
            print(f"Error appending action history for run {run_id}: {e}")
            return False
    
    def get_action_history(self, run_id: str) -> list[dict]:
        """Get the action history for a run."""
        try:
            run_data = self.get_run(run_id)
            if run_data:
                return run_data.get("action_history", [])
            return []
        except Exception as e:
            print(f"Error getting action history for run {run_id}: {e}")
            return []
    
    def delete_run(self, run_id: str) -> bool:
        """Delete a run and all associated data."""
        try:
            # Delete main run data
            self.redis.delete(f"hotelbench:run:{run_id}")
            # Delete screenshots
            self.redis.delete(f"hotelbench:screenshots:{run_id}")
            # Delete action hashes
            self.redis.delete(f"hotelbench:actions:{run_id}")
            return True
        except Exception as e:
            print(f"Error deleting run {run_id}: {e}")
            return False
    
    def health_check(self) -> bool:
        """Check if Redis is connected and healthy."""
        try:
            return self.redis.ping()
        except Exception as e:
            print(f"Redis health check failed: {e}")
            return False
    
    @staticmethod
    def hash_action(action: dict) -> str:
        """Generate a hash for an action for idempotency tracking."""
        action_str = json.dumps(action, sort_keys=True)
        return hashlib.md5(action_str.encode()).hexdigest()


# Global memory store instance
memory_store = MemoryStore()
