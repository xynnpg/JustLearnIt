import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DriveService:
    def __init__(self):
        try:
            self.SCOPES = [
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/drive'
            ]
            self.credentials_file = os.path.join('instance', 'justlearnit-456510-e82ebe7776e3.json')
            
            logger.info(f"Initializing DriveService with credentials file: {self.credentials_file}")
            
            if not os.path.exists(self.credentials_file):
                logger.error(f"Credentials file not found: {self.credentials_file}")
                raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
            
            self.credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file, scopes=self.SCOPES)
            logger.info("Successfully loaded credentials")
            
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info("Successfully built Drive service")
            
        except Exception as e:
            logger.error(f"Error initializing DriveService: {e}")
            raise

    def upload_file(self, file_path, mime_type, folder_id=None):
        """Upload a file to Google Drive"""
        try:
            logger.info(f"Uploading file: {file_path} with mime type: {mime_type}")
            
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
                
            file_metadata = {
                'name': os.path.basename(file_path)
            }
            if folder_id:
                file_metadata['parents'] = [folder_id]
                logger.debug(f"Setting parent folder ID: {folder_id}")

            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Successfully uploaded file. File ID: {file_id}")
            return file_id
            
        except HttpError as error:
            logger.error(f'Google Drive API error occurred: {error}')
            return None
        except Exception as e:
            logger.error(f'Unexpected error occurred: {e}')
            return None

    def create_folder(self, folder_name, parent_folder_id=None):
        """Create a folder in Google Drive"""
        try:
            logger.info(f"Creating folder: {folder_name}")
            
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
                logger.debug(f"Setting parent folder ID: {parent_folder_id}")

            file = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = file.get('id')
            logger.info(f"Successfully created folder. Folder ID: {folder_id}")
            return folder_id
            
        except HttpError as error:
            logger.error(f'Google Drive API error occurred: {error}')
            return None
        except Exception as e:
            logger.error(f'Unexpected error occurred: {e}')
            return None

    def get_file_url(self, file_id):
        """Get the web view link for a file"""
        try:
            logger.info(f"Getting URL for file ID: {file_id}")
            
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            url = file.get('webViewLink')
            logger.info(f"Successfully retrieved file URL: {url}")
            return url
            
        except HttpError as error:
            logger.error(f'Google Drive API error occurred: {error}')
            return None
        except Exception as e:
            logger.error(f'Unexpected error occurred: {e}')
            return None

# Initialize the drive service
try:
    drive_service = DriveService()
    logger.info("Drive service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize drive service: {e}")
    drive_service = None 