import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PIL import Image
from pillow_heif import register_heif_opener, HeifImagePlugin
from werkzeug.utils import secure_filename

# --- Congiguration Imports ---
from config import SQLALCHEMY_DATABASE_URI, UPLOAD_FOLDER

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
class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False) # Stroed as YYY-MM-DD
    title = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(200), nullable=False) # Path to saved image

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
        photo = request.files.get('photo')
        
        
        # 2. Validation: Image required (already enforced by 'required' in HTML, but check again)
        if not photo or photo.filename == '':
            # Flash message system would be better, but for simplicity:
            return "Error: Photo is required!", 400
        
        original_filename = secure_filename(photo.filename)
        ext = os.path.splitext(original_filename)[-1].lower()
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        is_heic = ext in ('.heic', '.heif')
        is_video = ext in ('.mp4', '.mov', '.webm')
        is_image = allowed_file(original_filename) and not is_video

        # 3. File Handling: Check extension and save file
        if is_image or is_heic or is_video:
            
            base_name = os.path.splitext(original_filename)[0]
            
            # Determine the final extension and name
            if is_heic:
                # Converted image is always JPG
                final_ext = ".jpg"
            elif is_video:
                # Video keeps its original extension (e.g., .mp4)
                final_ext = ext 
            else: 
                # Standard image keeps its original extension
                final_ext = ext 
                
            unique_filename = f"{timestamp}_{base_name}{final_ext}"
            final_save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            db_image_path = f"uploads/{unique_filename}"
            
            try:
                if is_heic:
                    # HEIC Conversion Logic (as before)
                    temp_heic_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{timestamp}{ext}")
                    photo.save(temp_heic_path)
                    
                    img = Image.open(temp_heic_path)
                    img = img.convert('RGB')
                    img.save(final_save_path, format="jpeg", quality=90)
                    
                    os.remove(temp_heic_path)
                    
                elif is_video:
                    # Video Saving: Save the file directly
                    photo.save(final_save_path)
                    
                else:
                    # Standard Image Saving (JPG, PNG, GIF)
                    photo.save(final_save_path) 

            except Exception as e:
                return f"File processing error: {e}", 500
            
            # 4. Save to SQLite (same as before)
            new_entry = Entry(
                date=datetime.date.today().strftime("%Y-%m-%d"),
                title=title,
                description=description,
                image_path=db_image_path # This field now holds the path for either image or video
            )
            
            try:
                db.session.add(new_entry)
                db.session.commit()
                return redirect(url_for('entry_success'))
            except Exception as e:
                db.session.rollback()
                return f"Database error: {e}", 500
        else:
            return "Error: Invalid file type! Only images and videos are allowed.", 400

    return render_template('new_entry.html')

@app.route('/entry-success')
def entry_success():
    return render_template('entry-success.html')

# 3. Run the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)