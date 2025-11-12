# 📓 Automated Media Journal

A full-stack Flask application for daily logging with support for images and videos, featuring automated weekly email summary generation and cloud synchronization to Google Drive.

## ✨ Features

* **Daily Entry Web Interface:** Flask front-end for logging text, date, and uploading media.
* **HEIC/Video Support:** Handles various media types in the upload folder.
* **Weekly Email Summary:** Automatically generates and emails a dark-mode HTML summary.
* **Media Handling:** Compresses images for inline embedding and uploads large files (like videos) to Google Drive for cloud links, bypassing email size limits.
* **Scheduled Automation:** Designed to run weekly via Windows Task Scheduler or cron job.

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
git clone [YOUR_REPOSITORY_URL]
cd [PROJECT_FOLDER_NAME]
```

### 2. Set up the Virtual Environment

```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configuration and Credentials (CRITICAL)

Create two files in the root directory:

#### a. .env file (For Email and Drive Folder ID)

Get your App Password from your email provider and your Google Drive Folder ID before filling this out.

```bash
# .env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your-sender-email@example.com
EMAIL_PASSWORD=your_generated_app_password
GOOGLE_DRIVE_FOLDER_ID=1A2B3C4D5E6F7G8H9I0J
```

#### b. google_credentials.json (For Drive API)

Follow the Google Cloud Console instructions to create a Service Account and download the JSON key file. Place this file directly in the project root.

### 5. Initialize the Database

Run the app once to create the database.db file and the necessary tables:

```bash
# Run the main Flask app
python app.py
```

### 6. Run the Automation

The script `weekly_automation_runner.py` handles both the email generation and the Google Drive upload/cleanup.

```bash
python weekly_automation_runner.py
```

### 7. Schedule the Task

Set up a weekly schedule (e.g., using Windows Task Scheduler or cron) to run the `weekly_automation_runner.py` script.