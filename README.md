# Candidate Assessment & Petition Management Application

This repository contains a Flask-based web application designed to streamline candidate assessment for immigration petitions (e.g., EB1A, EB2, EB2_NIW, EB3). The application handles user authentication, candidate data collection, automated scoring and analysis, file uploads (including resumes, financial proofs, exhibits, etc.), petition detail management, and even AI-powered content generation via Deepseek.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [User Authentication](#user-authentication)
  - [Candidate Submission & Assessment](#candidate-submission--assessment)
  - [File Uploads & Petition Management](#file-uploads--petition-management)
  - [Reports & Analysis](#reports--analysis)
  - [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Logging & Debugging](#logging--debugging)
- [License](#license)

---

## Features

- **User Authentication:**  
  Secure login with a two-step verification process (password plus one-time code sent via email).

- **Candidate Submission:**  
  A multi-part form allows for detailed input including personal information, education, work experience, achievements, publications, skills, and more.

- **Automated Candidate Assessment:**  
  The system automatically scores and assesses candidates based on the selected visa category using weighted criteria.

- **File Upload & Management:**  
  Upload and manage candidate files such as resumes, financial proofs, exhibits, etc. Files are organized into structured candidate folders and can be renamed via API.

- **Petition Generation & PDF Download:**  
  Generate petitions and cover letters; export candidate petitions as PDF documents using pdfkit.

- **Reports & Dashboards:**  
  Visual reports with charts for candidate scores, work experience distribution, education levels, top companies, and more.

- **AI Content Generation:**  
  Utilize Deepseek’s API (integrated via an OpenAI-like client) to generate custom content such as cover letters, proposed endeavor introductions, and more.

---

## Tech Stack

- **Backend:** Python, Flask  
- **Frontend:** HTML, Jinja2 templates, JavaScript  
- **Data Storage:** JSON file storage for candidate and user data  
- **APIs & Integrations:**  
  - **Stripe & Paystack** for payment processing  
  - **SendGrid** for email notifications  
  - **pdfkit** for PDF generation  
  - **Deepseek API** for AI-assisted content generation  
- **Others:** Werkzeug (for file uploads and security), logging, uuid, hashlib, etc.

---

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/your-repository-name.git

2. **Create a Virtual Environment and Install Dependencies:
      python3 -m venv venv
      source venv/bin/activate  # On Windows use: venv\Scripts\activate
      pip install -r requirements.txt

## Ensure Required Folders Exist:
The application automatically creates necessary folders (e.g., uploads, data, Credential) if they do not exist.

## Configuration

Configure the application using the Config class in config.py. Ensure the following settings are defined:

## Secret Keys & API Keys:
SECRET_KEY, SENDGRID_API_KEY, DEEPSEEK_API, STRIPE_SECRET_KEY, STRIPE_PUBLIC_KEY, PAYSTACK_PUBLIC_KEY, PAYSTACK_SECRET_KEY, etc.

File & Data Paths:
Paths for UPLOAD_FOLDER, DATA_FOLDER, and the candidates file (CANDIDATES_FILE).

Allowed File Extensions:
Define a set of allowed file extensions (e.g., {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg'}).

## Example configuration snippet:

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
        PDF_CONFIG = {
            'wkhtmltopdf': os.environ.get('WKHTMLTOPDF_PATH', '/usr/local/bin/wkhtmltopdf')
        }
### Usage

    #### User Authentication
    Login:
    Visit /login and provide your username and password. Upon success, a verification code is sent to your registered email.
    
    Verification:
    Enter the received code at /verify to complete your login.
    
    Profile Update & Logout:
    Update profile details via /update-profile and log out using /logout.
    
    #### Candidate Submission & Assessment
    Submit Candidate:
    Access the candidate submission form at /submit to provide detailed candidate data. Upon submission, the candidate is automatically scored based on the selected visa category.
    
    View Candidates:
    Navigate to /candidates to see the list of candidates. Filtering by assessment status is available.
    
    Candidate Detail & Comparison:
    View detailed candidate profiles at /candidate/<candidate_id>.
    Compare multiple candidates at /compare.
    
    #### File Uploads & Petition Management
    
    Uploading Files:
    Use the /petition route to upload additional files (e.g., exhibits, resumes, financial proofs) into the candidate’s folder.
    
    Renaming Files:
    Utilize the API endpoint /api/candidate/<candidate_id>/rename_file to rename candidate files.
    
    Download Petition PDF:
    Generate and download a petition PDF at /candidate/<candidate_id>/pdf.
    
    #### Reports & Analysis
    
    Dashboard:
    The /reports route provides various statistics and charts including experience distribution, education counts, top companies, and more.
    
    Candidate Analysis:
    Use /candidate_analysis to get a detailed report listing strengths, weaknesses, and recommendations for each candidate.
    
    #### API Endpoints
    File Operations:
    GET /api/candidate/<candidate_id>/files – Retrieve files by folder type.
    POST /api/candidate/<candidate_id>/rename_file – Rename a candidate file.
    
    Petition Details:
    POST/GET /api/candidate/<candidate_id>/petition_details – Save or retrieve petition details.
    
    AI Content Generation:
    POST /api/genai/generate – Generate custom content (e.g., cover letters) using the Deepseek API.
    POST /api/get_example – Retrieve example prompts for content generation.


## Project Structure

    your-repository-name/
    ├── app.py                # Main Flask application
    ├── config.py             # Configuration settings
    ├── Credential/           # User credential files (e.g., login.json)
    ├── data/                 # Candidate data (candidates.json) and reference files
    ├── static/               # Static assets (CSS, JS, images, profile pictures, etc.)
    ├── templates/            # Jinja2 HTML templates
    ├── uploads/              # Uploaded candidate files and documents
    ├── requirements.txt      # Python dependencies
    └── README.md             # Project documentation (this file)

## Logging & Debugging

Logging:
The application uses Python’s built-in logging module (default level is DEBUG). Adjust the logging level in app.py if needed.
Error Handling:
The application provides error handling for issues such as invalid file uploads and missing candidate records, returning appropriate HTTP status codes for API responses.


# License

This project is licensed under the MIT License.
