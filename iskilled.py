import os
import json
import uuid
import hashlib
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify, abort
from werkzeug.utils import secure_filename
import pdfkit
import random
import string
from datetime import datetime, timedelta, timezone
import pytz
import requests
from functools import wraps
import stripe
import paystackapi
#from paystackapi.transaction import Transaction as PaystackTransaction
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To
from config import Config
import logging
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config.from_object(Config)
app.config["UPLOAD_FOLDER"] = Config.UPLOAD_FOLDER
app.config['DEEPSEEK_API_KEY'] = Config.DEEPSEEK_API
client = OpenAI(api_key=app.config['DEEPSEEK_API_KEY'], base_url="https://api.deepseek.com")
app.secret_key = app.config['SECRET_KEY']
stripe.api_key = app.config['STRIPE_SECRET_KEY']
stripe_public_key = app.config['STRIPE_PUBLIC_KEY']
paystack_public_key = app.config['PAYSTACK_PUBLIC_KEY']
PAYSTACK_SECRET_KEY = app.config['PAYSTACK_SECRET_KEY']
PAYSTACK_BASE_URL = app.config['PAYSTACK_BASE_URL']

# Ensure that the uploads folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Construct the full path to the login.json file
file_path = os.path.join('Credential', 'login.json')

# Load the mock user database
with open(file_path, 'r') as file:
    USERS = json.load(file)

    # Helper function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function

# Helper function to send email
def send_email_html(sendto_emails, send_from_email, subject, message, content_type='plain'):
    try:
        if not isinstance(sendto_emails, list):
            sendto_emails = [sendto_emails]

        to_emails = [To(email) for email in sendto_emails]

        if content_type == 'html':
            email = Mail(
                from_email=send_from_email,
                to_emails=to_emails,
                subject=subject,
                html_content=message
            )
        else:
            email = Mail(
                from_email=send_from_email,
                to_emails=to_emails,
                subject=subject,
                plain_text_content=message
            )

        sg = SendGridAPIClient(app.config['SENDGRID_API_KEY'])
        response = sg.send(email)

        if response.status_code in [200, 202]:
            print(f"Email sent successfully to {sendto_emails}")
            return {'success': 'Email sent successfully'}, 200
        else:
            print(f"Failed to send email. Status Code: {response.status_code}, Body: {response.body}")
            return {'error': 'Failed to send email'}, response.status_code

    except Exception as e:
        print("Exception occurred while sending email:", e)
        return {'error': str(e)}, 500

# Login Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Find user by username
        user = next((u for u in USERS if u['username'] == username), None)
        print(user)
        if user and hash_password(password) == user['password']:
            # Generate verification code
            verification_code = ''.join(random.choices(string.digits, k=6))
            session['verification_code'] = verification_code

            # Store timezone-aware datetime in UTC
            session['verification_expiry'] = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
            # Store user info in session
            # Store user info in session
            session['user_id'] = user['username']
            session['user_name'] = user.get('name')
            session['email'] = user.get('email')
            session['phone'] = user.get('phone')
            session['profile_picture'] = user.get('profile_picture', 'static/profile_pictures/default.png')  # Default profile picture fallback
            session['role'] = user['role']

            # Send verification email
            send_email_html(
                sendto_emails=user['email'],
                send_from_email='admin@suscalableconsulting.com',
                subject='Your Verification Code',
                message=f'<p>Your verification code is: <strong>{verification_code}</strong></p>',
                content_type='html'
            )

            return redirect(url_for('verify'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        code = request.form['code']
        if 'verification_code' in session and session['verification_code'] == code:
            # Parse the stored ISO-formatted datetime back into a datetime object
            expiry_time = datetime.fromisoformat(session['verification_expiry'])

            # Ensure both are timezone-aware
            if datetime.now(timezone.utc) <= expiry_time:
                # Verification successful
                session.pop('verification_code', None)
                session.pop('verification_expiry', None)
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            else:
                # Code expired
                flash('Verification code expired. Please log in again.', 'danger')
                return redirect(url_for('login'))
        else:
            # Invalid code
            flash('Invalid verification code.', 'danger')

    return render_template('verify.html', countdown=60)


def save_profile_picture(profile_picture):
    # Ensure the upload folder exists
    upload_folder = os.path.join(app.root_path, 'static', 'profile_pictures')
    os.makedirs(upload_folder, exist_ok=True)

    # Secure the filename and save the picture
    filename = secure_filename(profile_picture.filename)
    picture_path = os.path.join(upload_folder, filename)
    profile_picture.save(picture_path)

    # Return the relative path for serving the image later
    return f'static/profile_pictures/{filename}'

def save_users(users):
    file_path = os.path.join(app.root_path, 'credential', 'login.json')  # Adjust the path if necessary
    with open(file_path, 'w') as file:
        json.dump(users, file, indent=4)

def get_user_by_username(username):
    return next((user for user in USERS if user['username'] == username), None)

@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    username = request.form.get('username')
    password = request.form.get('password')  # Only update if provided
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    profile_picture = request.files.get('profile_picture')

    # Fetch user and update fields
    user = get_user_by_username(session['user_id'])  # Fetch user by session ID
    if user:
        user['username'] = username
        user['name'] = name
        user['email'] = email
        user['phone'] = phone

        if password:
            user['password'] = hash_password(password)  # Update only if provided

        if profile_picture:
            picture_path = save_profile_picture(profile_picture)  # Save and update picture path
            user['profile_picture'] = picture_path

        # Save updates to the database or file
        save_users(USERS)

        # Update session
        session['user_name'] = username
        session['name'] = name
        session['email'] = email
        session['phone'] = phone
        if profile_picture:
            session['profile_picture'] = picture_path

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('index'))

    flash('Failed to update profile.', 'danger')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    
    # Flash a message to confirm logout
    flash('You have been logged out successfully.', 'info')
    
    # Redirect to the login page
    return redirect(url_for('login'))


# -----------------------------
# Helper Functions for Candidate Data
# -----------------------------
def load_candidates():
    path = app.config["CANDIDATES_FILE"]
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_candidates(candidates):
    path = app.config["CANDIDATES_FILE"]
    with open(path, "w") as f:
        json.dump(candidates, f, indent=4)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

# Load reference data from JSON (used for quality matching)
def load_reference_data(filename):
    path = os.path.join("data", filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

reference_data = load_reference_data("reference_data.json")

# -----------------------------
# Quality Matching Helper
# -----------------------------
def quality_match_score(candidate_str, reference_list, max_score=5):
    """
    Return max_score if any reference term appears in candidate_str (case-insensitive).
    Otherwise, return 1 if candidate_str is provided, or 0 if not.
    """
    if not candidate_str:
        return 0
    candidate_str = candidate_str.lower()
    for ref in reference_list:
        if ref.lower() in candidate_str:
            return max_score
    return 1  # Minimal score when provided but no match

# -----------------------------
# Scoring Functions by Visa Category
# (Using only keys we actually save from the form)
# -----------------------------

def degree_bonus(candidate):
    """
    Compute bonus points based on the candidate's degree level using the first element
    from the 'education_highest' array.
    
    Bonus values (example):
      - PhD/Doctorate: +20
      - Master's (MBA, etc.): +10
      - Bachelor's: +5
    """
    bonus = 0
    edu_list = candidate.get("education_highest", [])
    if edu_list and len(edu_list) > 0:
        edu = edu_list[0].strip().lower()
        if "phd" in edu or "doctor" in edu or "ph.d" in edu or "ph.d." in edu or "doctoral" in edu:
            bonus = 20
        elif "master" in edu or "mba" in edu or "ms" in edu or "mtech" in edu or "masters" in edu or "msc" in edu:
            bonus = 10
        elif "bachelor" in edu or "ba " in edu or "bsc " in edu or "beng" in edu or "b.eng" in edu or "hnd" in edu:
            bonus = 5
    return bonus

def score_candidate_eb1a(candidate, ref):
    """
    EB1A (Extraordinary Ability)
    """
    final_score = 0
    primary_criteria_met = 0  # Count for Awards, Published Work, Original Contributions

    # 1. Awards and Recognitions
    weight = 30
    awards = candidate.get("achievement_award", [])
    availability = 1 if awards else 0
    quantity = min(len(awards), 5) if awards else 0
    score_awards = weight * availability * (quantity / 5)
    final_score += score_awards
    if awards and score_awards >= 0.8 * weight:  # if near perfect for this criterion
        primary_criteria_met += 1

    # 2. Published Work
    weight = 30
    pubs = candidate.get("publication_title", [])
    availability = 1 if pubs else 0
    quantity = min(len(pubs), 5) if pubs else 0
    score_pubs = weight * availability * (quantity / 5)
    final_score += score_pubs
    if pubs and score_pubs >= 0.8 * weight:
        primary_criteria_met += 1

    # 3. Exclusive Memberships
    weight = 10
    memberships = candidate.get("achievement_membership", [])
    availability = 1 if memberships else 0
    quantity = min(len(memberships), 5) if memberships else 0
    qual = quality_match_score(" ".join(memberships), ref.get("top_associations", [])) if memberships else 0
    final_score += weight * availability * (quantity / 5) * (qual / 5)

    # 4. Judging Work
    weight = 30
    judging = candidate.get("extra_judging", False)
    availability = 1 if judging else 0
    quantity = min(candidate.get("extra_judging", 3), 5) if judging else 0
    final_score += weight * availability * (quantity / 5)

    # 5. Original Contributions
    weight = 30
    contributions = candidate.get("extra_contributions", [])
    availability = 1 if contributions else 0
    quantity = min(len(contributions), 5) if contributions else 0
    score_contrib = weight * availability * (quantity / 5)
    final_score += score_contrib
    if contributions and score_contrib >= 0.8 * weight:
        primary_criteria_met += 1

    # 6. High Salary/Remuneration
    weight = 10
    high_salary = candidate.get("high_salary", False)
    availability = 1 if high_salary else 0
    final_score += weight * availability

    # Bonus for Degree Level and Extra Higher-Cadre Attributes:
    bonus = degree_bonus(candidate)
    # 1. Patents
    if candidate.get("achievement_patents", []):
        bonus += len(candidate["achievement_patents"]) * 10  # 10 points per patent

    # 2. Leadership Roles
    if candidate.get("achievement_leadership", []):
        bonus += len(candidate["achievement_leadership"]) * 1.5  # 1.5 points per leadership role

    # 3. Licenses and Certifications
    if candidate.get("license_name", []):
        bonus += len(candidate["license_name"]) * 2  # 2 points per license/certification

    # 4. Work Experience at Top Companies
    top_companies = ref.get("top_companies", [])
    work_experience = candidate.get("experience_employer", [])
    bonus += sum(5 for company in work_experience if company in top_companies)  # 5 points per top company

    # 5. Publications in Top Journals
    publications = candidate.get("publication_publisher", [])
    top_journals = ref.get("top_journals", [])
    bonus += sum(3 for pub in publications if any(journal in pub for journal in top_journals))  # 3 points per top journal

    # 6. Projects with Significant Impact
    if candidate.get("project_impact", []):
        bonus += len(candidate["project_impact"]) * 2  # 2 points per impactful project
    final_score += bonus

    # Cap final score to 100 if it exceeds 100
    final_score = min(final_score, 100)

    candidate["score"] = round(final_score, 2)
    candidate["assessment"] = "High Skilled Candidate" if final_score >= 70 else "Candidate needs further review"
    return candidate

def score_candidate_eb2_niw(candidate, ref):
    """
    EB2 NIW (National Interest Waiver)
    """
    final_score = 0

    # 1. Educational Background (30%)
    weight = 30
    edu = candidate.get("education_university", [])[0].strip() if candidate.get("education_university") else ""
    if edu:
        edu_quality = quality_match_score(edu, ref.get("top_universities", []))
        final_score += weight  # Base score for having an educational background
        final_score += edu_quality  # Directly add the quality score as a bonus

    # 2. Work Experience (20%)
    weight = 20
    work = candidate.get("work_experience", 0)
    quantity = min(work, 5) if work else 0
    final_score += weight * (quantity / 5)

    # 3. Published Work (30%)
    weight = 30
    pubs = candidate.get("publication_title", [])
    availability = 1 if pubs else 0
    quantity = min(len(pubs), 5) if pubs else 0
    final_score += weight * availability * (quantity / 5)

    # 4. Recommendation Letters (20%)
    weight = 20
    recs = candidate.get("recommendation_letters", [])
    availability = 1 if recs else 0
    quantity = min(len(recs), 5) if recs else 0
    final_score += weight * availability * (quantity / 5)

    # 3. Professional Memberships (extra 5)
    weight = 5
    memberships = candidate.get("achievement_membership", []) + candidate.get("extra_memberships", [])
    availability = 1 if memberships else 0
    quantity = min(len(memberships), 5) if memberships else 0  # Maximum of 5 memberships considered
    quality_memberships = quality_match_score(" ".join(memberships), ref.get("top_associations", [])) if memberships else 0
    final_score += weight * availability * (quantity / 5)  # Base score for membership count
    final_score += quality_memberships  # Add direct bonus for quality

    # 4. Skills and Certifications (extra 5)
    weight = 5
    skills = candidate.get("technical_skills", "") + " " + candidate.get("core_competencies", "")
    certs = candidate.get("education_certifications", [])
    combined = skills + " " + " ".join(certs)
    availability = 1 if combined.strip() else 0
    quality_skills = quality_match_score(combined, ref.get("top_certifications", [])) if combined.strip() else 0
    quantity = min(candidate.get("skills_quantity", 3), 5)  # Maximum of 5 skills considered
    final_score += weight * availability * (quantity / 5)  # Base score for skills count
    final_score += quality_skills  # Add direct bonus for quality

    # Bonus for Degree Level and Extra Higher-Cadre Attributes:
    bonus = degree_bonus(candidate)
    # 1. Judging Experience
    if candidate.get("extra_judging", False):
        bonus += 3

    # 2. Original Contributions
    if candidate.get("extra_contributions", []):
        bonus += 5

    # 4. Patents
    if candidate.get("achievement_patents", []):
        bonus += len(candidate["achievement_patents"]) * 10  # 10 points per patent

    # 5. Leadership Roles
    if candidate.get("achievement_leadership", []):
        bonus += len(candidate["achievement_leadership"]) * 1.5  # 1.5 points per leadership role

    # 6. Licenses and Certifications
    if candidate.get("license_name", []):
        bonus += len(candidate["license_name"]) * 2  # 2 points per license/certification

    # 7. Work Experience at Top Companies
    top_companies = ref.get("top_companies", [])
    work_experience = candidate.get("experience_employer", [])
    bonus += sum(5 for company in work_experience if company in top_companies)  # 5 points per top company

    # 8. Publications in Top Journals
    publications = candidate.get("publication_publisher", [])
    top_journals = ref.get("top_journals", [])
    bonus += sum(3 for pub in publications if any(journal in pub for journal in top_journals))  # 3 points per top journal

    # 9. Projects with Significant Impact
    if candidate.get("project_impact", []):
        bonus += len(candidate["project_impact"]) * 2  # 2 points per impactful project
    final_score += bonus

    final_score = min(final_score, 100)
    candidate["score"] = round(final_score, 2)
    candidate["assessment"] = "High Skilled Candidate" if final_score >= 65 else "Candidate needs further review"
    return candidate

def score_candidate_eb2(candidate, ref):
    """
    EB2 (Advanced Degree or Exceptional Ability)
    Criteria (weighted to sum 100):
      - Educational Background: 25%
      - Work Experience: 25%
      - Professional Memberships: 15%
      - Skills and Certifications: 20%
      - Recommendation Letters: 15%
    Bonus: Extra points for degree level and additional higher-cadre attributes.
    """
    final_score = 0

    # 1. Educational Background (30%)
    weight = 30
    edu = candidate.get("education_university", [])[0].strip() if candidate.get("education_university") else ""
    if edu:
        edu_quality = quality_match_score(edu, ref.get("top_universities", []))
        final_score += weight
        final_score += edu_quality

    # 2. Work Experience (25%)
    weight = 25
    work = candidate.get("work_experience", 0)
    quantity = min(work, 5) if work else 0
    final_score += weight * (quantity / 5)

   # 3. Professional Memberships (15%)
    weight = 15
    memberships = candidate.get("achievement_membership", []) + candidate.get("extra_memberships", [])
    availability = 1 if memberships else 0
    quantity = min(len(memberships), 5) if memberships else 0  # Maximum of 5 memberships considered
    quality_memberships = quality_match_score(" ".join(memberships), ref.get("top_associations", [])) if memberships else 0
    final_score += weight * availability * (quantity / 5)  # Base score for membership count
    final_score += quality_memberships  # Add direct bonus for quality

    # 4. Skills and Certifications (20%)
    weight = 20
    skills = candidate.get("technical_skills", "") + " " + candidate.get("core_competencies", "")
    certs = candidate.get("education_certifications", [])
    combined = skills + " " + " ".join(certs)
    availability = 1 if combined.strip() else 0
    quality_skills = quality_match_score(combined, ref.get("top_certifications", [])) if combined.strip() else 0
    quantity = min(candidate.get("skills_quantity", 3), 5)  # Maximum of 5 skills considered
    final_score += weight * availability * (quantity / 5)  # Base score for skills count
    final_score += quality_skills  # Add direct bonus for quality

    # 5. Recommendation Letters (15%)
    weight = 15
    recs = candidate.get("recommendation_letters", [])
    availability = 1 if recs else 0
    quantity = min(len(recs), 5) if recs else 0
    final_score += weight * availability * (quantity / 5)
    
    # Bonus for Degree Level and Extra Higher-Cadre Attributes:
    bonus = degree_bonus(candidate)
    # 1. Judging Experience
    if candidate.get("extra_judging", False):
        bonus += 3

    # 2. Original Contributions
    if candidate.get("extra_contributions", []):
        bonus += 5

    # 4. Patents
    if candidate.get("achievement_patents", []):
        bonus += len(candidate["achievement_patents"]) * 10  # 10 points per patent

    # 5. Leadership Roles
    if candidate.get("achievement_leadership", []):
        bonus += len(candidate["achievement_leadership"]) * 1.5  # 1.5 points per leadership role

    # 6. Licenses and Certifications
    if candidate.get("license_name", []):
        bonus += len(candidate["license_name"]) * 2  # 2 points per license/certification

    # 7. Work Experience at Top Companies
    top_companies = ref.get("top_companies", [])
    work_experience = candidate.get("experience_employer", [])
    bonus += sum(5 for company in work_experience if company in top_companies)  # 5 points per top company

    # 8. Publications in Top Journals
    publications = candidate.get("publication_publisher", [])
    top_journals = ref.get("top_journals", [])
    bonus += sum(3 for pub in publications if any(journal in pub for journal in top_journals))  # 3 points per top journal

    # 9. Projects with Significant Impact
    if candidate.get("project_impact", []):
        bonus += len(candidate["project_impact"]) * 2  # 2 points per impactful project
    final_score += bonus

    final_score = min(final_score, 100)
    candidate["score"] = round(final_score, 2)
    candidate["assessment"] = "High Skilled Candidate" if final_score >= 70 else "Candidate needs further review"
    return candidate

def score_candidate_eb3(candidate, ref):
    """
    EB3 (Skilled Worker, Professional, or Other Worker)
    Criteria (weighted to sum 100):
      - Job Offer Details: 40%
      - Educational Background: 25%
      - Work Experience: 25%
      - Skills and Certifications: 10%
    Bonus: Extra points for extra attributes (judging, original contributions, extra memberships).
    Note: Degree bonus is NOT applied for EB3.
    """
    final_score = 0

    # 1. Job Offer Details (40%)
    weight = 40
    job_offer = candidate.get("job_offer", "").strip()
    availability = 1 if job_offer else 0
    quality_job = 1 if job_offer else 0  # Assume default quality of 1
    final_score += weight * availability * (quality_job / 5)

    # 2. Educational Background (25%)
    weight = 25
    edu = candidate.get("education_university", [])[0].strip() if candidate.get("education_university") else ""
    if edu:
        edu_quality = quality_match_score(edu, ref.get("top_universities", []))
        final_score += weight * (edu_quality / 5)

    # 3. Work Experience (25%)
    weight = 25
    work = candidate.get("work_experience", 0)
    quantity = min(work, 5) if work else 0
    final_score += weight * (quantity / 5)

    # 4. Skills and Certifications (10%)
    weight = 10
    skills = candidate.get("technical_skills", "") + " " + candidate.get("core_competencies", "")
    certs = candidate.get("education_certifications", [])
    combined = skills + " " + " ".join(certs)
    availability = 1 if combined.strip() else 0
    quality_skills = quality_match_score(combined, ref.get("top_certifications", [])) if combined.strip() else 0
    final_score += weight * availability * (quality_skills / 5)
    
    # Bonus for Extra Higher-Cadre Attributes (for EB3)
    bonus = degree_bonus(candidate)

    # 1. Judging Experience
    if candidate.get("extra_judging", False):
        bonus += 3

    # 2. Original Contributions
    if candidate.get("extra_contributions", []):
        bonus += 5

    # 3. Professional Memberships
    if candidate.get("extra_memberships", []):
        bonus += 3

    # 4. Patents
    if candidate.get("achievement_patents", []):
        bonus += len(candidate["achievement_patents"]) * 10  # 10 points per patent

    # 5. Leadership Roles
    if candidate.get("achievement_leadership", []):
        bonus += len(candidate["achievement_leadership"]) * 1.5  # 1.5 points per leadership role

    # 6. Licenses and Certifications
    if candidate.get("license_name", []):
        bonus += len(candidate["license_name"]) * 2  # 2 points per license/certification

    # 7. Work Experience at Top Companies
    top_companies = ref.get("top_companies", [])
    work_experience = candidate.get("experience_employer", [])
    bonus += sum(5 for company in work_experience if company in top_companies)  # 5 points per top company

    # 8. Publications in Top Journals
    publications = candidate.get("publication_publisher", [])
    top_journals = ref.get("top_journals", [])
    bonus += sum(3 for pub in publications if any(journal in pub for journal in top_journals))  # 3 points per top journal

    # 9. Projects with Significant Impact
    if candidate.get("project_impact", []):
        bonus += len(candidate["project_impact"]) * 2  # 2 points per impactful project

    final_score += bonus

    final_score = min(final_score, 100)
    candidate["score"] = round(final_score, 2)
    candidate["assessment"] = "High Skilled Candidate" if final_score >= 50 else "Candidate needs further review"
    return candidate

# -----------------------------
# Main Automated Assessment Dispatcher
# -----------------------------
def auto_assess(candidate):
    """
    Determines which scoring algorithm to use based on candidate['visa_category'].
    """
    visa_category = candidate.get("visa_category", "EB2")  # default to EB2 if not provided

    if visa_category == "EB1A":
        candidate = score_candidate_eb1a(candidate, reference_data)
    elif visa_category == "EB2_NIW":
        candidate = score_candidate_eb2_niw(candidate, reference_data)
    elif visa_category == "EB2":
        candidate = score_candidate_eb2(candidate, reference_data)
    elif visa_category == "EB3":
        candidate = score_candidate_eb3(candidate, reference_data)
    else:
        candidate = score_candidate_eb2(candidate, reference_data)

    return candidate

# -----------------------------
# Routes
# -----------------------------

@app.route('/')
@login_required
def index():
    return redirect(url_for('reports'))

@app.route('/candidates')
@login_required
def candidates():
    candidates = load_candidates()
    filter_assessment = request.args.get("assessment")
    if filter_assessment:
        candidates = [c for c in candidates if c.get("assessment") == filter_assessment]
    return render_template("candidate_list.html", candidates=candidates)

@app.route('/submit', methods=["GET", "POST"])
def candidate_form():
    if request.method == "POST":
        # Capture basic candidate details
        candidate = {
            "id": str(uuid.uuid4()),
            "full_name": request.form.get("full_name"),
            "dob": request.form.get("dob"),
            "nationality": request.form.get("nationality"),
            "country_residence": request.form.get("country_residence"),
            "passport_country": request.form.get("passport_country"),
            "passport_expiry": request.form.get("passport_expiry"),
            "marital_status": request.form.get("marital_status"),
            "dependents": request.form.get("dependents"),
            "email": request.form.get("email"),
            "phone": request.form.get("phone"),
            "mailing_address": request.form.get("mailing_address"),
            # Educational Background (Lists)
            "education_highest": request.form.getlist("education_highest[]"),
            "education_field": request.form.getlist("education_field[]"),
            "education_university": request.form.getlist("education_university[]"),
            "education_country": request.form.getlist("education_country[]"),
            "education_graduation_dates": request.form.getlist("education_graduation_dates[]"),
            "education_honors": request.form.getlist("education_honors[]"),
            "education_certifications": request.form.getlist("education_certifications[]"),
            "education_publications": request.form.getlist("education_publications[]"),
            # Work Experience (Lists)
            "experience_employer": request.form.getlist("experience_employer[]"),
            "experience_location": request.form.getlist("experience_location[]"),
            "experience_title": request.form.getlist("experience_title[]"),
            "experience_duration": request.form.getlist("experience_duration[]"),
            "experience_industry": request.form.getlist("experience_industry[]"),
            "experience_responsibilities": request.form.getlist("experience_responsibilities[]"),
            "experience_accomplishments": request.form.getlist("experience_accomplishments[]"),
            "experience_skills": request.form.getlist("experience_skills[]"),
            # Achievements and Recognitions (Lists)
            "achievement_award": request.form.getlist("achievement_award[]"),
            "achievement_membership": request.form.getlist("achievement_membership[]"),
            "achievement_patents": request.form.getlist("achievement_patents[]"),
            "achievement_leadership": request.form.getlist("achievement_leadership[]"),
            "achievement_research": request.form.getlist("achievement_research[]"),
            "achievement_speaking": request.form.getlist("achievement_speaking[]"),
            "achievement_community": request.form.getlist("achievement_community[]"),
            # Publications and Media (Lists)
            "publication_title": request.form.getlist("publication_title[]"),
            "publication_type": request.form.getlist("publication_type[]"),
            "publication_publisher": request.form.getlist("publication_publisher[]"),
            "publication_date": request.form.getlist("publication_date[]"),
            "publication_media": request.form.getlist("publication_media[]"),
            "publication_presentations": request.form.getlist("publication_presentations[]"),
            "publication_citations": request.form.getlist("publication_citations[]"),
            # Professional Licenses and Certifications (Lists)
            "license_name": request.form.getlist("license_name[]"),
            "license_authority": request.form.getlist("license_authority[]"),
            "license_validity": request.form.getlist("license_validity[]"),
            "license_number": request.form.getlist("license_number[]"),
            "license_details": request.form.getlist("license_details[]"),
            # Evidence of Extraordinary Ability (for EB1A) (Lists)
            "extra_contributions": request.form.getlist("extra_contributions[]"),
            "extra_memberships": request.form.getlist("extra_memberships[]"),
            "extra_high_salary": request.form.getlist("extra_high_salary[]"),
            "extra_roles": request.form.getlist("extra_roles[]"),
            "extra_judging": request.form.getlist("extra_judging[]"),
            "extra_commercial": request.form.getlist("extra_commercial[]"),
            # Special Projects and Contributions (Lists)
            "project_name": request.form.getlist("project_name[]"),
            "project_scope": request.form.getlist("project_scope[]"),
            "project_impact": request.form.getlist("project_impact[]"),
            "project_changes": request.form.getlist("project_changes[]"),
            "project_solutions": request.form.getlist("project_solutions[]"),
            # Language Proficiency (Lists)
            "language": request.form.getlist("language[]"),
            "language_proficiency": request.form.getlist("language_proficiency[]"),
            "language_certifications": request.form.getlist("language_certifications[]"),
            # Immigration History (Lists)
            "immigration_current_status": request.form.getlist("immigration_current_status[]"),
            "immigration_previous_applications": request.form.getlist("immigration_previous_applications[]"),
            "immigration_intentions": request.form.getlist("immigration_intentions[]"),
            "immigration_relocation_preferences": request.form.getlist("immigration_relocation_preferences[]"),
            # Skills and Technical Expertise (Strings)
            "core_competencies": request.form.get("core_competencies"),
            "technical_skills": request.form.get("technical_skills"),
            "cross_disciplines": request.form.get("cross_disciplines"),
            # Contributions to the U.S. Economy and Society (EB2 NIW Specific) (Lists)
            "contribution_national_interest": request.form.getlist("contribution_national_interest[]"),
            "contribution_job_creation": request.form.getlist("contribution_job_creation[]"),
            "contribution_economy": request.form.getlist("contribution_economy[]"),
            "contribution_advancements": request.form.getlist("contribution_advancements[]"),
            # Employment Offer Details (Lists) (For EB2 and EB3)
            "employment_offer_employer": request.form.getlist("employment_offer_employer[]"),
            "employment_offer_details": request.form.getlist("employment_offer_details[]"),
            "employment_offer_title": request.form.getlist("employment_offer_title[]"),
            "employment_offer_description": request.form.getlist("employment_offer_description[]"),
            "employment_offer_labor_cert": request.form.getlist("employment_offer_labor_cert[]"),
            "employment_offer_salary": request.form.getlist("employment_offer_salary[]"),
            # References (Lists)
            "reference_name": request.form.getlist("reference_name[]"),
            "reference_title": request.form.getlist("reference_title[]"),
            "reference_contact": request.form.getlist("reference_contact[]"),
            "reference_relationship": request.form.getlist("reference_relationship[]"),
            # Financial Information
            "financial_support": request.form.get("financial_support"),
            "financial_assets": request.form.get("financial_assets"),
            # Future Goals (Lists)
            "future_short_term": request.form.getlist("future_short_term[]"),
            "future_long_term": request.form.getlist("future_long_term[]"),
            "future_contribution": request.form.getlist("future_contribution[]"),
            # Uploads (Lists)
            "upload_type": request.form.getlist("upload_type[]"),
            "visa_category": request.form.get("visa_category", "EB2"),
            "job_offer": request.form.get("job_offer")
        }

        # Sum work experience
        work_experience_list = request.form.getlist("work_experience[]")
        total_work_experience = sum(float(years) for years in work_experience_list if years.strip().isdigit() or years.strip().replace('.', '', 1).isdigit())
        candidate["work_experience"] = total_work_experience

        # Create a folder for the candidate
        candidate_folder_name = f"{candidate['full_name'].replace(' ', '_')}_{candidate['id']}"
        candidate_folder_path = os.path.join(app.config["UPLOAD_FOLDER"], candidate_folder_name)
        os.makedirs(candidate_folder_path, exist_ok=True)

        # Create subfolders
        subfolders = ["Uploads", "Exhibits", "Resume", "Payments"]
        for folder in subfolders:
            os.makedirs(os.path.join(candidate_folder_path, folder), exist_ok=True)
        
        # Save CV to Resume subfolder
        cv_file = request.files.get("cv_file")
        if cv_file and allowed_file(cv_file.filename):
            extension = cv_file.filename.rsplit('.', 1)[1].lower()
            cv_filename = f"{candidate['id']}_cv.{extension}"
            cv_path = os.path.join(candidate_folder_path, "Resume", cv_filename)
            cv_file.save(cv_path)
            candidate["cv_file"] = cv_path
        else:
            candidate["cv_file"] = None

        # Save financial proofs to Payments subfolder
        candidate["financial_proof"] = []
        for file in request.files.getlist("financial_proof"):
            if file and allowed_file(file.filename):
                extension = file.filename.rsplit('.', 1)[1].lower()
                financial_filename = f"{candidate['id']}_financial_proof_{uuid.uuid4()}.{extension}"
                financial_path = os.path.join(candidate_folder_path, "Payments", financial_filename)
                file.save(financial_path)
                candidate["financial_proof"].append(financial_path)

        # Save other uploads to Uploads subfolder
        candidate["upload_file"] = []
        for idx, file in enumerate(request.files.getlist("upload_file[]")):
            if file and allowed_file(file.filename):
                extension = file.filename.rsplit('.', 1)[1].lower()
                upload_filename = f"{candidate['id']}_upload_{idx}.{extension}"
                upload_path = os.path.join(candidate_folder_path, "Uploads", upload_filename)
                file.save(upload_path)
                candidate["upload_file"].append(upload_path)

        # Save Exhibits files to Exhibits subfolder
        candidate["exhibits"] = []
        for idx, file in enumerate(request.files.getlist("exhibits[]")):
            if file and allowed_file(file.filename):
                extension = file.filename.rsplit('.', 1)[1].lower()
                exhibit_filename = f"{candidate['id']}_exhibit_{idx}.{extension}"
                exhibit_path = os.path.join(candidate_folder_path, "Exhibits", exhibit_filename)
                file.save(exhibit_path)
                candidate["exhibits"].append(exhibit_path)

        # Automated Candidate Assessment (scoring) based on visa_category
        candidate = auto_assess(candidate)

        # Append candidate to file storage
        candidates = load_candidates()
        candidates.append(candidate)
        save_candidates(candidates)

        flash("Candidate submitted successfully!", "success")
        return redirect(url_for("reports"))

    return render_template("candidate_form.html")


@app.route('/candidate/<candidate_id>')
def candidate_detail(candidate_id):
    candidates = load_candidates()
    candidate = next((c for c in candidates if c["id"] == candidate_id), None)
    if not candidate:
        flash("Candidate not found.", "danger")
        return redirect(url_for("index"))
    
    # Calculate averages from all candidates using work_experience
    total_candidates = len(candidates)
    avg_score = (sum(float(c.get("score", 0)) for c in candidates) / total_candidates) if total_candidates else 0
    avg_experience = (sum(float(c.get("work_experience", 0)) for c in candidates) / total_candidates) if total_candidates else 0

    return render_template("candidate_detail.html", candidate=candidate, avg_score=avg_score, avg_experience=avg_experience)

@app.route('/candidate-details', methods=["GET"])
@login_required
def candidate_details():
    candidates = load_candidates()  # Load candidates from the file
    return render_template("candidate_profile.html", candidates=candidates)


@app.route('/compare', methods=["GET", "POST"])
@login_required
def candidate_compare():
    candidates = load_candidates()
    selected_ids = []
    
    if request.method == "POST":
        selected_ids = request.form.getlist("candidate_ids")
    elif request.method == "GET":
        selected_ids = request.args.get("ids", "").split(",")
        selected_ids = [cid for cid in selected_ids if cid]

    selected_candidates = [c for c in candidates if c["id"] in selected_ids]
    if not selected_candidates:
        flash("No candidates selected for comparison.", "warning")
        return redirect(url_for("index"))
    return render_template("candidate_compare.html", candidates=selected_candidates)


#Report Dashboard
@app.route('/reports')
@login_required
def reports():
    candidates = load_candidates()
    total = len(candidates)
    
    high_skilled = sum(1 for candidate in candidates if candidate.get("assessment") == "High Skilled Candidate")
    if total > 0:
        total_score = sum(float(candidate.get("score", 0)) for candidate in candidates)
        average_score = total_score / total
        overview = f"{round(high_skilled / total * 100, 1)}% of candidates are high skilled with an average score of {round(average_score, 1)}."
    else:
        average_score = 0
        overview = "No candidate data available."
    
    # Experience Distribution (bins) using work_experience
    exp_dist = {"0-2 yrs": 0, "3-5 yrs": 0, "6-10 yrs": 0, "10+ yrs": 0}
    for candidate in candidates:
        try:
            years = float(candidate.get("work_experience", 0))
        except (ValueError, TypeError):
            years = 0
        if years <= 2:
            exp_dist["0-2 yrs"] += 1
        elif years <= 5:
            exp_dist["3-5 yrs"] += 1
        elif years <= 10:
            exp_dist["6-10 yrs"] += 1
        else:
            exp_dist["10+ yrs"] += 1
    experience_labels = list(exp_dist.keys())
    experience_data = list(exp_dist.values())
    
    # Education Distribution: use the first element of the "education_highest" array (if provided)
    education_counts = {}
    for candidate in candidates:
        edu_list = candidate.get("education_highest", [])
        if edu_list and len(edu_list) > 0:
            # Use the first entry from the array as the candidate's highest education
            edu = edu_list[0].strip()
        else:
            edu = "Not Provided"
        education_counts[edu] = education_counts.get(edu, 0) + 1
    
    sorted_edu = sorted(education_counts.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_edu) > 4:
        top_edu = sorted_edu[:4]
        other_count = sum(count for _, count in sorted_edu[4:])
        top_edu.append(("Others", other_count))
    else:
        top_edu = sorted_edu
    education_labels = [item[0] for item in top_edu]
    education_data = [item[1] for item in top_edu]
    
    # Top 5 Companies: Use "company" field; if missing, fallback to the first element in "experience_employer"
    company_counts = {}
    for candidate in candidates:
        comp = candidate.get("company")
        if not comp:
            exp_employers = candidate.get("experience_employer", [])
            if exp_employers and len(exp_employers) > 0:
                comp = exp_employers[0]
            else:
                comp = "Not Provided"
        company_counts[comp] = company_counts.get(comp, 0) + 1
    sorted_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)
    top_companies = sorted_companies[:5]
    company_labels = [item[0] for item in top_companies]
    company_data = [item[1] for item in top_companies]
    
    # Scatter Data: work_experience vs score.
    scatter_data = []
    for candidate in candidates:
        try:
            exp = float(candidate.get("work_experience", 0))
        except (ValueError, TypeError):
            exp = 0
        try:
            score = float(candidate.get("score", 0))
        except (ValueError, TypeError):
            score = 0
        scatter_data.append({"x": exp, "y": score})
    
    # Radar Chart: Score distribution bins.
    score_bins = {"0-50": 0, "50-70": 0, "70-90": 0, "90+": 0}
    for candidate in candidates:
        try:
            score = float(candidate.get("score", 0))
        except (ValueError, TypeError):
            score = 0
        if score < 50:
            score_bins["0-50"] += 1
        elif score < 70:
            score_bins["50-70"] += 1
        elif score < 90:
            score_bins["70-90"] += 1
        else:
            score_bins["90+"] += 1
    radar_labels = list(score_bins.keys())
    radar_data = list(score_bins.values())
    
    # Latest candidate submissions (last 5 candidates, newest first)
    latest_candidates = list(reversed(candidates[-5:])) if candidates else []
    
    # Most common visa category
    visa_counts = {}
    for candidate in candidates:
        visa = candidate.get("visa_category", "Unknown")
        visa_counts[visa] = visa_counts.get(visa, 0) + 1
    most_common_visa = max(visa_counts, key=visa_counts.get) if visa_counts else "N/A"
    
    stats = {
        "total": total,
        "high_skilled": high_skilled,
        "average_score": round(average_score, 1),
        "overview": overview,
        "experience_labels": experience_labels,
        "experience_data": experience_data,
        "education_labels": education_labels,
        "education_data": education_data,
        "company_labels": company_labels,
        "company_data": company_data,
        "scatter_data": scatter_data,
        "radar_labels": radar_labels,
        "radar_data": radar_data,
        "latest_candidates": latest_candidates,
        "most_common_visa": most_common_visa
    }
    
    return render_template("report_dashboard.html", stats=stats)


@app.route('/candidate_analysis', methods=['GET', 'POST'])
@login_required
def candidate_analysis():
    candidates = load_candidates()
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data or 'candidate_id' not in data:
                return jsonify({"error": "Candidate ID is required"}), 400

            candidate_id = data['candidate_id']
            selected_candidate = next((c for c in candidates if c['id'] == candidate_id), None)
            if not selected_candidate:
                return jsonify({"error": "Candidate not found"}), 404

            analysis = evaluate_candidate(selected_candidate, reference_data)
            return jsonify(analysis)
        except Exception as e:
            print(f"Error: {e}")
            return jsonify({"error": "An internal error occurred"}), 500

    return render_template('candidate_analysis.html', candidates=candidates)


def evaluate_candidate(candidate, ref):
    """
    Evaluate a candidate based on visa category criteria.
    
    For EB1A, candidates are evaluated against USCIS's extraordinary ability criteria, requiring at least 
    three primary criteria (Awards, Published Work, and Original Contributions) to be near-perfect for automatic qualification.
    
    For EB2, EB2_NIW, and EB3, additional bonus points are awarded for higher-cadre attributes like 
    judging experience, original contributions, and exclusive memberships.
    
    Returns a JSON object with:
      - candidate_name
      - overall score (capped at 100)
      - lists of strengths, weaknesses, and recommendations.
    """
    visa = candidate.get("visa_category", "EB2")
    score_methods = {
        "EB1A": score_candidate_eb1a,
        "EB2": score_candidate_eb2,
        "EB2_NIW": score_candidate_eb2_niw,
        "EB3": score_candidate_eb3
    }

    # Score candidate based on visa category
    score_function = score_methods.get(visa, score_candidate_eb2)
    scored_candidate = score_function(candidate, ref)
    score = scored_candidate.get("score", 0)

    # Adjust score for EB1A based on primary criteria
    if visa == "EB1A":
        primary_count = sum([
            bool(candidate.get("achievement_award", [])),
            bool(candidate.get("publication_title", [])),
            bool(candidate.get("extra_contributions", []))
        ])
        if primary_count >= 3 and score >= 80:  # Near-perfect primary criteria
            scored_candidate["score"] = 100
            scored_candidate["assessment"] = "High Skilled Candidate"

    strengths = []
    weaknesses = []
    recommendations = []

    # Evaluate educational background
    edu = candidate.get("education_university", [])[0].strip() if candidate.get("education_university") else ""
    if edu:
        edu_quality = quality_match_score(edu, ref.get("top_universities", []))
        if edu_quality >= 4:
            strengths.append(f"Strong educational background from {edu}.")
        else:
            weaknesses.append(f"Academic Degree ({edu}) from top-tier institution bonus missing.")
            recommendations.append("Highlight academic honors, advanced research, or specialized training.")
        degree_points = degree_bonus(candidate)
        if degree_points >= 20:
            strengths.append("Holds a doctorate-level degree, which is a significant advantage.")
        elif degree_points >= 10:
            strengths.append("Possesses a master's degree, a strong qualification.")
        elif degree_points >= 5:
            strengths.append("Holds a bachelor's degree.")
    else:
        weaknesses.append("No educational background provided.")
        recommendations.append("Include details of your highest degree and academic achievements.")

    # Evaluate work experience
    work_exp = candidate.get("work_experience", 0)
    try:
        work_exp = float(work_exp)
    except (ValueError, TypeError):
        work_exp = 0
    if work_exp >= 5:
        strengths.append("Demonstrates extensive work experience.")
    else:
        weaknesses.append("Limited work experience.")
        recommendations.append("Consider adding more industry or leadership experience if any.")

    # Evaluate awards
    awards = candidate.get("achievement_award", [])
    if awards:
        strengths.append(f"Recognized with awards such as: {', '.join(awards)}.")
    else:
        weaknesses.append("No awards or recognitions provided.")
        if visa == "EB1A":
            recommendations.append("Include industry awards to strengthen your profile.")

    # Evaluate publications
    pubs = candidate.get("publication_title", [])
    if pubs:
        strengths.append("Has published work or research contributions.")
    else:
        weaknesses.append("No published work detected.")
        if visa in ["EB1A", "EB2_NIW"]:
            recommendations.append("Add research or publications to enhance your case.")

    # Evaluate memberships
    memberships = candidate.get("achievement_membership", []) + candidate.get("extra_memberships", [])
    if memberships:
        strengths.append(f"Member of respected organizations: {', '.join(memberships)}.")
    else:
        weaknesses.append("Lacks membership in known professional associations.")
        if visa in ["EB1A", "EB2"]:
            recommendations.append("Join recognized professional organizations to improve your profile.")

    # Evaluate recommendation letters
    recs = candidate.get("recommendation_letters", [])
    if recs:
        strengths.append("Supported by strong recommendation letters.")
    else:
        weaknesses.append("No recommendation letters provided.")
        recommendations.append("Obtain references from recognized leaders in your field.")

    # Evaluate high salary (EB1A specific)
    if candidate.get("high_salary", False):
        strengths.append("Demonstrates exceptional remuneration compared to peers.")
    else:
        weaknesses.append("Does not showcase extraordinary salary levels.")
        if visa == "EB1A":
            recommendations.append("Provide evidence of financial success or industry-leading compensation.")

    # Evaluate job offer (EB3 specific)
    if visa == "EB3":
        job_offer = candidate.get("job_offer", "").strip()
        if job_offer:
            strengths.append(f"Holds a valid job offer: {job_offer}.")
        else:
            weaknesses.append("No job offer provided for EB3 category.")
            recommendations.append("Secure a valid job offer to meet EB3 requirements.")

    # Evaluate extra attributes for EB2, EB2_NIW
    if visa in ["EB2", "EB2_NIW"]:
        extra_attrs = []
        attr_bonus = 0

        # Judging Experience
        if candidate.get("extra_judging", False):
            extra_attrs.append("judging experience (+3 points)")
            attr_bonus += 3

        # Original Contributions
        if candidate.get("extra_contributions", []):
            count = len(candidate["extra_contributions"])
            extra_attrs.append(f"original contributions ({count} contributions, +{count * 5} points)")
            attr_bonus += count * 5

        # Exclusive Memberships
        if candidate.get("extra_memberships", []):
            count = len(candidate["extra_memberships"])
            extra_attrs.append(f"exclusive memberships ({count} memberships, +{count * 3} points)")
            attr_bonus += count * 3

        # Patents
        if candidate.get("achievement_patents", []):
            count = len(candidate["achievement_patents"])
            extra_attrs.append(f"patents ({count} patents, +{count * 10} points)")
            attr_bonus += count * 10

        # Leadership Roles
        if candidate.get("achievement_leadership", []):
            count = len(candidate["achievement_leadership"])
            extra_attrs.append(f"leadership roles ({count} roles, +{count * 1.5} points)")
            attr_bonus += count * 1.5

        # Licenses and Certifications
        if candidate.get("license_name", []):
            count = len(candidate["license_name"])
            extra_attrs.append(f"licenses/certifications ({count} items, +{count * 2} points)")
            attr_bonus += count * 2

        # Work Experience at Top Companies
        top_companies = ref.get("top_companies", [])
        work_experience = candidate.get("experience_employer", [])
        top_companies_count = sum(1 for company in work_experience if company in top_companies)
        if top_companies_count > 0:
            extra_attrs.append(f"work experience at top companies ({top_companies_count} companies, +{top_companies_count * 5} points)")
            attr_bonus += top_companies_count * 5

        # Publications in Top Journals
        publications = candidate.get("publication_publisher", [])
        top_journals = ref.get("top_journals", [])
        top_journals_count = sum(1 for pub in publications if any(journal in pub for journal in top_journals))
        if top_journals_count > 0:
            extra_attrs.append(f"publications in top journals ({top_journals_count} journals, +{top_journals_count * 3} points)")
            attr_bonus += top_journals_count * 3

        if extra_attrs:
            strengths.append(f"Possesses extra attributes ({', '.join(extra_attrs)}), contributing a total of +{attr_bonus} bonus points.")
            recommendations.append("Highlight these extra qualifications to further strengthen your application.")

    # Evaluate extra attributes for EB1A
    if visa in ["EB1A"]:
        extra_attrs = []
        attr_bonus = 0

        # Patents
        if candidate.get("achievement_patents", []):
            count = len(candidate["achievement_patents"])
            extra_attrs.append(f"patents ({count} patents, +{count * 10} points)")
            attr_bonus += count * 10

        # Leadership Roles
        if candidate.get("achievement_leadership", []):
            count = len(candidate["achievement_leadership"])
            extra_attrs.append(f"leadership roles ({count} roles, +{count * 1.5} points)")
            attr_bonus += count * 1.5

        # Licenses and Certifications
        if candidate.get("license_name", []):
            count = len(candidate["license_name"])
            extra_attrs.append(f"licenses/certifications ({count} items, +{count * 2} points)")
            attr_bonus += count * 2

        # Work Experience at Top Companies
        top_companies = ref.get("top_companies", [])
        work_experience = candidate.get("experience_employer", [])
        top_companies_count = sum(1 for company in work_experience if company in top_companies)
        if top_companies_count > 0:
            extra_attrs.append(f"work experience at top companies ({top_companies_count} companies, +{top_companies_count * 5} points)")
            attr_bonus += top_companies_count * 5

        # Publications in Top Journals
        publications = candidate.get("publication_publisher", [])
        top_journals = ref.get("top_journals", [])
        top_journals_count = sum(1 for pub in publications if any(journal in pub for journal in top_journals))
        if top_journals_count > 0:
            extra_attrs.append(f"publications in top journals ({top_journals_count} journals, +{top_journals_count * 3} points)")
            attr_bonus += top_journals_count * 3

        if extra_attrs:
            strengths.append(f"Possesses extra attributes ({', '.join(extra_attrs)}), contributing a total of +{attr_bonus} bonus points.")
            recommendations.append("Highlight these extra qualifications to further strengthen your application.")

    # Evaluate extra attributes for EB2, EB2_NIW, and EB3
    if visa in ["EB3"]:
        extra_attrs = []
        attr_bonus = 0

        # Judging Experience
        if candidate.get("extra_judging", False):
            extra_attrs.append("judging experience (+3 points)")
            attr_bonus += 3

        # Original Contributions
        if candidate.get("extra_contributions", []):
            count = len(candidate["extra_contributions"])
            extra_attrs.append(f"original contributions ({count} contributions, +{count * 5} points)")
            attr_bonus += count * 5

        # Professional Memberships
        if candidate.get("extra_memberships", []):
            count = len(candidate["extra_memberships"])
            extra_attrs.append(f"exclusive memberships ({count} memberships, +{count * 3} points)")
            attr_bonus += count * 3

        # Patents
        if candidate.get("achievement_patents", []):
            count = len(candidate["achievement_patents"])
            extra_attrs.append(f"patents ({count} patents, +{count * 10} points)")
            attr_bonus += count * 10

        # Leadership Roles
        if candidate.get("achievement_leadership", []):
            count = len(candidate["achievement_leadership"])
            extra_attrs.append(f"leadership roles ({count} roles, +{count * 1.5} points)")
            attr_bonus += count * 1.5

        # Licenses and Certifications
        if candidate.get("license_name", []):
            count = len(candidate["license_name"])
            extra_attrs.append(f"licenses/certifications ({count} items, +{count * 2} points)")
            attr_bonus += count * 2

        # Work Experience at Top Companies
        top_companies = ref.get("top_companies", [])
        work_experience = candidate.get("experience_employer", [])
        top_companies_count = sum(1 for company in work_experience if company in top_companies)
        if top_companies_count > 0:
            extra_attrs.append(f"work experience at top companies ({top_companies_count} companies, +{top_companies_count * 5} points)")
            attr_bonus += top_companies_count * 5

        # Publications in Top Journals
        publications = candidate.get("publication_publisher", [])
        top_journals = ref.get("top_journals", [])
        top_journals_count = sum(1 for pub in publications if any(journal in pub for journal in top_journals))
        if top_journals_count > 0:
            extra_attrs.append(f"publications in top journals ({top_journals_count} journals, +{top_journals_count * 3} points)")
            attr_bonus += top_journals_count * 3

        if extra_attrs:
            strengths.append(f"Possesses extra attributes ({', '.join(extra_attrs)}), contributing a total of +{attr_bonus} bonus points.")
            recommendations.append("Highlight these extra qualifications to further strengthen your application.")


    # Provide overall recommendations
    if score >= 80:
        recommendations.append("Overall, this profile is highly competitive.")
    elif score >= 50:
        recommendations.append("Enhancements in certain areas can further strengthen the profile.")
    else:
        recommendations.append("Significant improvements are required to meet the criteria.")

    return {
        "candidate_name": scored_candidate.get("full_name", "Unknown"),
        "score": scored_candidate["score"],
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations
    }

# Context Processor to inject ALLOWED_EXTENSIONS into all templates
@app.context_processor
def inject_allowed_extensions():
    return {
        'allowed_extensions': app.config.get('ALLOWED_EXTENSIONS', [])
    }

# -----------------------------
# Existing /petition Route (Unchanged)
# -----------------------------
@app.route('/petition', methods=['GET', 'POST'])
@login_required  # Ensure that only logged-in users can access
def petition():
    candidates = load_candidates()
    selected_candidate_id = None  # Initialize variable

    if request.method == 'POST':
        # Handle File Uploads
        candidate_id = request.form.get('candidate_id')
        folder_type = request.form.get('folder_type')  # e.g., Uploads, Exhibits, Resume, Payments
        uploaded_files = request.files.getlist('files')

        # Input Validation
        if not candidate_id or not folder_type:
            flash('Candidate and Folder Type are required.', 'danger')
            return redirect(url_for('petition'))

        # Validate Folder Type
        if folder_type not in ["Uploads", "Exhibits", "Resume", "Payments"]:
            flash('Invalid folder type selected.', 'danger')
            return redirect(url_for('petition'))

        # Load Candidates
        candidates = load_candidates()

        # Find the Candidate
        candidate = next((c for c in candidates if c["id"] == candidate_id), None)
        if not candidate:
            flash('Selected candidate does not exist.', 'danger')
            return redirect(url_for('petition'))

        # Define Folder Paths
        candidate_folder_name = f"{candidate['full_name'].replace(' ', '_')}_{candidate['id']}"
        candidate_folder_path = os.path.join(app.config["UPLOAD_FOLDER"], candidate_folder_name, folder_type)
        os.makedirs(candidate_folder_path, exist_ok=True)

        # Initialize File Lists if Not Present
        if folder_type == "Uploads":
            candidate.setdefault("upload_file", [])
        elif folder_type == "Exhibits":
            candidate.setdefault("exhibits", [])
        elif folder_type == "Resume":
            candidate.setdefault("cv_file", None)
        elif folder_type == "Payments":
            candidate.setdefault("financial_proof", [])

        # Save Uploaded Files
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(candidate_folder_path, unique_filename)
                file.save(file_path)

                # Update Candidate Data
                relative_path = os.path.relpath(file_path, app.config["UPLOAD_FOLDER"]).replace('\\', '/')
                if folder_type == "Uploads":
                    candidate["upload_file"].append(relative_path)
                elif folder_type == "Exhibits":
                    candidate["exhibits"].append(relative_path)
                elif folder_type == "Resume":
                    candidate["cv_file"] = relative_path
                elif folder_type == "Payments":
                    candidate["financial_proof"].append(relative_path)
            else:
                flash(f'File {file.filename} is not allowed.', 'warning')

        # Save Updated Candidates
        save_candidates(candidates)
        flash('Files uploaded successfully.', 'success')

        # Redirect back to the petition page with the selected candidate_id
        return redirect(url_for('petition', selected_candidate_id=candidate_id))

    elif request.method == 'GET':
        # Handle GET Request: Display Petition Page
        selected_candidate_id = request.args.get('selected_candidate_id')

    allowed_extensions = app.config.get('ALLOWED_EXTENSIONS', [])
    return render_template(
        'petition.html',
        candidates=candidates,
        allowed_extensions=allowed_extensions,
        selected_candidate_id=selected_candidate_id  # Pass selected_candidate_id to the template
    )

# -----------------------------
# Existing /api/candidate/<candidate_id>/files Route (Unchanged)
# -----------------------------
@app.route('/api/candidate/<candidate_id>/files', methods=['GET'])
@login_required
def get_candidate_files(candidate_id):
    folder = request.args.get('folder')
    if folder not in ["Uploads", "Exhibits", "Resume", "Payments"]:
        return jsonify({"error": "Invalid folder type."}), 400

    # Load Candidates
    candidates = load_candidates()
    candidate = next((c for c in candidates if c["id"] == candidate_id), None)
    if not candidate:
        return jsonify({"error": "Candidate not found."}), 404

    # Determine the folder key in candidate data
    folder_key_map = {
        "Uploads": "upload_file",
        "Exhibits": "exhibits",
        "Resume": "cv_file",
        "Payments": "financial_proof"
    }
    folder_key = folder_key_map.get(folder)

    if not folder_key:
        return jsonify({"error": "Invalid folder key."}), 400

    files = candidate.get(folder_key, [])
    if folder == "Resume" and files:
        # Resume is a single file
        files = [files]

    return jsonify({"files": files}), 200

# -----------------------------
# Updated /api/candidate/<candidate_id>/petition_details Route
# -----------------------------
@app.route('/api/candidate/<candidate_id>/petition_details', methods=['POST', 'GET'])
@login_required
def petition_details(candidate_id):
    candidates = load_candidates()
    candidate = next((c for c in candidates if c["id"] == candidate_id), None)
    if not candidate:
        return jsonify({"error": "Candidate not found."}), 404

    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided."}), 400

        cover_letter = data.get('cover_letter')
        petition_content = data.get('petition')
        list_of_exhibits = data.get('list_of_exhibits')

        # Initialize Petition Details if Not Present
        if "petition_details" not in candidate:
            candidate["petition_details"] = {}

        # Update Cover Letter
        if cover_letter is not None:
            candidate["petition_details"]['cover_letter'] = cover_letter

        # Update Petition Content
        if petition_content is not None:
            candidate["petition_details"]['petition'] = petition_content

        # Update List of Exhibits
        if list_of_exhibits is not None:
            candidate["petition_details"]['list_of_exhibits'] = list_of_exhibits

        # Save Updated Candidates
        save_candidates(candidates)

        return jsonify({"success": "Petition details saved successfully."}), 200

    elif request.method == 'GET':
        # Optionally, implement GET method to retrieve petition details
        # Not strictly necessary for this functionality
        petition_details = candidate.get("petition_details", {})
        return jsonify(petition_details), 200

# -----------------------------
# Download PDF Route
# -----------------------------
@app.route('/candidate/<candidate_id>/pdf')
@login_required
def candidate_pdf(candidate_id):
    candidates = load_candidates()
    candidate = next((c for c in candidates if c["id"] == candidate_id), None)
    if not candidate:
        flash("Candidate not found.", "danger")
        return redirect(url_for("index"))
    
    # Retrieve petition details
    petition_details = candidate.get("petition_details", {})
    cover_letter = petition_details.get("cover_letter", "")
    exhibits = petition_details.get("list_of_exhibits", [])
    petition_content = petition_details.get("petition", "")
    
    # Render a separate template for PDF if needed
    rendered = render_template("candidate_pdf.html", candidate=candidate, cover_letter=cover_letter, exhibits=exhibits, petition_content=petition_content)
    
    # Configure pdfkit
    config_pdf = pdfkit.configuration(**app.config.get("PDF_CONFIG", {}))
    pdf = pdfkit.from_string(rendered, False, configuration=config_pdf)
    pdf_filename = f"{candidate['full_name'].replace(' ', '_')}_petition.pdf"
    
    from io import BytesIO
    return send_file(BytesIO(pdf),
                     as_attachment=True,
                     download_name=pdf_filename,
                     mimetype='application/pdf')


# -----------------------------
# Route for Renaming Files
# -----------------------------
@app.route('/api/candidate/<candidate_id>/rename_file', methods=['POST'])
@login_required
def rename_file(candidate_id):
    app.logger.debug(f"Rename file request received for candidate_id: {candidate_id}")
    
    # Load candidate and validate
    candidates = load_candidates()
    candidate = next((c for c in candidates if c["id"] == candidate_id), None)
    if not candidate:
        app.logger.warning(f"Candidate {candidate_id} not found.")
        return jsonify({"error": "Candidate not found."}), 404

    data = request.get_json()
    if not data or 'old_file_path' not in data or 'new_file_name' not in data:
        app.logger.warning("Invalid request data for renaming file.")
        return jsonify({"error": "Invalid request data."}), 400

    old_file_path = data['old_file_path']
    new_file_name = secure_filename(data['new_file_name'])
    app.logger.debug(f"Renaming file from {old_file_path} to {new_file_name}")

    # Ensure file exists
    full_old_file_path = os.path.join(app.config["UPLOAD_FOLDER"], old_file_path)
    if not os.path.isfile(full_old_file_path):
        app.logger.warning(f"Original file {full_old_file_path} not found.")
        return jsonify({"error": "Original file not found."}), 404

    # Determine new file path
    folder = os.path.dirname(full_old_file_path)
    new_file_path = os.path.join(folder, new_file_name)
    app.logger.debug(f"New file path: {new_file_path}")

    # Check if new file name already exists
    if os.path.exists(new_file_path):
        app.logger.warning(f"File with name {new_file_name} already exists.")
        return jsonify({"error": "A file with the new name already exists."}), 400

    # Rename file
    try:
        os.rename(full_old_file_path, new_file_path)
        app.logger.info(f"File renamed successfully to {new_file_path}")
        
        # Update candidate's record if necessary
        relative_new_file_path = os.path.relpath(new_file_path, app.config["UPLOAD_FOLDER"]).replace('\\', '/')
        updated = False

        for folder_key in ["upload_file", "exhibits", "cv_file", "financial_proof"]:
            if folder_key in candidate:
                if isinstance(candidate[folder_key], list):
                    # Update lists (Uploads, Exhibits, etc.)
                    for i, path in enumerate(candidate[folder_key]):
                        if path == old_file_path:
                            candidate[folder_key][i] = relative_new_file_path
                            updated = True
                elif candidate[folder_key] == old_file_path:
                    # Update single files (Resume)
                    candidate[folder_key] = relative_new_file_path
                    updated = True

        # Save changes if necessary
        if updated:
            save_candidates(candidates)
            app.logger.debug("Candidate records updated with new file path.")
        else:
            app.logger.warning("Old file path not found in candidate records.")

        return jsonify({"success": "File renamed successfully."}), 200
    except Exception as e:
        app.logger.error(f"Failed to rename file: {str(e)}")
        return jsonify({"error": f"Failed to rename file: {str(e)}"}), 500
    

@app.route('/api/get_example', methods=['POST'])
def get_example():
    data = request.get_json()
    prompt_type = data.get('prompt_type')
    app.logger.debug(f"Received prompt_type: {prompt_type}")

    if not prompt_type:
        app.logger.warning("No prompt_type provided in the request.")
        return jsonify({"error": "Prompt type is required."}), 400

    # Validate prompt_type to prevent unauthorized file access
    ALLOWED_PROMPTS = {
        "cover_letter",
        "advanced_degree",
        "proposed_endeavor_intro",
        "substantial_merit",
        "national_importance",
        "well_positioned",
        "exceptional_contributions",
        "letters_of_recommendation",
        "projects",
        "awards",
        "membership",
        "impact_evidence",
        "industry_contributions",
        "on_balance",
        "business_plans",
        "employer_affidavits"
    }

    if prompt_type not in ALLOWED_PROMPTS:
        app.logger.warning(f"Invalid prompt_type received: {prompt_type}")
        return jsonify({"error": "Invalid prompt type."}), 400

    # Construct the filename and path (e.g., cover_letter.txt)
    filename = f"{prompt_type}.txt"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    app.logger.debug(f"Looking for file: {file_path}")

    try:
        # Read and return the content of the example file
        with open(file_path, 'r', encoding='utf-8') as file:
            example_content = file.read()
        app.logger.debug(f"Successfully read content from {filename}")
        return jsonify({"example": example_content}), 200
    except FileNotFoundError:
        app.logger.error(f"Example file '{filename}' not found.")
        return jsonify({"error": f"Example file '{filename}' not found."}), 404
    except Exception as e:
        app.logger.error(f"Error reading file '{filename}': {str(e)}")
        return jsonify({"error": str(e)}), 500
    

@app.route('/api/genai/generate', methods=['POST'])
@login_required
def genai_generate():
    data = request.get_json()
    candidate_id = data.get('candidate_id')
    prompt_type = data.get('prompt_type')
    format = data.get('format')
    custom_prompt = data.get('custom_prompt')
    proposed_endeavor_summary = data.get('proposed_endeavor_summary')
    field = data.get('field')
    additional_data = data.get('additional_data', {})

    if not candidate_id or not prompt_type or not format:
        return jsonify({"error": "Missing required fields."}), 400

    # Load candidate data
    candidates = load_candidates()
    candidate = next((c for c in candidates if c["id"] == candidate_id), None)
    if not candidate:
        return jsonify({"error": "Candidate not found."}), 404

    # Prepare the prompt based on the candidate's data and additional fields
    prompt = generate_prompt(candidate, prompt_type, custom_prompt, proposed_endeavor_summary, field, additional_data)

    try:
        # Call Deepseek API using the OpenAI client
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            stream=True
        )

        # Extract the generated content from the response
        generated_content = response.choices[0].message.content
        return jsonify({"generated_content": generated_content}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def generate_prompt(candidate, prompt_type, custom_prompt, proposed_endeavor_summary, field, additional_data):
    # Generate a prompt based on the candidate's data and the selected prompt type
    if prompt_type == 'cover_letter':
        return f"Generate a cover letter for {candidate['full_name']} based on their experience in {candidate['experience_industry'][0]}."
    elif prompt_type == 'proposed_endeavor_intro':
        return f"Generate an introduction for the proposed endeavor of {candidate['full_name']} in the field of {field}. Summary: {proposed_endeavor_summary}."
    elif prompt_type == 'substantial_merit':
        sources = additional_data.get('sources', [])
        articles = additional_data.get('articles', [])
        sources_text = ", ".join([f"{source} ({article})" for source, article in zip(sources, articles)])
        return f"Generate content about the substantial merit of {candidate['full_name']}'s work in {field}. Sources: {sources_text}."
    elif prompt_type == 'national_importance':
        sources = additional_data.get('sources', [])
        contents = additional_data.get('contents', [])
        sources_text = ", ".join([f"{source} ({content})" for source, content in zip(sources, contents)])
        return f"Generate content about the national importance of {candidate['full_name']}'s work in {field}. Sources: {sources_text}."
    else:
        return custom_prompt


if __name__ == '__main__':
    os.makedirs(app.config["DATA_FOLDER"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    if not os.path.exists(app.config["CANDIDATES_FILE"]):
        save_candidates([])
    app.run()
