import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
import pdfkit

# Use the Agg backend for Matplotlib (prevents GUI errors)
import matplotlib
matplotlib.use('Agg')

app = Flask(__name__)

# Define folders
UPLOAD_FOLDER = "uploads"
CLEANED_FOLDER = "cleaned_files"
CHARTS_FOLDER = "static/charts"
PDF_FOLDER = "static/pdf"

# Ensure folders exist
for folder in [UPLOAD_FOLDER, CLEANED_FOLDER, CHARTS_FOLDER, PDF_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CLEANED_FOLDER'] = CLEANED_FOLDER
app.config['CHARTS_FOLDER'] = CHARTS_FOLDER
app.config['PDF_FOLDER'] = PDF_FOLDER
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

        # Data Cleaning (Remove duplicates, drop NaN values, fill missing values)
        df = df.drop_duplicates().dropna().fillna(0)

        # Save cleaned file
        cleaned_filename = "cleaned_warehouse.csv"
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
        df = pd.read_csv(cleaned_file_path) if filename.endswith('.csv') else pd.read_excel(cleaned_file_path)

        # Ensure required columns exist
        required_columns = [
            'Purchase_Price', 'Selling_Price', 'Total Sales Volume', 'Total Revenue',
            'Profit per Unit', 'Profit Margin (%)', 'Stock Turnover Rate', 'Storage Space (cubic ft)', 'Quantity Available'
        ]
        if not all(column in df.columns for column in required_columns):
            flash("Your Excel file must contain these columns: Purchase_Price, Selling_Price, Total Sales Volume, Total Revenue, Profit per Unit, Profit Margin (%), Stock Turnover Rate, Storage Space (cubic ft), Quantity Available.", "danger")
            return redirect(url_for('summary', filename=filename))

        # Calculate insights
        most_stocked_product = df.loc[df['Quantity Available'].idxmax()]['Product Name']
        slow_moving_products = df[df['Stock Turnover Rate'] < 1]['Product Name'].tolist()
        total_stock = df['Quantity Available'].sum()
        most_valuable_product = df.loc[df['Total Revenue'].idxmax()]['Product Name']
        least_valuable_product = df.loc[df['Total Revenue'].idxmin()]['Product Name']
        most_profitable_products = df[df['Profit Margin (%)'] == df['Profit Margin (%)'].max()]['Product Name'].tolist()
        least_profitable_products = df[df['Profit Margin (%)'] == df['Profit Margin (%)'].min()]['Product Name'].tolist()
        best_selling_product = df.loc[df['Total Sales Volume'].idxmax()]['Product Name']
        worst_selling_product = df.loc[df['Total Sales Volume'].idxmin()]['Product Name']

        # Warehouse density analysis
        if request.method == 'POST':
            total_capacity = float(request.form.get('total_capacity'))
            used_space = df['Storage Space (cubic ft)'].sum()
            available_space = total_capacity - used_space
            warehouse_density_message = "Warehouse has sufficient space." if available_space > 0 else "Warning: Warehouse is almost full."

            return render_template("report.html", 
                                   most_stocked_product=most_stocked_product,
                                   slow_moving_products=slow_moving_products,
                                   total_stock=total_stock,
                                   most_valuable_product=most_valuable_product,
                                   least_valuable_product=least_valuable_product,
                                   most_profitable_products=most_profitable_products,
                                   least_profitable_products=least_profitable_products,
                                   best_selling_product=best_selling_product,
                                   worst_selling_product=worst_selling_product,
                                   warehouse_density_message=warehouse_density_message,
                                   available_space=available_space)

        return render_template("report.html", 
                               most_stocked_product=most_stocked_product,
                               slow_moving_products=slow_moving_products,
                               total_stock=total_stock,
                               most_valuable_product=most_valuable_product,
                               least_valuable_product=least_valuable_product,
                               most_profitable_products=most_profitable_products,
                               least_profitable_products=least_profitable_products,
                               best_selling_product=best_selling_product,
                               worst_selling_product=worst_selling_product)

    except Exception as e:
        flash(f"Error generating report: {e}", "danger")
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

if __name__ == '__main__':
    app.run(debug=True)