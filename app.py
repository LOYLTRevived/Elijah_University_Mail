import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PIL import Image
from pillow_heif import register_heif_opener, HeifImagePlugin
from werkzeug.utils import secure_filename
from sqlalchemy.orm import relationship

# --- Congiguration Imports ---
from config import SQLALCHEMY_DATABASE_URI, UPLOAD_FOLDER, ALLOWED_EXTENSIONS

# --- HEIC Opener Registration ---
try:
    register_heif_opener()
except Exception as e:
    print(f"HEIC registration failed: {e}")

# 1. Initialize the Flask application
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB limit

db = SQLAlchemy(app)

# --- Database Model (The blueprint for youe wntries) ---
class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey('entry.id'), nullable=False)
    media_path = db.Column(db.String(200), nullable=False)
    is_video =  db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Media {self.media_path}>'

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False) # Stroed as YYY-MM-DD
    title = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=False)
    media = relationship('Media', backref='entry', lazy='joined', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Entry {self.date}>'
    
# --- Initial Database Setup ---
# This ensures the database and table are created when you run the app for the first time
with app.app_context():
    db.create_all()

# --- Helper Functions ---

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    from config import ALLOWED_EXTENSIONS
    return '.' in filename and \
              filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_and_save_media(photo_file):
    """
    Handles saving one media file (image/video/heic) and returns the saved path and type.
    """
    if not photo_file or photo_file.filename == '':
        return None, None, None
    
    original_filename = secure_filename(photo_file.filename)
    if not allowed_file(original_filename):
        return None, "Error: Invalid file type!", None
    
    ext = os.path.splitext(original_filename)[-1].lower()
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    is_heic = ext in ('.heic', '.heif')
    is_video = ext in ('.mp4', '.mov', '.webm')

    base_name = os.path.splitext(original_filename)[0]

    # Determine the final extension and name
    if is_heic:
        final_ext = ".jpg"
    elif is_video:
        final_ext = ext 
    else: 
        final_ext = ext 
        
    unique_filename = f"{timestamp}_{base_name}{final_ext}"
    final_save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    db_media_path = f"uploads/{unique_filename}"
    
    try:
        if is_heic:
            # HEIC Conversion Logic
            # NOTE: If multiple files are uploaded extremely quickly, a collision on the temp path might occur.
            # Using the unique_filename structure for the temp path too, but for simplicity sticking to old logic
            temp_heic_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{timestamp}_{base_name}{ext}")
            photo_file.save(temp_heic_path)
            
            img = Image.open(temp_heic_path)
            img = img.convert('RGB')
            img.save(final_save_path, format="jpeg", quality=90)
            
            os.remove(temp_heic_path)
            
        else:
            # Video or Standard Image Saving
            photo_file.save(final_save_path)
        
        # Return path and a flag indicating if it's a video
        return db_media_path, None, is_video 

    except Exception as e:
        return None, f"File processing error: {e}", None

# --- Routes ---

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
# Fetch ALL entries from the database, ordered by date (latest first)
    all_entries = Entry.query.order_by(Entry.date.desc(), Entry.id.desc()).all()
    
    # Render the new template and pass the list of entries
    return render_template('entries.html', entries=all_entries)

@app.route('/new-entry', methods=['GET', 'POST'])
def new_entry():
    if request.method == 'POST':
        # 1. Get form data
        title = request.form.get('title', '').strip()
        description = request.form['description']
        
        # NEW: Get the list of files from the 'photos' input (note the plural name)
        uploaded_files = request.files.getlist('photos') 
        
        
        # 2. Validation: At least one file required
        if not uploaded_files or uploaded_files[0].filename == '':
            return "Error: At least one photo/video is required!", 400

        # 3. Create the new Entry
        new_entry = Entry(
            date=datetime.date.today().strftime("%Y-%m-%d"),
            title=title,
            description=description,
            # No image_path field anymore
        )
        
        media_items = []
        
        # 4. Process all uploaded files
        for photo in uploaded_files:
            media_path, error, is_video = process_and_save_media(photo)
            
            if error:
                # In a real app, you might handle this more gracefully, but for now, fail the whole entry.
                return f"File upload failed: {error}", 400
            
            if media_path:
                # Create a new Media object for each successful file
                new_media = Media(media_path=media_path, is_video=is_video)
                media_items.append(new_media)


        if not media_items:
            # This should be caught by the file validation, but as a safeguard:
             return "Error: No valid files were processed!", 400
        
        # 5. Add all media items to the new entry
        new_entry.media = media_items

        # 6. Save to SQLite
        try:
            db.session.add(new_entry)
            # Media items are automatically added/persisted due to the relationship setup
            db.session.commit()
            return redirect(url_for('entry_success'))
        except Exception as e:
            db.session.rollback()
            return f"Database error: {e}", 500
        

    return render_template('new_entry.html')

@app.route('/entry-success')
def entry_success():
    return render_template('entry-success.html')

# 3. Run the application
if __name__ == '__main__':
    # Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        
    app.run(host='0.0.0.0', port=5001, debug=True)