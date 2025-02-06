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
   cd your-repository-name
