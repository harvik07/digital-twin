import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename

# Use the Agg backend for Matplotlib (prevents GUI errors)
import matplotlib
matplotlib.use('Agg')

app = Flask(__name__)

# Define folders
UPLOAD_FOLDER = "uploads"
CLEANED_FOLDER = "cleaned_files"
CHARTS_FOLDER = "static/charts"

# Ensure folders exist
for folder in [UPLOAD_FOLDER, CLEANED_FOLDER, CHARTS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CLEANED_FOLDER'] = CLEANED_FOLDER
app.config['CHARTS_FOLDER'] = CHARTS_FOLDER
app.secret_key = 'your_secret_key'  # Flash messages

# 🏠 Home - File Upload & Cleaning
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        file = request.files['file']
        if file.filename == '':
            flash("No file selected!", "danger")
            return redirect(request.url)

        file_ext = file.filename.rsplit('.', 1)[1].lower()
        if file_ext not in ['csv', 'xlsx']:
            flash("Invalid file format! Please upload a CSV or Excel file.", "danger")
            return redirect(request.url)

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Load file
        df = pd.read_csv(file_path) if file_ext == 'csv' else pd.read_excel(file_path)

        # Data Cleaning (Remove duplicates, fill missing values)
        df = df.drop_duplicates().fillna(0)

        # Save cleaned file
        cleaned_filename = f"cleaned_{file.filename}"
        cleaned_path = os.path.join(app.config['CLEANED_FOLDER'], cleaned_filename)
        df.to_csv(cleaned_path, index=False) if file_ext == 'csv' else df.to_excel(cleaned_path, index=False)

        # Generate summary statistics
        summary = df.describe().to_html()

        # Redirect to summary page
        return render_template("summary.html", summary=summary, cleaned_filename=cleaned_filename)

    return render_template("index.html")

# 📊 Summary Page - Show Summary & Download Option
@app.route('/summary/<filename>')
def summary(filename):
    cleaned_file_path = os.path.join(app.config['CLEANED_FOLDER'], filename)
    try:
        df = pd.read_csv(cleaned_file_path) if filename.endswith('.csv') else pd.read_excel(cleaned_file_path)
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
        df = pd.read_csv(cleaned_file_path) if filename.endswith('.csv') else pd.read_excel(cleaned_file_path)
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

if __name__ == '__main__':
    app.run(debug=True)
