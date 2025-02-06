# Candidate Assessment & Petition Management Application

This repository contains a Flask-based web application designed to streamline the process of candidate assessment for immigration petitions (e.g., EB1A, EB2, EB2_NIW, EB3). The application handles user authentication, candidate data collection, automated scoring and analysis, file uploads (including resumes, financial proofs, exhibits, etc.), petition detail management, and even content generation via Deepseek’s AI API.

Table of Contents

Features
Tech Stack
Installation
Configuration
Usage
User Authentication
Candidate Submission & Assessment
File Uploads & Petition Management
Reports & Analysis
API Endpoints
Project Structure
Logging & Debugging
License
Features

User Authentication:
Secure login with a two-step verification process (password and one-time code sent via email).
Candidate Submission:
A multi-part form allows for detailed submission of candidate data including personal information, education, work experience, achievements, publications, skills, and more.
Automated Candidate Assessment:
Based on the selected visa category (EB1A, EB2, EB2_NIW, EB3), the application automatically scores and assesses each candidate using weighted criteria.
File Upload & Management:
Upload resumes, financial proofs, exhibits, and other documents into structured candidate folders. Files can be renamed via an API endpoint.
Petition Generation & PDF Download:
Generate petitions and cover letters; export candidate petitions as PDF documents.
Reports & Dashboards:
Visual reports provide insights on candidate scores, work experience distribution, education, and more.
Content Generation with AI:
Use Deepseek’s API (via an OpenAI-like interface) to generate custom content such as cover letters, proposed endeavor introductions, and more.
Tech Stack

Backend: Python, Flask
Frontend: HTML, Jinja2 templates, JavaScript (for some interactive endpoints)
Database: JSON file storage (for candidate and user data)
APIs & Integrations:
Stripe & Paystack: For payment processing
SendGrid: For sending verification emails
pdfkit: For PDF generation
Deepseek API: For AI-assisted content generation
Others: Werkzeug (for security and file uploads), logging, uuid, and more.
Installation

Clone the Repository:
git clone https://github.com/yourusername/your-repository-name.git
cd your-repository-name
Create a Virtual Environment and Install Dependencies:
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
Ensure Required Folders Exist:
The application automatically creates necessary folders (such as uploads, data, and credential folders) if they are missing.
Configuration

Create a configuration file (or update your existing one) using the Config class provided in config.py. The configuration should include:

Secret Keys:
SECRET_KEY, API keys for SendGrid, Deepseek, Stripe, Paystack, etc.
Upload & Data Directories:
Paths for UPLOAD_FOLDER, DATA_FOLDER, and the candidates file path (CANDIDATES_FILE).
Allowed File Extensions:
List of file extensions permitted for upload (e.g., ['pdf', 'docx', 'png', 'jpg']).
Example snippet from your config.py:

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_default_secret_key')
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    DATA_FOLDER = os.path.join(os.getcwd(), 'data')
    CANDIDATES_FILE = os.path.join(DATA_FOLDER, 'candidates.json')
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg'}
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
    PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY')
    PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')
    PAYSTACK_BASE_URL = os.environ.get('PAYSTACK_BASE_URL')
    DEEPSEEK_API = os.environ.get('DEEPSEEK_API_KEY')
    # PDF_CONFIG can be set to the configuration required by pdfkit
    PDF_CONFIG = {
        'wkhtmltopdf': os.environ.get('WKHTMLTOPDF_PATH', '/usr/local/bin/wkhtmltopdf')
    }
Usage

User Authentication
Login:
Visit /login and provide your username and password. Upon successful authentication, a verification code will be emailed to you.
Verification:
Enter the received code at /verify to complete the login process.
Profile Update & Logout:
Update your profile details at /update-profile and log out via /logout.
Candidate Submission & Assessment
Submit Candidate:
Access the candidate submission form at /submit. Fill in the candidate’s personal, educational, professional, and achievement details. On submission, the candidate’s data is saved and automatically scored based on the visa category.
View Candidates:
Navigate to /candidates to view the list of candidates. Use filters (e.g., by assessment status) if needed.
Candidate Detail & Comparison:
View detailed information at /candidate/<candidate_id>.
Compare multiple candidates using /compare.
File Uploads & Petition Management
Uploading Files:
Use the /petition route to upload additional files (such as exhibits, resumes, or financial proofs) to a candidate’s folder.
Renaming Files:
An API endpoint /api/candidate/<candidate_id>/rename_file is available for renaming files in candidate records.
Download Petition PDF:
Generate and download a petition PDF at /candidate/<candidate_id>/pdf.
Reports & Analysis
Dashboard:
The /reports route displays various statistics and charts (experience distribution, education counts, top companies, scatter plots, etc.).
Candidate Analysis:
The /candidate_analysis endpoint provides a detailed assessment, listing strengths, weaknesses, and recommendations based on candidate data and visa category criteria.
API Endpoints
Some of the key API endpoints include:

File Operations:
GET /api/candidate/<candidate_id>/files – Retrieve files by folder type.
POST /api/candidate/<candidate_id>/rename_file – Rename a candidate file.
Petition Details:
POST/GET /api/candidate/<candidate_id>/petition_details – Save or retrieve petition details.
AI Content Generation:
POST /api/genai/generate – Generate custom content (e.g., cover letters) using the Deepseek API.
POST /api/get_example – Retrieve example prompts for content generation.
Project Structure

your-repository-name/
├── app.py                # Main Flask application
├── config.py             # Configuration settings
├── Credential/           # Contains user credential files (e.g., login.json)
├── data/                 # Contains candidate data (candidates.json) and reference JSON files
├── static/               # Static files (CSS, JS, images, profile pictures, etc.)
├── templates/            # Jinja2 templates for rendering HTML pages
├── uploads/              # Folder for uploaded candidate files and documents
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation (this file)
Logging & Debugging

Logging:
The application uses Python’s built-in logging module. By default, logging is set to DEBUG level, which helps trace the flow and catch errors. Adjust the logging level in app.py if necessary.
Error Handling:
The application includes error handling for common issues (e.g., invalid file uploads, missing candidate records) and returns appropriate HTTP status codes for API endpoints.
License

Include your license information here. For example:

MIT License
