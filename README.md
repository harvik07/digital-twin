🏭 Digital Twin for Intelligent Warehousing


An interactive, web-based digital twin system designed to streamline warehouse management through real-time visualizations, predictive analytics, and automated reporting. This system bridges physical inventory with intelligent digital insights, providing decision-makers with a powerful tool for modern supply chain optimization.

🚀 Features
🔐 Secure Authentication: Login system with session management.

📥 CSV Upload: Upload warehouse inventory data (SKU, quantity, zones, etc.).

🧹 Automated Preprocessing: Cleans, structures, and stores uploaded data.

🗺 2D Warehouse Layout: Real-time visual representation of the warehouse using dynamic grid-based rendering.

🔍 Advanced Search & Filter: Locate inventory by SKU, category, zone, stock level, and more.

📊 Interactive Dashboards: Visual insights with charts, zone-wise reports, and inventory summaries.

📈 Predictive Analytics: Linear regression models forecast stock depletion and restocking needs.

🧾 Custom Reports: Auto-generated reports (PDF/Excel) for audits, stock summaries, and AI-driven predictions.

⚙️ Modular & Scalable Architecture: Built with a layered backend and responsive frontend.

🧠 Technology Stack
Frontend: CSS

Backend: Python Flask

Database: SQLite / PostgreSQL

ML Model: Linear Regression (Scikit-learn)

Visualization: HTML5 Canvas / SVG, D3.js (optional)

Exporting: Pandas + Jinja2 for PDF/Excel generation

🖼 System Architecture

User Interface Layer – Secure login, CSV uploader, visualization panel.

Preprocessing Layer – Cleans and validates uploaded data.

Analytics Engine – Maps zones, calculates KPIs, and feeds visualization tools.

Visualization Layer – Interactive 2D layout with hover/click tooltips and color-coded zones.

Prediction Module – Time-series based stock forecasting with alerts.

Reporting Module – Generates downloadable summaries, exceptions, and AI recommendations.

This project is licensed under the MIT License.
