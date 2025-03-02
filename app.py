import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
import pdfkit
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import chardet
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import IsolationForest
import sqlite3

# Use the Agg backend for Matplotlib (prevents GUI errors)
import matplotlib
matplotlib.use('Agg')

app = Flask(__name__)

# Define folders
UPLOAD_FOLDER = "uploads"
CLEANED_FOLDER = "cleaned_files"
CHARTS_FOLDER = "static/charts"
PDF_FOLDER = "static/pdf"
UPDATED_FILES = "updated_files"

# Ensure folders exist
for folder in [UPLOAD_FOLDER, CLEANED_FOLDER, CHARTS_FOLDER, PDF_FOLDER, UPDATED_FILES]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CLEANED_FOLDER'] = CLEANED_FOLDER
app.config['CHARTS_FOLDER'] = CHARTS_FOLDER
app.config['PDF_FOLDER'] = PDF_FOLDER
app.config['UPDATED_FILES'] = UPDATED_FILES
app.secret_key = 'your_secret_key'  # Flash messages
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    company_name = db.Column(db.String(150), nullable=False)
    warehouse_type = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(60), nullable=False)
    workspace_name = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        company_name = request.form.get('company_name')
        warehouse_type = request.form.get('warehouse_type')
        password = request.form.get('password')
        workspace_name = request.form.get('workspace_name')
        
        # Check if the email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Please use a different email address.', 'danger')
            return redirect(url_for('signup'))
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        user = User(name=name, email=email, company_name=company_name, warehouse_type=warehouse_type, password=hashed_password, workspace_name=workspace_name)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('upload_csv'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('upload_csv'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html')

@app.route('/upload_csv', methods=['GET', 'POST'])
@login_required
def upload_csv():
    if request.method == 'POST':
        if 'csvFile' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['csvFile']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and file.filename.endswith('.csv'):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Load and clean CSV (basic cleaning example)
            df = pd.read_csv(file_path)
            df = df.dropna()  # Remove empty rows
            cleaned_file_path = os.path.join(app.config['CLEANED_FOLDER'], f"cleaned_{filename}")
            df.to_csv(cleaned_file_path, index=False)  # Save cleaned file

            flash('File successfully uploaded and cleaned', 'success')
            print(f"Redirecting to insights with filename: cleaned_{filename}")
            return redirect(url_for('insights', filename=f"cleaned_{filename}"))
        else:
            flash('Invalid file type. Please upload a CSV file.', 'danger')
            return redirect(request.url)
    return render_template('upload.html')

@app.route('/insights/<filename>')
@login_required
def insights(filename):
    file_path = os.path.join(app.config['CLEANED_FOLDER'], filename)
    try:
        df = pd.read_csv(file_path)
        summary = df.describe().to_html()
        return render_template('insights.html', summary=summary, filename=filename)
    except Exception as e:
        flash(f"Error loading insights: {e}", 'danger')
        return redirect(url_for('upload_csv'))

@app.route('/download_cleaned_file/<filename>')
@login_required
def download_cleaned_file(filename):
    file_path = os.path.join(app.config['CLEANED_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash(f"File {filename} not found.", 'danger')
        return redirect(url_for('upload_csv'))

@app.route('/features')
@login_required
def features():
    return render_template('features.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create the database tables
    app.run(debug=True)


