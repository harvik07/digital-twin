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

# 🏠 Home - File Upload & Cleaning
@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html')

# 📊 Summary Page - Show Summary & Download Option
@app.route('/summary/<filename>')
def summary(filename):
    cleaned_file_path = os.path.join(app.config['CLEANED_FOLDER'], filename)
    try:
        # Detect file encoding
        with open(cleaned_file_path, 'rb') as f:
            result = chardet.detect(f.read())
            encoding = result['encoding']

        # Load file with detected encoding
        df = pd.read_csv(cleaned_file_path, encoding=encoding) if filename.endswith('.csv') else pd.read_excel(cleaned_file_path)
        summary = df.describe().to_html()
        return render_template("summary.html", summary=summary, cleaned_filename=filename)
    except Exception as e:
        flash(f"Error loading summary: {e}", "danger")
        return redirect(url_for('home'))

# 📈 Data Visualization Page - Generate Charts
@app.route('/visualization/<filename>', methods=['GET', 'POST'])
def visualization(filename):
    cleaned_file_path = os.path.join(app.config['CLEANED_FOLDER'], filename)

    if not os.path.exists(cleaned_file_path):
        flash(f"File {filename} not found.")
        return redirect(url_for('home'))

    try:
        # Detect file encoding
        with open(cleaned_file_path, 'rb') as f:
            result = chardet.detect(f.read())
            encoding = result['encoding']

        # Load file with detected encoding
        if filename.endswith('.csv'):
            chunks = pd.read_csv(cleaned_file_path, encoding=encoding, chunksize=10000)
            df = pd.concat(chunks)
        else:
            df = pd.read_excel(cleaned_file_path)
        columns = df.columns.tolist()

        if request.method == 'POST':
            chart_type = request.form.get('chart_type')
            x_column = request.form.get('x_column')
            y_column = request.form.get('y_column')

            chart_filename = f"chart_{filename}_{chart_type}.png"
            chart_path = os.path.join(app.config['CHARTS_FOLDER'], chart_filename)

            # Delete previous chart file if it exists
            if os.path.exists(chart_path):
                os.remove(chart_path)

            plt.figure(figsize=(12, 8), dpi=100)  # High-resolution

            if chart_type == "bar":
                sns.barplot(x=df[x_column], y=df[y_column])
            elif chart_type == "line":
                sns.lineplot(x=df[x_column], y=df[y_column])
            elif chart_type == "pie":
                df[y_column].value_counts().plot.pie(autopct='%1.1f%%')
            elif chart_type == "heatmap":
                sns.heatmap(df.corr(), annot=True, cmap='coolwarm')
            elif chart_type == "histogram":
                sns.histplot(df[x_column])
            elif chart_type == "scatter":
                sns.scatterplot(x=df[x_column], y=df[y_column])
            elif chart_type == "box":
                sns.boxplot(x=df[x_column], y=df[y_column])

            plt.xticks(rotation=45)
            plt.tight_layout()  # Adjust layout to prevent overlap
            plt.savefig(chart_path, dpi=100)
            plt.close()

            return render_template('visualization.html', columns=columns, filename=filename, chart_url=chart_filename)

        return render_template('visualization.html', columns=columns, filename=filename, chart_url=None)

    except Exception as e:
        flash(f"Error loading visualization: {e}", "danger")
        return redirect(url_for('home'))

# 🏢 2D Warehouse Visualization Route
@app.route('/warehouse_2d_model/<filename>')
def warehouse_2d_model(filename):
    cleaned_file_path = os.path.join(app.config['CLEANED_FOLDER'], filename)

    if not os.path.exists(cleaned_file_path):
        flash(f"File {filename} not found.")
        return redirect(url_for('home'))

    try:
        df = pd.read_csv(cleaned_file_path) if filename.endswith('.csv') else pd.read_excel(cleaned_file_path)

        # Ensure only required columns exist
        required_columns = ['Shelf Number', 'Product Name', 'Quantity Available']
        if not all(column in df.columns for column in required_columns):
            flash("To generate the 2D layout, your CSV must have these columns: Shelf Number, Product Name, Quantity Available.", "danger")
            return redirect(url_for('summary', filename=filename))

        df = df[required_columns]  

        # Convert data to JSON for 2D visualization
        warehouse_data = df.to_dict(orient='records')

        return render_template("2dwarehouse.html", warehouse_data=warehouse_data)

    except Exception as e:
        flash(f"Error loading 2D warehouse model: {e}", "danger")
        return redirect(url_for('home'))

# 🏢 Search & Filter Warehouse Visualization Route
@app.route('/search_layout', methods=['GET', 'POST'])
def search_layout():
    cleaned_file_path = os.path.join(app.config['CLEANED_FOLDER'], 'cleaned_warehouse.csv')

    if not os.path.exists(cleaned_file_path):
        flash(f"File not found.")
        return redirect(url_for('home'))

    try:
        df = pd.read_csv(cleaned_file_path) if cleaned_file_path.endswith('.csv') else pd.read_excel(cleaned_file_path)

        # Ensure only required columns exist
        required_columns = ['Shelf Number', 'Product Name', 'Quantity Available']
        if not all(column in df.columns for column in required_columns):
            flash("To generate the 2D layout, your CSV must have these columns: Shelf Number, Product Name, Quantity Available.", "danger")
            return redirect(url_for('home'))

        df = df[required_columns]

        # Convert data to JSON for 2D visualization
        warehouse_data = df.to_dict(orient='records')

        return render_template("search_layout.html", warehouse_data=warehouse_data)

    except Exception as e:
        flash(f"Error loading 2D warehouse model: {e}", "danger")
        return redirect(url_for('home'))

# 📝 Generate Report Route
@app.route('/generate_report/<filename>', methods=['GET', 'POST'])
def generate_report(filename):
    cleaned_file_path = os.path.join(app.config['CLEANED_FOLDER'], filename)

    if not os.path.exists(cleaned_file_path):
        flash(f"File {filename} not found.")
        return redirect(url_for('home'))

    try:
        # Detect file encoding
        with open(cleaned_file_path, 'rb') as f:
            result = chardet.detect(f.read())
            encoding = result['encoding']

        # Load file with detected encoding
        if filename.endswith('.csv'):
            chunks = pd.read_csv(cleaned_file_path, encoding=encoding, chunksize=10000)
            df = pd.concat(chunks)
        else:
            df = pd.read_excel(cleaned_file_path)

        # Ensure required columns exist or calculate them
        if 'Profit per Unit' not in df.columns:
            df['Profit per Unit'] = df['Selling_Price'] - df['Purchase_Price']
        if 'Profit Margin (%)' not in df.columns:
            df['Profit Margin (%)'] = ((df['Selling_Price'] - df['Purchase_Price']) / df['Selling_Price']) * 100
        if 'Stock Turnover Rate' not in df.columns:
            df['Stock Turnover Rate'] = df['Total Sales Volume'] / df['Quantity Available']

        # Ensure required columns exist
        required_columns = [
            'Product Name', 'Purchase_Price', 'Selling_Price', 'Total Sales Volume', 'Total Revenue',
            'Profit per Unit', 'Profit Margin (%)', 'Stock Turnover Rate', 'Quantity Available'
        ]
        if not all(column in df.columns for column in required_columns):
            flash("Your Excel file must contain these columns: Product Name, Purchase_Price, Selling_Price, Total Sales Volume, Total Revenue, Profit per Unit, Profit Margin (%), Stock Turnover Rate, Quantity Available.", "danger")
            return redirect(url_for('summary', filename=filename))

        # Calculate insights
        most_stocked_product = df.loc[df['Quantity Available'].idxmax()]['Product Name']
        slow_moving_products = df[df['Stock Turnover Rate'] < 1]['Product Name'].tolist()
        total_stock = df['Quantity Available'].sum()
        most_valuable_product = df.loc[df['Total Revenue'].idxmax()]['Product Name']
        least_valuable_product = df.loc[df['Total Revenue'].idxmin()]['Product Name']
        most_profitable_product = df.loc[df['Profit Margin (%)'].idxmax()]['Product Name']
        least_profitable_product = df.loc[df['Profit Margin (%)'].idxmin()]['Product Name']
        best_selling_product = df.loc[df['Total Sales Volume'].idxmax()]['Product Name']
        worst_selling_product = df.loc[df['Total Sales Volume'].idxmin()]['Product Name']

        # Warehouse density analysis
        warehouse_density_message = ""
        available_space = None
        if request.method == 'POST':
            total_capacity = float(request.form.get('total_capacity'))
            used_space = df['Storage Space (cubic ft)'].sum() if 'Storage Space (cubic ft)' in df.columns else 0
            available_space = total_capacity - used_space
            warehouse_density_message = "Warehouse has sufficient space." if available_space > 0 else "Warning: Warehouse is almost full."

            # Save updated CSV file
            updated_filename = f"updated_{filename}"
            updated_path = os.path.join(app.config['UPDATED_FILES'], updated_filename)
            df.to_csv(updated_path, index=False) if filename.endswith('.csv') else df.to_excel(updated_path, index=False)

            return render_template("report.html", 
                                   most_stocked_product=most_stocked_product,
                                   slow_moving_products=slow_moving_products,
                                   total_stock=total_stock,
                                   most_valuable_product=most_valuable_product,
                                   least_valuable_product=least_valuable_product,
                                   most_profitable_product=most_profitable_product,
                                   least_profitable_product=least_profitable_product,
                                   best_selling_product=best_selling_product,
                                   worst_selling_product=worst_selling_product,
                                   warehouse_density_message=warehouse_density_message,
                                   available_space=available_space,
                                   updated_filename=updated_filename)

        return render_template("report.html", 
                               most_stocked_product=most_stocked_product,
                               slow_moving_products=slow_moving_products,
                               total_stock=total_stock,
                               most_valuable_product=most_valuable_product,
                               least_valuable_product=least_valuable_product,
                               most_profitable_product=most_profitable_product,
                               least_profitable_product=least_profitable_product,
                               best_selling_product=best_selling_product,
                               worst_selling_product=worst_selling_product,
                               warehouse_density_message=warehouse_density_message,
                               available_space=available_space)

    except Exception as e:
        flash(f"Error generating report: {e}", "danger")
        return redirect(url_for('home'))

# 📄 Download Updated CSV Route
@app.route('/download_updated_file/<filename>')
def download_updated_file(filename):
    updated_file_path = os.path.join(app.config['UPDATED_FILES'], filename)
    if os.path.exists(updated_file_path):
        return send_file(updated_file_path, as_attachment=True)
    else:
        flash(f"File {filename} not found.", "danger")
        return redirect(url_for('home'))

# 📄 Generate PDF Route
@app.route('/generate_pdf/<filename>')
def generate_pdf(filename):
    try:
        report_html = url_for('generate_report', filename=filename, _external=True)
        pdf_path = os.path.join(app.config['PDF_FOLDER'], f'report_{filename}.pdf')
        pdfkit.from_url(report_html, pdf_path)
        return send_file(pdf_path, as_attachment=True)
    except Exception as e:
        flash(f"Error generating PDF: {e}", "danger")
        return redirect(url_for('generate_report', filename=filename))

@app.route('/download_cleaned_file/<filename>')
def download_cleaned_file(filename):
    cleaned_file_path = os.path.join(app.config['CLEANED_FOLDER'], filename)
    if os.path.exists(cleaned_file_path):
        return send_file(cleaned_file_path, as_attachment=True)
    else:
        flash(f"File {filename} not found.", "danger")
        return redirect(url_for('home'))

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
        hashed_password = generate_password_hash(password).decode('utf-8')
        user = User(name=name, email=email, company_name=company_name, warehouse_type=warehouse_type, password=hashed_password, workspace_name=workspace_name)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# 📈 Predict Stock Demand Route
@app.route('/predict_stock_demand/<filename>')
def predict_stock_demand(filename):
    cleaned_file_path = os.path.join(app.config['CLEANED_FOLDER'], filename)
    if not os.path.exists(cleaned_file_path):
        flash(f"File {filename} not found.", "danger")
        return redirect(url_for('home'))

    try:
        df = pd.read_csv(cleaned_file_path) if filename.endswith('.csv') else pd.read_excel(cleaned_file_path)
        if 'Total Sales Volume' not in df.columns:
            flash("The file must contain 'Total Sales Volume' column.", "danger")
            return redirect(url_for('summary', filename=filename))

        # Prepare data for Linear Regression
        X = np.arange(len(df)).reshape(-1, 1)
        y = df['Total Sales Volume'].values
        model = LinearRegression()
        model.fit(X, y)
        future_demand = model.predict(np.array([[len(df) + 1]]))[0]

        return render_template('predict_stock_demand.html', future_demand=future_demand)

    except Exception as e:
        flash(f"Error predicting stock demand: {e}", "danger")
        return redirect(url_for('home'))

# 📦 Recommend Stock Level Route
@app.route('/recommend_stock/<filename>')
def recommend_stock(filename):
    cleaned_file_path = os.path.join(app.config['CLEANED_FOLDER'], filename)
    if not os.path.exists(cleaned_file_path):
        flash(f"File {filename} not found.", "danger")
        return redirect(url_for('home'))

    try:
        df = pd.read_csv(cleaned_file_path) if filename.endswith('.csv') else pd.read_excel(cleaned_file_path)
        if 'Product Name' not in df.columns or 'Quantity Available' not in df.columns or 'Reorder_Level' not in df.columns or 'Total Sales Volume' not in df.columns:
            flash("The file must contain 'Product Name', 'Quantity Available', 'Reorder_Level', and 'Total Sales Volume' columns.", "danger")
            return redirect(url_for('summary', filename=filename))

        # Prepare data for Linear Regression for each product
        future_demand = {}
        for product in df['Product Name'].unique():
            product_df = df[df['Product Name'] == product]
            if len(product_df) < 2:  # Ensure there is enough data to train the model
                future_demand[product] = "Insufficient data"
                continue
            X = np.arange(len(product_df)).reshape(-1, 1)
            y = product_df['Total Sales Volume'].values
            model = LinearRegression()
            model.fit(X, y)
            prediction = model.predict(np.array([[len(product_df) + 1]]))[0]
            future_demand[product] = max(0, prediction)  # Ensure the prediction is not negative

        # Generate stock recommendations
        df['Future Demand'] = df['Product Name'].map(future_demand)
        recommendations = df[df['Quantity Available'] < df['Reorder_Level']]

        return render_template('recommend_stock.html', recommendations=recommendations.to_html(index=False), future_demand=future_demand)

    except Exception as e:
        flash(f"Error recommending stock levels: {e}", "danger")
        return redirect(url_for('home'))


# 📊 Visualize Trends Route
@app.route('/visualize_trends/<filename>')
def visualize_trends(filename):
    cleaned_file_path = os.path.join(app.config['CLEANED_FOLDER'], filename)
    if not os.path.exists(cleaned_file_path):
        flash(f"File {filename} not found.", "danger")
        return redirect(url_for('home'))

    try:
        df = pd.read_csv(cleaned_file_path) if filename.endswith('.csv') else pd.read_excel(cleaned_file_path)
        if 'Total Sales Volume' not in df.columns:
            flash("The file must contain 'Total Sales Volume' column.", "danger")
            return redirect(url_for('summary', filename=filename))

        plt.figure(figsize=(12, 8))
        sns.lineplot(data=df, x=np.arange(len(df)), y='Total Sales Volume')
        plt.title('Sales Trend')
        plt.xlabel('Time')
        plt.ylabel('Total Sales Volume')
        trend_chart_path = os.path.join(app.config['CHARTS_FOLDER'], f'trend_{filename}.png')
        plt.savefig(trend_chart_path)
        plt.close()

        return render_template('visualize_trends.html', trend_chart_url=f'trend_{filename}.png')

    except Exception as e:
        flash(f"Error visualizing trends: {e}", "danger")
        return redirect(url_for('home'))

@app.route('/test_login_url')
def test_login_url():
    return url_for('login')

if __name__ == '__main__':
    app.run(debug=True)