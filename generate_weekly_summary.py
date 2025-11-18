import os
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import mimetypes
from PIL import Image
import tempfile
import shutil

# 🚨 CRITICAL UPDATE: Import the new Media model and required SQLAlchemy functions
from app import app, db, Entry, Media 
from flask import render_template
# from sqlalchemy.orm import joinedload # Flask-SQLAlchemy usually accesses this via db.joinedload

from config import (
    UPLOAD_FOLDER, 
    SMTP_SERVER, 
    SMTP_PORT, 
    EMAIL_ADDRESS, 
    EMAIL_PASSWORD, 
    RECIPIENT_EMAIL,
    MAX_INLINE_IMAGE_SIZE_BYTES,
    CLOUD_STORAGE_BASE_URL
)

# --- Configuration ---
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.webm') 
COMPRESSED_TEMP_DIR = tempfile.gettempdir()

# --- Helper Functions (No changes required for the helpers) ---

def is_video_file(filename):
    """Checks if a file is a video based on its extension."""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[-1].lower()
    return ext in VIDEO_EXTENSIONS

def get_last_week_dates():
    """Calculates the date range, covering the last 7 days PLUS today."""
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=7) 
    end_date = today 
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def compress_image(original_path, filename):
    """Compresses an image to a temporary path if it exceeds a size limit."""
    
    # 1. Define the temporary output path
    temp_filename = f"compressed_{filename}"
    temp_path = os.path.join(COMPRESSED_TEMP_DIR, temp_filename)
    
    # 2. Open and save with compression
    try:
        img = Image.open(original_path)
        img.save(temp_path, format=img.format, optimize=True, quality=80) 
        
        # 3. Check if compression was effective (or necessary)
        if os.path.getsize(temp_path) < os.path.getsize(original_path):
            print(f"Compressed {filename}: {os.path.getsize(original_path) / (1024*1024):.2f}MB -> {os.path.getsize(temp_path) / (1024*1024):.2f}MB")
            return temp_path
        else:
            # Compression didn't help much, just use the original file
            os.remove(temp_path)
            return original_path
            
    except Exception as e:
        print(f"Error during compression of {filename}: {e}. Using original file.")
        return original_path

def send_email(subject, html_body, media_list):
    """Sends the summary email with inline media handling."""
    print(f"\n--- Sending Email to {RECIPIENT_EMAIL} ---")
    
    msg = MIMEMultipart('mixed')
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject

    msg_related = MIMEMultipart('related')
    msg_related.attach(MIMEText(html_body, 'html'))
    msg.attach(msg_related)
    
    # List to track temporary files that need cleanup after sending
    temp_files_to_cleanup = []

    for media in media_list:
        original_path = media['local_media_path']
        filename = media['media_filename']
        
        if not os.path.exists(original_path):
            print(f"Warning: File not found at {original_path}. Skipping.")
            continue

        # --- VIDEO/LARGE FILE HANDLING ---
        # The logic here is fine, it handles a flattened list of all media items
        if media['is_video'] or os.path.getsize(original_path) > MAX_INLINE_IMAGE_SIZE_BYTES:
            
            # Skip attachment entirely and rely on the cloud link in the HTML
            print(f"Skipping direct attachment for large file: {filename}")
            continue
            
        # --- IMAGE EMBEDDING (Compression if needed) ---
        else:
            final_media_path = original_path
            
            # Check if image is large and attempt compression
            if os.path.getsize(original_path) > MAX_INLINE_IMAGE_SIZE_BYTES:
                final_media_path = compress_image(original_path, filename)
                if final_media_path != original_path:
                    temp_files_to_cleanup.append(final_media_path)
            
            try:
                with open(final_media_path, 'rb') as fp:
                    img = MIMEImage(fp.read())
                
                # Set the Content-ID matching the src="cid:..." in the HTML
                img.add_header('Content-ID', f'<{filename}>')
                img.add_header('Content-Disposition', 'inline', filename=filename)
                msg_related.attach(img)
                print(f"Embedded image: {filename} (inline CID, size OK)")
            except Exception as e:
                print(f"Error embedding image {filename}: {e}")

    # Connect to the SMTP server and send
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())
        print("Email sent successfully!")
        return True
    except smtplib.SMTPAuthenticationError:
        print("\n!!! ERROR: SMTP Authentication Failed. Check EMAIL_ADDRESS and EMAIL_PASSWORD (App Password).")
        return False
    except Exception as e:
        print(f"\n!!! ERROR: Failed to send email: {e}")
        return False
    finally:
        # Cleanup temporary files
        for f in temp_files_to_cleanup:
            try:
                os.remove(f)
            except Exception:
                pass


# --- Main Summary Generation Logic (Modified to handle multiple media files) ---

def generate_summary_and_send():
    """Generates the summary and calls the email sending function."""
    with app.app_context():
        start_date, end_date_incl = get_last_week_dates()
        
        # 🚨 UPDATE: Use joinedload to fetch associated Media objects efficiently
        entries = db.session.execute(
            db.select(Entry)
            .where(Entry.date >= start_date)
            .where(Entry.date <= end_date_incl) 
            .order_by(Entry.date.desc())
            .options(db.joinedload(Entry.media)) # Assuming the relationship is named 'media'
        ).scalars().all()
        
        if not entries:
            print(f"\n--- Weekly Summary --- No entries found for the period {start_date} to {end_date_incl}. Email skipped.")
            return

        print(f"\n--- Generating Weekly Summary ({start_date} to {end_date_incl}) ---")
        
        summary_data = [] # List of dictionaries for the template
        media_list = []   # Flattened list of ALL media items for email attachment
        
        for entry in entries:
            entry_media_items = [] # List of media for this specific entry (for the HTML template)
            
            # 🚨 UPDATE: Loop through the media items attached to the entry
            for media_obj in entry.media:
                filename = media_obj.media_path.split('/')[-1]
                
                # Use the 'is_video' property from the database
                is_vid = media_obj.is_video 
                full_local_media_path = os.path.join(UPLOAD_FOLDER, filename)
                
                # Determine if we should use an external link (for videos and oversized images)
                is_external_link = is_vid or (os.path.exists(full_local_media_path) and os.path.getsize(full_local_media_path) > MAX_INLINE_IMAGE_SIZE_BYTES)

                media_info = {
                    'is_video': is_vid,
                    'is_external_link': is_external_link, # New flag for the template
                    'local_media_path': full_local_media_path,
                    'media_filename': filename,
                    'external_url': CLOUD_STORAGE_BASE_URL + filename # Used in HTML template
                }
                
                # Add to the flattened list for email attachment processing
                media_list.append(media_info)
                
                # Add to the entry's list for the HTML template
                entry_media_items.append(media_info)

            summary_data.append({
                'date': entry.date,
                'title': entry.title,
                'description': entry.description,
                'media_items': entry_media_items # 🚨 NEW: Pass the list of media items to the template
            })
            
        html_body = render_template(
            'weekly_email.html',
            entries=summary_data,
            start_date=start_date,
            end_date=end_date_incl
        )

        subject = f"Weekly Log Summary: {start_date} to {end_date_incl}"
        
        # The send_email function now receives the flattened list of all media
        send_email(subject, html_body, media_list)


if __name__ == '__main__':
    generate_summary_and_send()