"""
Data manager for persistent storage and user activity logging
"""
import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from config.settings import DATA_DIR, USER_LOGS_DIR

logger = logging.getLogger(__name__)

class DataManager:
    """Manages persistent data storage and user activity logging"""
    
    def __init__(self):
        self.data_dir = DATA_DIR
        self.user_logs_dir = USER_LOGS_DIR
        self.is_initialized = False
        
        logger.info("📊 DataManager initialized")

    async def initialize(self):
        """Initialize data manager and ensure directories exist"""
        if self.is_initialized:
            return
            
        try:
            # Ensure all directories exist
            os.makedirs(self.data_dir, exist_ok=True)
            os.makedirs(self.user_logs_dir, exist_ok=True)
            
            self.is_initialized = True
            logger.info("✅ DataManager initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize DataManager: {e}")
            raise

    async def log_user_activity(self, telegram_user_id: int, solana_address: str, 
                               activity_type: str, data: Dict[str, Any]):
        """Log user activity with hybrid identification"""
        try:
            if not self.is_initialized:
                await self.initialize()
            
            # Create activity log entry
            activity_entry = {
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat(),
                'telegram_user_id': telegram_user_id,
                'solana_address': solana_address,
                'activity_type': activity_type,
                'data': data
            }
            
            # Get user log file path
            user_log_file = os.path.join(self.user_logs_dir, f"user_{telegram_user_id}.json")
            
            # Load existing logs or create new
            user_logs = []
            if os.path.exists(user_log_file):
                try:
                    with open(user_log_file, 'r') as f:
                        user_logs = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load existing logs for user {telegram_user_id}: {e}")
                    user_logs = []
            
            # Add new activity
            user_logs.append(activity_entry)
            
            # Keep only last 1000 entries per user
            if len(user_logs) > 1000:
                user_logs = user_logs[-1000:]
            
            # Save updated logs
            with open(user_log_file, 'w') as f:
                json.dump(user_logs, f, indent=2)
            
            logger.info(f"📝 Activity logged for user {telegram_user_id}: {activity_type}")
            
        except Exception as e:
            logger.error(f"❌ Failed to log activity for user {telegram_user_id}: {e}")

    async def get_user_activity_logs(self, telegram_user_id: int, 
                                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get user activity logs"""
        try:
            user_log_file = os.path.join(self.user_logs_dir, f"user_{telegram_user_id}.json")
            
            if not os.path.exists(user_log_file):
                return []
            
            with open(user_log_file, 'r') as f:
                user_logs = json.load(f)
            
            # Sort by timestamp (newest first)
            user_logs.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Apply limit if specified
            if limit:
                user_logs = user_logs[:limit]
            
            return user_logs
            
        except Exception as e:
            logger.error(f"❌ Failed to get activity logs for user {telegram_user_id}: {e}")
            return []

    async def get_user_activity_summary(self, telegram_user_id: int) -> Dict[str, Any]:
        """Get summary of user activity"""
        try:
            logs = await self.get_user_activity_logs(telegram_user_id)
            
            if not logs:
                return {
                    'total_activities': 0,
                    'activity_types': {},
                    'first_activity': None,
                    'last_activity': None
                }
            
            # Count activity types
            activity_types = {}
            for log in logs:
                activity_type = log.get('activity_type', 'unknown')
                activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
            
            return {
                'total_activities': len(logs),
                'activity_types': activity_types,
                'first_activity': logs[-1]['datetime'] if logs else None,
                'last_activity': logs[0]['datetime'] if logs else None
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get activity summary for user {telegram_user_id}: {e}")
            return {'error': str(e)}

    async def backup_user_data(self, telegram_user_id: int) -> Optional[str]:
        """Create backup of user data"""
        try:
            user_log_file = os.path.join(self.user_logs_dir, f"user_{telegram_user_id}.json")
            
            if not os.path.exists(user_log_file):
                return None
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"user_{telegram_user_id}_backup_{timestamp}.json"
            backup_path = os.path.join(self.user_logs_dir, backup_filename)
            
            # Copy file
            import shutil
            shutil.copy2(user_log_file, backup_path)
            
            logger.info(f"📋 Backup created for user {telegram_user_id}: {backup_filename}")
            return backup_path
            
        except Exception as e:
            logger.error(f"❌ Failed to backup data for user {telegram_user_id}: {e}")
            return None

    async def get_all_user_stats(self) -> Dict[str, Any]:
        """Get statistics for all users"""
        try:
            if not os.path.exists(self.user_logs_dir):
                return {'total_users': 0, 'total_activities': 0}
            
            total_users = 0
            total_activities = 0
            activity_types = {}
            
            # Iterate through all user log files
            for filename in os.listdir(self.user_logs_dir):
                if filename.startswith('user_') and filename.endswith('.json'):
                    try:
                        user_id_str = filename.replace('user_', '').replace('.json', '').split('_')[0]
                        user_id = int(user_id_str)
                        
                        logs = await self.get_user_activity_logs(user_id)
                        total_users += 1
                        total_activities += len(logs)
                        
                        # Count activity types
                        for log in logs:
                            activity_type = log.get('activity_type', 'unknown')
                            activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
                            
                    except (ValueError, IndexError):
                        continue
            
            return {
                'total_users': total_users,
                'total_activities': total_activities,
                'activity_types': activity_types
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get all user stats: {e}")
            return {'error': str(e)}

    async def cleanup_old_logs(self, days_to_keep: int = 30):
        """Clean up old log entries"""
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            cleaned_files = 0
            cleaned_entries = 0
            
            if not os.path.exists(self.user_logs_dir):
                return
            
            for filename in os.listdir(self.user_logs_dir):
                if filename.startswith('user_') and filename.endswith('.json'):
                    file_path = os.path.join(self.user_logs_dir, filename)
                    
                    try:
                        with open(file_path, 'r') as f:
                            logs = json.load(f)
                        
                        # Filter out old entries
                        filtered_logs = [
                            log for log in logs 
                            if log.get('timestamp', 0) > cutoff_time
                        ]
                        
                        # Only update if we removed entries
                        if len(filtered_logs) < len(logs):
                            with open(file_path, 'w') as f:
                                json.dump(filtered_logs, f, indent=2)
                            
                            cleaned_files += 1
                            cleaned_entries += len(logs) - len(filtered_logs)
                            
                    except Exception as e:
                        logger.warning(f"Could not clean log file {filename}: {e}")
            
            if cleaned_files > 0:
                logger.info(f"🧹 Cleaned {cleaned_entries} old entries from {cleaned_files} files")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old logs: {e}")

    async def export_user_data(self, telegram_user_id: int) -> Optional[Dict[str, Any]]:
        """Export all user data for backup/transfer"""
        try:
            logs = await self.get_user_activity_logs(telegram_user_id)
            summary = await self.get_user_activity_summary(telegram_user_id)
            
            export_data = {
                'telegram_user_id': telegram_user_id,
                'export_timestamp': time.time(),
                'export_datetime': datetime.now().isoformat(),
                'activity_summary': summary,
                'activity_logs': logs,
                'metadata': {
                    'total_logs': len(logs),
                    'export_version': '1.0'
                }
            }
            
            return export_data
            
        except Exception as e:
            logger.error(f"❌ Failed to export data for user {telegram_user_id}: {e}")
            return None

    async def import_user_data(self, telegram_user_id: int, import_data: Dict[str, Any]) -> bool:
        """Import user data from backup"""
        try:
            if 'activity_logs' not in import_data:
                logger.error("Import data missing activity_logs")
                return False
            
            # Backup existing data first
            await self.backup_user_data(telegram_user_id)
            
            # Import new data
            logs = import_data['activity_logs']
            
            # Validate log entries
            validated_logs = []
            for log in logs:
                if all(key in log for key in ['timestamp', 'activity_type', 'data']):
                    validated_logs.append(log)
            
            # Save imported logs
            user_log_file = os.path.join(self.user_logs_dir, f"user_{telegram_user_id}.json")
            with open(user_log_file, 'w') as f:
                json.dump(validated_logs, f, indent=2)
            
            logger.info(f"📥 Imported {len(validated_logs)} activity logs for user {telegram_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to import data for user {telegram_user_id}: {e}")
            return False

    async def cleanup(self):
        """Cleanup data manager resources"""
        try:
            # Perform any final cleanup operations
            await self.cleanup_old_logs()
            
            logger.info("🧹 DataManager cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error during DataManager cleanup: {e}")

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            stats = {
                'data_directory': self.data_dir,
                'user_logs_directory': self.user_logs_dir,
                'total_user_files': 0,
                'total_size_bytes': 0
            }
            
            if os.path.exists(self.user_logs_dir):
                for filename in os.listdir(self.user_logs_dir):
                    if filename.startswith('user_') and filename.endswith('.json'):
                        stats['total_user_files'] += 1
                        
                        file_path = os.path.join(self.user_logs_dir, filename)
                        stats['total_size_bytes'] += os.path.getsize(file_path)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get storage stats: {e}")
            return {'error': str(e)}
