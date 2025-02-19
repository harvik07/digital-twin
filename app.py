import os
import logging
import pandas as pd
from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Folder Configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")  # Absolute path
CLEANED_FOLDER = os.path.join(os.getcwd(), "cleaned_files")  # Absolute path
LOG_FILE = os.path.join(os.getcwd(), "app_debug.log")  # Log file

# Ensure folders exist
for folder in [UPLOAD_FOLDER, CLEANED_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# 🔹 Set up logging
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CLEANED_FOLDER'] = CLEANED_FOLDER
app.secret_key = 'your_secret_key'  # Secret key for flash messages

# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            logging.error("❌ No file part in request")
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            logging.error("❌ No file selected")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            try:
                file.save(file_path)  # Save the uploaded file
                logging.info(f"✅ File uploaded: {filename}")
                flash(f'File uploaded successfully: {filename}')
                return redirect(url_for('clean_file', filename=filename))  # Redirect to clean file
            except Exception as e:
                flash(f'Error saving file: {e}')
                logging.error(f"❌ Error saving file: {e}")
                return redirect(url_for('home'))
        else:
            flash('Invalid file format. Only CSV and XLSX files are allowed.')
            logging.error(f"❌ Invalid file format: {file.filename}")
            return redirect(request.url)

    return render_template('index.html')

@app.route('/clean/<filename>')
def clean_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    cleaned_filename = f"cleaned_{filename}"
    cleaned_file_path = os.path.join(app.config['CLEANED_FOLDER'], cleaned_filename)

    logging.info(f"📂 Checking if file exists: {file_path}")
    if not os.path.exists(file_path):
        flash('Uploaded file not found!')
        logging.error(f"❌ File not found: {file_path}")
        return redirect(url_for('home'))

    try:
        # Load data
        if filename.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            flash('Unsupported file format')
            logging.error(f"❌ Unsupported file format: {filename}")
            return redirect(url_for('home'))

        # Clean data: Remove NaN & duplicates
        df_cleaned = df.dropna().drop_duplicates()

        # Save the cleaned file
        if filename.endswith('.csv'):
            df_cleaned.to_csv(cleaned_file_path, index=False)
        else:
            df_cleaned.to_excel(cleaned_file_path, index=False)

        logging.info(f"✅ Cleaned file saved at: {cleaned_file_path}")

        # Generate summary statistics
        summary_stats = df_cleaned.describe().to_html()

        flash(f'File cleaned successfully: {cleaned_filename}')
        return render_template('summary.html', summary_stats=summary_stats, filename=cleaned_filename)

    except Exception as e:
        flash(f'Error processing file: {e}')
        logging.error(f"❌ Error processing file: {e}")
        return redirect(url_for('home'))

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['CLEANED_FOLDER'], filename)

    if os.path.exists(file_path):
        logging.info(f"📥 Download requested for: {filename}")
        return send_file(file_path, as_attachment=True)
    else:
        flash('File not found for download.')
        logging.error(f"❌ Download failed - File not found: {filename}")
        return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)

    
