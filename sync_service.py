import os
import time
import threading
from datetime import datetime
from drive_utils import drive_service
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self):
        self.root_folder_id = None
        self.lessons_folder_id = None
        self.tests_folder_id = None
        self.videos_folder_id = None
        self.images_folder_id = None
        self.sync_interval = 300  # 5 minutes in seconds
        self.is_running = False
        self.sync_thread = None
        logger.info("Initializing SyncService")
        self.initialize_folders()

    def initialize_folders(self):
        """Initialize or get existing folders in Google Drive"""
        try:
            logger.info("Starting folder initialization")
            # Create or get root folder
            self.root_folder_id = self._get_or_create_folder("JustLearnIt")
            logger.info(f"Root folder ID: {self.root_folder_id}")
            
            if not self.root_folder_id:
                logger.error("Failed to create/get root folder")
                return
            
            # Create or get subfolders
            self.lessons_folder_id = self._get_or_create_folder("lessons", self.root_folder_id)
            logger.info(f"Lessons folder ID: {self.lessons_folder_id}")
            
            self.tests_folder_id = self._get_or_create_folder("tests", self.root_folder_id)
            logger.info(f"Tests folder ID: {self.tests_folder_id}")
            
            self.videos_folder_id = self._get_or_create_folder("videos", self.root_folder_id)
            logger.info(f"Videos folder ID: {self.videos_folder_id}")
            
            self.images_folder_id = self._get_or_create_folder("images", self.root_folder_id)
            logger.info(f"Images folder ID: {self.images_folder_id}")
            
            logger.info("Google Drive folders initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing folders: {e}")

    def _get_or_create_folder(self, folder_name, parent_id=None):
        """Get existing folder or create a new one"""
        try:
            logger.info(f"Getting/creating folder: {folder_name}")
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            logger.debug(f"Search query: {query}")
            results = drive_service.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            if items:
                logger.info(f"Found existing folder: {folder_name} with ID: {items[0]['id']}")
                return items[0]['id']
            
            # Create new folder if not found
            logger.info(f"Creating new folder: {folder_name}")
            folder_id = drive_service.create_folder(folder_name, parent_id)
            logger.info(f"Created new folder: {folder_name} with ID: {folder_id}")
            return folder_id
        except Exception as e:
            logger.error(f"Error in _get_or_create_folder: {e}")
            return None

    def sync_all(self):
        """Sync all content with Google Drive"""
        logger.info(f"Starting sync at {datetime.now()}")
        self.sync_lessons()
        self.sync_tests()
        self.sync_videos()
        self.sync_images()
        logger.info(f"Sync completed at {datetime.now()}")

    def sync_lessons(self):
        """Sync lessons with Google Drive"""
        lessons_dir = os.path.join('instance', 'lectii')
        if not os.path.exists(lessons_dir):
            logger.warning(f"Lessons directory not found: {lessons_dir}")
            return
        
        logger.info(f"Syncing lessons from {lessons_dir}")
        for filename in os.listdir(lessons_dir):
            file_path = os.path.join(lessons_dir, filename)
            if os.path.isfile(file_path):
                logger.info(f"Syncing lesson file: {filename}")
                self._sync_file(file_path, self.lessons_folder_id)

    def sync_tests(self):
        """Sync tests with Google Drive"""
        tests_dir = os.path.join('instance', 'teste')
        if not os.path.exists(tests_dir):
            logger.warning(f"Tests directory not found: {tests_dir}")
            return
        
        logger.info(f"Syncing tests from {tests_dir}")
        for filename in os.listdir(tests_dir):
            file_path = os.path.join(tests_dir, filename)
            if os.path.isfile(file_path):
                logger.info(f"Syncing test file: {filename}")
                self._sync_file(file_path, self.tests_folder_id)

    def sync_videos(self):
        """Sync videos with Google Drive"""
        videos_dir = os.path.join('instance', 'videos')
        if not os.path.exists(videos_dir):
            logger.warning(f"Videos directory not found: {videos_dir}")
            return
        
        logger.info(f"Syncing videos from {videos_dir}")
        for filename in os.listdir(videos_dir):
            file_path = os.path.join(videos_dir, filename)
            if os.path.isfile(file_path):
                logger.info(f"Syncing video file: {filename}")
                self._sync_file(file_path, self.videos_folder_id)

    def sync_images(self):
        """Sync images with Google Drive"""
        images_dir = os.path.join('instance', 'images')
        if not os.path.exists(images_dir):
            logger.warning(f"Images directory not found: {images_dir}")
            return
        
        logger.info(f"Syncing images from {images_dir}")
        for filename in os.listdir(images_dir):
            file_path = os.path.join(images_dir, filename)
            if os.path.isfile(file_path):
                logger.info(f"Syncing image file: {filename}")
                self._sync_file(file_path, self.images_folder_id)

    def _sync_file(self, file_path, folder_id):
        """Sync a single file with Google Drive"""
        try:
            # Get file metadata
            filename = os.path.basename(file_path)
            mime_type = self._get_mime_type(file_path)
            
            logger.info(f"Syncing file: {filename} to folder ID: {folder_id}")
            
            # Check if file exists in Drive
            query = f"name='{filename}' and '{folder_id}' in parents"
            results = drive_service.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, modifiedTime)'
            ).execute()
            
            items = results.get('files', [])
            
            if items:
                # File exists, check if local file is newer
                drive_file = items[0]
                drive_modified = datetime.fromisoformat(drive_file['modifiedTime'].replace('Z', '+00:00'))
                local_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if local_modified > drive_modified:
                    logger.info(f"Updating file in Drive: {filename}")
                    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
                    drive_service.service.files().update(
                        fileId=drive_file['id'],
                        media_body=media
                    ).execute()
                    logger.info(f"Updated file in Drive: {filename}")
            else:
                logger.info(f"Uploading new file to Drive: {filename}")
                file_id = drive_service.upload_file(file_path, mime_type, folder_id)
                logger.info(f"Uploaded new file to Drive: {filename} with ID: {file_id}")
                
        except Exception as e:
            logger.error(f"Error syncing file {file_path}: {e}")

    def _get_mime_type(self, file_path):
        """Get MIME type based on file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.ogg': 'video/ogg',
            '.html': 'text/html',
            '.json': 'application/json'
        }
        return mime_types.get(ext, 'application/octet-stream')

    def start_sync_service(self):
        """Start the periodic sync service"""
        if not self.is_running:
            logger.info("Starting sync service")
            self.is_running = True
            self.sync_thread = threading.Thread(target=self._sync_loop)
            self.sync_thread.daemon = True
            self.sync_thread.start()
            logger.info("Sync service started")

    def stop_sync_service(self):
        """Stop the periodic sync service"""
        if self.is_running:
            logger.info("Stopping sync service")
            self.is_running = False
            if self.sync_thread:
                self.sync_thread.join()
            logger.info("Sync service stopped")

    def _sync_loop(self):
        """Main sync loop that runs periodically"""
        while self.is_running:
            self.sync_all()
            time.sleep(self.sync_interval)

# Initialize the sync service
sync_service = SyncService() 