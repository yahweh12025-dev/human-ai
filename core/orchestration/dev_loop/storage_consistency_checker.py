#!/usr/bin/env python3
"""
Background Consistency Check between Supabase and Firebase
For autonomous development loop task: storage-audit-1
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SupabaseFirebaseConsistencyChecker:
    def __init__(self):
        self.supabase_client = None
        self.firebase_client = None
        self._init_clients()
    
    def _init_clients(self):
        """Initialize Supabase and Firebase clients if credentials are available"""
        # Try to initialize Supabase
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if supabase_url and supabase_key:
            try:
                import supabase
                self.supabase_client = supabase.create_client(supabase_url, supabase_key)
                logger.info("✅ Supabase client initialized for consistency check")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Supabase client: {e}")
        else:
            logger.warning("⚠️ Supabase credentials not found in environment variables")
        
        # Try to initialize Firebase
        firebase_project_id = os.getenv("FIREBASE_PROJECT_ID")
        
        if firebase_project_id:
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore
                
                if not firebase_admin._apps:
                    # Try Application Default credentials
                    cred = credentials.ApplicationDefault()
                    firebase_admin.initialize_app(cred)
                
                self.firebase_client = firestore.client()
                logger.info("✅ Firebase client initialized for consistency check")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Firebase client: {e}")
        else:
            logger.warning("⚠️ Firebase project ID not found in environment variables")
    
    def check_agent_logs_consistency(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        Check consistency of agent_logs between Supabase and Firebase
        
        Args:
            hours_back: How many hours back to check for consistency
            
        Returns:
            Dict with consistency check results
        """
        if not self.supabase_client or not self.firebase_client:
            return {
                "status": "skipped",
                "reason": "One or both clients not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "hours_checked": hours_back,
            "cutoff_time": cutoff_time,
            "supabase_count": 0,
            "firebase_count": 0,
            "in_supabase_not_firebase": [],
            "in_firebase_not_supabase": [],
            "status": "completed"
        }
        
        try:
            # Get logs from Supabase
            logger.info(f"Fetching agent logs from Supabase since {cutoff_time}")
            supabase_response = self.supabase_client.table("agent_logs")\
                .select("*", count="exact")\
                .gte("timestamp", cutoff_time)\
                .execute()
            
            supabase_logs = supabase_response.data if hasattr(supabase_response, 'data') else []
            results["supabase_count"] = len(supabase_logs)
            logger.info(f"Found {len(supabase_logs)} logs in Supabase")
            
            # Get logs from Firebase
            logger.info(f"Fetching agent logs from Firebase since {cutoff_time}")
            firebase_collection = self.firebase_client.collection("agent_logs")
            firebase_query = firebase_collection.where("timestamp", ">=", cutoff_time)
            firebase_docs = firebase_query.stream()
            
            firebase_logs = []
            for doc in firebase_docs:
                data = doc.to_dict()
                data["id"] = doc.id  # Include document ID for comparison
                firebase_logs.append(data)
            
            results["firebase_count"] = len(firebase_logs)
            logger.info(f"Found {len(firebase_logs)} logs in Firebase")
            
            # For now, we'll do a simple count comparison
            # In a full implementation, we'd compare specific entries by ID or hash
            if results["supabase_count"] != results["firebase_count"]:
                results["status"] = "inconsistent"
                results["discrepancy"] = abs(results["supabase_count"] - results["firebase_count"])
                logger.warning(f"⚠️ Count discrepancy: Supabase={results['supabase_count']}, Firebase={results['firebase_count']}")
            else:
                results["status"] = "consistent"
                logger.info("✅ Log counts are consistent between Supabase and Firebase")
                
        except Exception as e:
            logger.error(f"❌ Error during consistency check: {e}")
            results["status"] = "error"
            results["error"] = str(e)
        
        return results
    
    def run_consistency_check(self, hours_back: int = 24) -> None:
        """Run a single consistency check and log results"""
        logger.info("🔄 Starting Supabase-Firebase consistency check...")
        start_time = time.time()
        
        results = self.check_agent_logs_consistency(hours_back)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Consistency check completed in {elapsed_time:.2f} seconds")
        
        # Log results
        if results["status"] == "completed":
            if results.get("supabase_count", 0) == results.get("firebase_count", 0):
                logger.info(f"✅ CONSISTENT: {results['supabase_count']} logs in both systems")
            else:
                logger.warning(f"⚠️ INCONSISTENT: Supabase={results.get('supabase_count', 0)}, Firebase={results.get('firebase_count', 0)}")
        elif results["status"] == "skipped":
            logger.info(f"⏭️ SKIPPED: {results.get('reason', 'Unknown reason')}")
        else:
            logger.error(f"❌ ERROR: {results.get('error', 'Unknown error')}")
        
        return results

def main():
    """Main function to run the consistency check"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check consistency between Supabase and Firebase')
    parser.add_argument('--hours', type=int, default=24, help='Hours back to check for consistency')
    parser.add_argument('--continuous', action='store_true', help='Run continuously every 30 minutes')
    parser.add_argument('--interval', type=int, default=1800, help='Interval in seconds for continuous mode (default: 30 minutes)')
    
    args = parser.parse_args()
    
    checker = SupabaseFirebaseConsistencyChecker()
    
    if args.continuous:
        logger.info(f"🔄 Starting continuous consistency check (every {args.interval} seconds)")
        try:
            while True:
                checker.run_consistency_check(args.hours)
                logger.info(f"💤 Sleeping for {args.interval} seconds until next check...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("🛑 Consistency check stopped by user")
    else:
        # Single run
        checker.run_consistency_check(args.hours)

if __name__ == "__main__":
    main()
