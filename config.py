import os
from dotenv import load_dotenv # NEW IMPORT
load_dotenv() # NEW: Load environment variables from .env file


#Define the base directoy of the application
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

#SQLite Database Config
# The database.db file will be created in the main project folder
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')

# File uplaod Config
# Images will be saved in the 'uploads' folder
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'heic', 'mp4', 'mov', 'webm'}


MAX_INLINE_IMAGE_SIZE_BYTES = 10485760

# Email Config
SMTP_SERVER = os.environ.get('SMTP_SERVER')  
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587)) # Safe way to get port
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')    
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')

CLOUD_STORAGE_BASE_URL = os.environ.get('CLOUD_STORAGE_BASE_URL')