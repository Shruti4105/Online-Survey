import io
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, abort, send_file
)
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default-insecure-survey-key-change-in-prod-2026")

# Environment Configurations
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "").strip()
COSMOS_KEY = os.getenv("COSMOS_KEY", "").strip()
COSMOS_DATABASE = os.getenv("COSMOS_DATABASE", "SurveyDB").strip()
COSMOS_QUESTIONS_CONTAINER = os.getenv("COSMOS_QUESTIONS_CONTAINER", "Questions").strip()
COSMOS_RESPONSES_CONTAINER = os.getenv("COSMOS_RESPONSES_CONTAINER", "Responses").strip()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
AZURE_FILE_SHARE = os.getenv("AZURE_FILE_SHARE", "surveyfiles").strip()

CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "").strip()
TENANT_ID = os.getenv("TENANT_ID", "").strip()
REDIRECT_URI = os.getenv("REDIRECT_URI", "").strip()

ADMIN_EMAILS_RAW = os.getenv("ADMIN_EMAILS", "")
ADMIN_EMAILS = [e.strip().lower() for e in ADMIN_EMAILS_RAW.replace(";", ",").split(",") if e.strip()]

# Default 10 Seed Questions
DEFAULT_QUESTIONS = [
    {
        "id": "q1",
        "question": "How satisfied are you with our overall product/service?",
        "type": "radio",
        "options": ["Very Satisfied", "Satisfied", "Neutral", "Dissatisfied", "Very Dissatisfied"],
        "required": True,
        "active": True,
        "display_order": 1,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z"
    },
    {
        "id": "q2",
        "question": "How would you rate the quality of our product/service?",
        "type": "radio",
        "options": ["Excellent", "Good", "Average", "Poor", "Very Poor"],
        "required": True,
        "active": True,
        "display_order": 2,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z"
    },
    {
        "id": "q3",
        "question": "How easy was it to use our product/service?",
        "type": "radio",
        "options": ["Very Easy", "Easy", "Neutral", "Difficult", "Very Difficult"],
        "required": True,
        "active": True,
        "display_order": 3,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z"
    },
    {
        "id": "q4",
        "question": "How satisfied were you with our customer support?",
        "type": "radio",
        "options": ["Very Satisfied", "Satisfied", "Neutral", "Dissatisfied", "Very Dissatisfied", "I did not contact customer support"],
        "required": True,
        "active": True,
        "display_order": 4,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z"
    },
    {
        "id": "q5",
        "question": "How likely are you to recommend our product/service to a friend or colleague?",
        "type": "radio",
        "options": ["Definitely", "Probably", "Not Sure", "Probably Not", "Definitely Not"],
        "required": True,
        "active": True,
        "display_order": 5,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z"
    },
    {
        "id": "q6",
        "question": "Which aspect of our product/service do you value the most?",
        "type": "checkbox",
        "options": ["Quality", "Price", "Ease of Use", "Customer Support", "Features", "Reliability", "Speed/Performance", "Other"],
        "required": False,
        "active": True,
        "display_order": 6,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z"
    },
    {
        "id": "q7",
        "question": "How would you rate the value for money of our product/service?",
        "type": "radio",
        "options": ["Excellent", "Good", "Average", "Poor", "Very Poor"],
        "required": True,
        "active": True,
        "display_order": 7,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z"
    },
    {
        "id": "q8",
        "question": "What could we improve to make your experience better?",
        "type": "textarea",
        "options": [],
        "required": False,
        "active": True,
        "display_order": 8,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z"
    },
    {
        "id": "q9",
        "question": "Is there any feature or service you would like us to add in the future?",
        "type": "textarea",
        "options": [],
        "required": False,
        "active": True,
        "display_order": 9,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z"
    },
    {
        "id": "q10",
        "question": "Would you consider using our product/service again?",
        "type": "radio",
        "options": ["Definitely Yes", "Probably Yes", "Not Sure", "Probably No", "Definitely No"],
        "required": True,
        "active": True,
        "display_order": 10,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z"
    }
]

# --- Database & Azure Service Adapters ---

cosmos_client = None
questions_container = None
responses_container = None
_local_questions_store = []
_local_responses_store = []

def get_cosmos_containers():
    """Initializes and returns Cosmos DB containers, or None if credentials are not configured."""
    global cosmos_client, questions_container, responses_container
    if questions_container and responses_container:
        return questions_container, responses_container
    
    if COSMOS_ENDPOINT and COSMOS_KEY and not COSMOS_KEY.startswith("<"):
        try:
            from azure.cosmos import CosmosClient, PartitionKey
            cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)
            database = cosmos_client.create_database_if_not_exists(id=COSMOS_DATABASE)
            questions_container = database.create_container_if_not_exists(
                id=COSMOS_QUESTIONS_CONTAINER,
                partition_key=PartitionKey(path="/id")
            )
            responses_container = database.create_container_if_not_exists(
                id=COSMOS_RESPONSES_CONTAINER,
                partition_key=PartitionKey(path="/id")
            )
            seed_default_questions_if_needed(questions_container)
            return questions_container, responses_container
        except Exception as e:
            app.logger.error(f"Cosmos DB connection failed: {e}")
            return None, None
    return None, None

def seed_default_questions_if_needed(container):
    """Inserts default questions only if container is empty."""
    try:
        query = "SELECT VALUE COUNT(1) FROM c"
        count_results = list(container.query_items(query=query, enable_cross_partition_query=True))
        if count_results and count_results[0] == 0:
            for q in DEFAULT_QUESTIONS:
                container.create_item(body=q)
            app.logger.info("Successfully seeded 10 default questions in Cosmos DB.")
    except Exception as e:
        app.logger.error(f"Error seeding questions: {e}")

def init_local_fallback():
    global _local_questions_store
    if not _local_questions_store:
        _local_questions_store = [dict(q) for q in DEFAULT_QUESTIONS]

init_local_fallback()

def fetch_all_questions(only_active=False):
    q_container, _ = get_cosmos_containers()
    if q_container:
        try:
            if only_active:
                query = "SELECT * FROM c WHERE c.active = true ORDER BY c.display_order ASC"
            else:
                query = "SELECT * FROM c ORDER BY c.display_order ASC"
            items = list(q_container.query_items(query=query, enable_cross_partition_query=True))
            return sorted(items, key=lambda x: x.get("display_order", 0))
        except Exception as e:
            app.logger.error(f"Error querying Cosmos DB questions: {e}")
    
    qs = [dict(q) for q in _local_questions_store if (not only_active or q.get("active", True))]
    return sorted(qs, key=lambda x: x.get("display_order", 0))

def fetch_question_by_id(question_id):
    q_container, _ = get_cosmos_containers()
    if q_container:
        try:
            query = "SELECT * FROM c WHERE c.id = @id"
            params = [{"name": "@id", "value": question_id}]
            items = list(q_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
            return items[0] if items else None
        except Exception as e:
            app.logger.error(f"Error fetching question {question_id}: {e}")
    
    for q in _local_questions_store:
        if q.get("id") == question_id:
            return dict(q)
    return None

def save_question_document(question_doc, is_new=False):
    q_container, _ = get_cosmos_containers()
    now_iso = datetime.now(timezone.utc).isoformat()
    question_doc["updated_at"] = now_iso
    if is_new:
        question_doc["created_at"] = now_iso
    
    if q_container:
        try:
            q_container.upsert_item(body=question_doc)
            return True
        except Exception as e:
            app.logger.error(f"Error saving question: {e}")
            return False
    
    global _local_questions_store
    if is_new:
        _local_questions_store.append(question_doc)
    else:
        for idx, q in enumerate(_local_questions_store):
            if q.get("id") == question_doc.get("id"):
                _local_questions_store[idx] = question_doc
                break
    return True

def delete_question_document(question_id):
    q_container, _ = get_cosmos_containers()
    if q_container:
        try:
            q_container.delete_item(item=question_id, partition_key=question_id)
            return True
        except Exception as e:
            app.logger.error(f"Error deleting question {question_id}: {e}")
            return False
    
    global _local_questions_store
    _local_questions_store = [q for q in _local_questions_store if q.get("id") != question_id]
    return True

def save_response_document(response_doc):
    _, r_container = get_cosmos_containers()
    if r_container:
        try:
            r_container.create_item(body=response_doc)
            return True
        except Exception as e:
            app.logger.error(f"Error creating response: {e}")
            return False
    
    global _local_responses_store
    _local_responses_store.append(response_doc)
    return True

def fetch_all_responses():
    _, r_container = get_cosmos_containers()
    if r_container:
        try:
            query = "SELECT * FROM c ORDER BY c.submitted_at DESC"
            items = list(r_container.query_items(query=query, enable_cross_partition_query=True))
            return items
        except Exception as e:
            app.logger.error(f"Error querying responses: {e}")
    
    return sorted(_local_responses_store, key=lambda x: x.get("submitted_at", ""), reverse=True)

def fetch_response_by_id(response_id):
    _, r_container = get_cosmos_containers()
    if r_container:
        try:
            query = "SELECT * FROM c WHERE c.id = @id"
            params = [{"name": "@id", "value": response_id}]
            items = list(r_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
            return items[0] if items else None
        except Exception as e:
            app.logger.error(f"Error fetching response {response_id}: {e}")
    
    for r in _local_responses_store:
        if r.get("id") == response_id:
            return r
    return None

def upload_file_to_azure_files(file_obj):
    if not file_obj or file_obj.filename == "":
        app.logger.info("upload_file_to_azure_files: No file provided or filename is empty.")
        return None
    
    filename = secure_filename(file_obj.filename)
    if not filename:
        filename = f"attachment_{uuid.uuid4().hex[:6]}.dat"
    
    unique_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_{filename}"
    file_bytes = file_obj.read()
    file_size = len(file_bytes)
    
    app.logger.info(f"upload_file_to_azure_files: Preparing upload for '{filename}' ({file_size} bytes)")
    
    if AZURE_STORAGE_CONNECTION_STRING and not AZURE_STORAGE_CONNECTION_STRING.startswith("<"):
        try:
            from azure.storage.fileshare import ShareServiceClient
            service_client = ShareServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
            share_client = service_client.get_share_client(AZURE_FILE_SHARE)
            if not share_client.exists():
                share_client.create_share()
            
            file_client = share_client.get_file_client(unique_name)
            file_client.create_file(file_size)
            if file_size > 0:
                file_client.upload_range(file_bytes, 0, file_size)
            result_path = f"{AZURE_FILE_SHARE}/{unique_name}"
            app.logger.info(f"upload_file_to_azure_files: Successfully uploaded to Azure Files path: '{result_path}'")
            return result_path
        except Exception as e:
            app.logger.error(f"Azure Files upload error: {e}")
    
    upload_dir = os.path.join(app.root_path, "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    local_path = os.path.join(upload_dir, unique_name)
    with open(local_path, "wb") as f:
        f.write(file_bytes)
    result_path = f"uploads/{unique_name}"
    app.logger.info(f"upload_file_to_azure_files: Successfully stored in local fallback path: '{result_path}'")
    return result_path

def is_admin(user_email):
    if not user_email:
        return False
    if not ADMIN_EMAILS:
        return True
    return user_email.lower() in ADMIN_EMAILS

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get("user")
        if not user:
            flash("Please sign in with an authorized Microsoft administrator account to access the Admin portal.", "warning")
            return redirect(url_for("login", next=request.url))
        
        email = user.get("email") or user.get("preferred_username") or ""
        if not is_admin(email):
            flash(f"Access denied: Account '{email}' is not authorized as an administrator.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

def get_msal_app():
    if CLIENT_ID and CLIENT_SECRET and TENANT_ID and not CLIENT_ID.startswith("<"):
        try:
            import msal
            authority = f"https://login.microsoftonline.com/{TENANT_ID}"
            return msal.ConfidentialClientApplication(
                client_id=CLIENT_ID,
                client_credential=CLIENT_SECRET,
                authority=authority
            )
        except Exception as e:
            app.logger.error(f"MSAL init error: {e}")
    return None

@app.context_processor
def inject_global_context():
    user = session.get("user")
    user_email = (user.get("email") or user.get("preferred_username") or "") if user else ""
    return {
        "current_user": user,
        "is_admin_user": is_admin(user_email),
        "cosmos_connected": bool(COSMOS_ENDPOINT and COSMOS_KEY and not COSMOS_KEY.startswith("<")),
        "current_year": datetime.now().year
    }

# ==========================================
# PUBLIC / CUSTOMER ROUTES
# ==========================================

@app.route("/")
def index():
    active_questions = fetch_all_questions(only_active=True)
    return render_template("index.html", total_questions=len(active_questions))

@app.route("/login")
def login():
    msal_app = get_msal_app()
    redirect_uri = REDIRECT_URI or url_for("auth_callback", _external=True)
    if msal_app:
        auth_url = msal_app.get_authorization_request_url(
            scopes=["User.Read"],
            redirect_uri=redirect_uri
        )
        return redirect(auth_url)
    return render_template("login.html", redirect_uri=redirect_uri)

@app.route("/dev-login", methods=["POST"])
def dev_login():
    email = request.form.get("email", "").strip().lower()
    name = request.form.get("name", "").strip() or "Demo User"
    if not email:
        flash("Please provide an email address.", "warning")
        return redirect(url_for("login"))
    
    session["user"] = {
        "name": name,
        "email": email,
        "preferred_username": email,
        "auth_provider": "local_dev"
    }
    flash(f"Signed in as {name} ({email})", "success")
    if is_admin(email):
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("survey"))

@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")
    if not code:
        flash("Authentication failed or was canceled.", "danger")
        return redirect(url_for("login"))
    
    msal_app = get_msal_app()
    if not msal_app:
        flash("Microsoft Entra ID is not configured on this environment.", "danger")
        return redirect(url_for("login"))
    
    redirect_uri = REDIRECT_URI or url_for("auth_callback", _external=True)
    result = msal_app.acquire_token_by_authorization_code(
        code=code,
        scopes=["User.Read"],
        redirect_uri=redirect_uri
    )
    
    if "error" in result:
        app.logger.error(f"MSAL Error: {result.get('error_description')}")
        flash(f"Sign-in error: {result.get('error_description')}", "danger")
        return redirect(url_for("login"))
    
    id_claims = result.get("id_token_claims", {})
    user_info = {
        "name": id_claims.get("name") or id_claims.get("given_name") or "User",
        "email": (id_claims.get("email") or id_claims.get("preferred_username") or "").lower(),
        "preferred_username": id_claims.get("preferred_username", "").lower(),
        "oid": id_claims.get("oid")
    }
    session["user"] = user_info
    flash(f"Welcome back, {user_info['name']}!", "success")
    
    if is_admin(user_info["email"]):
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("survey"))

@app.route("/logout")
def logout():
    session.clear()
    flash("You have successfully signed out.", "info")
    return redirect(url_for("index"))

@app.route("/survey")
def survey():
    questions = fetch_all_questions(only_active=True)
    user = session.get("user", {})
    default_name = user.get("name", "")
    default_email = user.get("email") or user.get("preferred_username", "")
    return render_template(
        "survey.html",
        questions=questions,
        default_name=default_name,
        default_email=default_email
    )

@app.route("/submit", methods=["POST"])
def submit_survey():
    name = request.form.get("customer_name", "").strip()
    email = request.form.get("customer_email", "").strip()
    phone = request.form.get("customer_phone", "").strip()
    
    if not name or not email or "@" not in email:
        flash("Please provide a valid name and email address.", "danger")
        return redirect(url_for("survey"))
    
    active_questions = fetch_all_questions(only_active=True)
    responses_dict = {}
    missing_required = []
    
    for q in active_questions:
        q_id = q.get("id")
        q_type = q.get("type")
        is_req = q.get("required", False)
        
        if q_type == "checkbox":
            val = request.form.getlist(f"q_{q_id}")
            if is_req and (not val or len(val) == 0):
                missing_required.append(q.get("question"))
            responses_dict[q_id] = val
        else:
            val = request.form.get(f"q_{q_id}", "").strip()
            if is_req and not val:
                missing_required.append(q.get("question"))
            responses_dict[q_id] = val
    
    if missing_required:
        flash(f"Please answer required question: \"{missing_required[0]}\"", "warning")
        return redirect(url_for("survey"))
    
    attachment_path = None
    has_attachment_key = "optional_attachment" in request.files
    uploaded_file = request.files.get("optional_attachment")
    app.logger.info(f"Survey submission: request.files contains 'optional_attachment': {has_attachment_key}")
    
    if uploaded_file and uploaded_file.filename:
        app.logger.info(f"Survey submission: Found file with filename='{uploaded_file.filename}'")
        attachment_path = upload_file_to_azure_files(uploaded_file)
        app.logger.info(f"Survey submission: upload_file_to_azure_files returned path='{attachment_path}'")
    else:
        app.logger.info("Survey submission: No file attached or empty filename.")
    
    response_id = f"resp_{uuid.uuid4().hex[:10]}"
    submission_doc = {
        "id": response_id,
        "name": name,
        "email": email,
        "phone": phone,
        "responses": responses_dict,
        "attachment": attachment_path,
        "submitted_at": datetime.now(timezone.utc).isoformat()
    }
    
    save_response_document(submission_doc)
    app.logger.info(f"Survey submission: Persisted response document '{response_id}' with attachment='{attachment_path}'")
    session["last_submission_id"] = response_id
    return redirect(url_for("result", id=response_id))

@app.route("/result")
def result():
    response_id = request.args.get("id") or session.get("last_submission_id")
    response_doc = fetch_response_by_id(response_id) if response_id else None
    return render_template("result.html", response=response_doc, response_id=response_id)

@app.route("/attachment/<path:filename>")
def view_attachment(filename):
    """Retrieves and streams uploaded attachment from Azure Files or local fallback storage."""
    if not filename:
        abort(404)
    
    # Normalize path and strip folder prefixes
    clean_filename = filename.replace("\\", "/").strip()
    if clean_filename.startswith(f"{AZURE_FILE_SHARE}/"):
        clean_filename = clean_filename[len(AZURE_FILE_SHARE) + 1:]
    elif clean_filename.startswith("uploads/"):
        clean_filename = clean_filename[len("uploads/"):]
    
    # Path traversal protection: isolate base file name
    clean_filename = os.path.basename(clean_filename)
    if not clean_filename or clean_filename in (".", "..") or ".." in clean_filename:
        abort(404)
    
    # Determine MIME type for proper browser rendering (PDFs, images, etc.)
    mime_type, _ = mimetypes.guess_type(clean_filename)
    if not mime_type:
        mime_type = "application/octet-stream"
    
    # 1. Attempt retrieval from Azure Files if configured
    if AZURE_STORAGE_CONNECTION_STRING and not AZURE_STORAGE_CONNECTION_STRING.startswith("<"):
        try:
            from azure.storage.fileshare import ShareServiceClient
            service_client = ShareServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
            share_client = service_client.get_share_client(AZURE_FILE_SHARE)
            file_client = share_client.get_file_client(clean_filename)
            if file_client.exists():
                download_stream = file_client.download_file()
                file_bytes = download_stream.readall()
                return send_file(
                    io.BytesIO(file_bytes),
                    mimetype=mime_type,
                    as_attachment=False,
                    download_name=clean_filename
                )
        except Exception as e:
            app.logger.error(f"Error retrieving attachment from Azure Files: {e}")
    
    # 2. Fallback to local static/uploads storage
    upload_dir = os.path.join(app.root_path, "static", "uploads")
    local_file_path = os.path.join(upload_dir, clean_filename)
    
    # Ensure local path is strictly contained within uploads directory
    try:
        if os.path.commonpath([os.path.abspath(local_file_path), os.path.abspath(upload_dir)]) == os.path.abspath(upload_dir):
            if os.path.isfile(local_file_path):
                return send_file(
                    local_file_path,
                    mimetype=mime_type,
                    as_attachment=False,
                    download_name=clean_filename
                )
    except Exception as e:
        app.logger.error(f"Error retrieving local attachment: {e}")
    
    abort(404)

# ==========================================
# ADMIN DASHBOARD & MANAGEMENT ROUTES
# ==========================================

@app.route("/admin")
@admin_required
def admin_dashboard():
    all_questions = fetch_all_questions(only_active=False)
    active_count = sum(1 for q in all_questions if q.get("active", True))
    inactive_count = len(all_questions) - active_count
    
    responses = fetch_all_responses()
    total_responses = len(responses)
    recent_responses = responses[:5]
    
    stats = {}
    for q in all_questions:
        q_id = q.get("id")
        q_type = q.get("type")
        if q_type in ["radio", "checkbox", "yes_no", "rating"]:
            option_counts = {}
            total_answered = 0
            
            expected_options = list(q.get("options", []))
            if q_type == "yes_no" and not expected_options:
                expected_options = ["Yes", "No"]
            elif q_type == "rating" and not expected_options:
                expected_options = ["1", "2", "3", "4", "5"]
            
            for opt in expected_options:
                option_counts[str(opt)] = 0
            
            for r in responses:
                ans = r.get("responses", {}).get(q_id)
                if ans is not None and ans != "":
                    total_answered += 1
                    if isinstance(ans, list):
                        for item in ans:
                            option_counts[str(item)] = option_counts.get(str(item), 0) + 1
                    else:
                        option_counts[str(ans)] = option_counts.get(str(ans), 0) + 1
            
            breakdown = []
            for opt, cnt in option_counts.items():
                pct = round((cnt / total_answered * 100), 1) if total_answered > 0 else 0
                breakdown.append({"option": opt, "count": cnt, "percent": pct})
            
            stats[q_id] = {
                "question": q.get("question"),
                "type": q_type,
                "total_answered": total_answered,
                "breakdown": breakdown
            }
    
    return render_template(
        "admin/dashboard.html",
        total_questions=len(all_questions),
        active_count=active_count,
        inactive_count=inactive_count,
        total_responses=total_responses,
        recent_responses=recent_responses,
        stats=stats
    )

@app.route("/admin/questions")
@admin_required
def admin_questions():
    questions = fetch_all_questions(only_active=False)
    return render_template("admin/questions.html", questions=questions)

@app.route("/admin/questions/add", methods=["GET", "POST"])
@admin_required
def admin_add_question():
    if request.method == "POST":
        q_text = request.form.get("question_text", "").strip()
        q_type = request.form.get("question_type", "radio").strip()
        is_required = bool(request.form.get("is_required"))
        is_active = bool(request.form.get("is_active"))
        
        options_raw = request.form.getlist("options[]")
        options = [opt.strip() for opt in options_raw if opt.strip()]
        
        if q_type == "yes_no" and not options:
            options = ["Yes", "No"]
        elif q_type == "rating" and not options:
            options = ["1", "2", "3", "4", "5"]
        
        if not q_text:
            flash("Question text cannot be empty.", "warning")
            return render_template("admin/add_question.html")
        
        existing_questions = fetch_all_questions()
        next_order = max([q.get("display_order", 0) for q in existing_questions], default=0) + 1
        
        new_id = f"q_{uuid.uuid4().hex[:6]}"
        question_doc = {
            "id": new_id,
            "question": q_text,
            "type": q_type,
            "options": options,
            "required": is_required,
            "active": is_active,
            "display_order": next_order
        }
        
        save_question_document(question_doc, is_new=True)
        flash("Question created successfully.", "success")
        return redirect(url_for("admin_questions"))
    
    return render_template("admin/add_question.html")

@app.route("/admin/questions/edit/<question_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_question(question_id):
    question = fetch_question_by_id(question_id)
    if not question:
        flash("Question not found.", "danger")
        return redirect(url_for("admin_questions"))
    
    if request.method == "POST":
        q_text = request.form.get("question_text", "").strip()
        q_type = request.form.get("question_type", question.get("type", "radio")).strip()
        is_required = bool(request.form.get("is_required"))
        is_active = bool(request.form.get("is_active"))
        display_order = int(request.form.get("display_order", question.get("display_order", 1)))
        
        options_raw = request.form.getlist("options[]")
        options = [opt.strip() for opt in options_raw if opt.strip()]
        
        if q_type == "yes_no" and not options:
            options = ["Yes", "No"]
        elif q_type == "rating" and not options:
            options = ["1", "2", "3", "4", "5"]
        
        if not q_text:
            flash("Question text cannot be empty.", "warning")
            return render_template("admin/edit_question.html", question=question)
        
        question["question"] = q_text
        question["type"] = q_type
        question["options"] = options
        question["required"] = is_required
        question["active"] = is_active
        question["display_order"] = display_order
        
        save_question_document(question, is_new=False)
        flash("Question updated successfully.", "success")
        return redirect(url_for("admin_questions"))
    
    return render_template("admin/edit_question.html", question=question)

@app.route("/admin/questions/delete/<question_id>", methods=["POST"])
@admin_required
def admin_delete_question(question_id):
    delete_question_document(question_id)
    flash("Question removed successfully.", "info")
    return redirect(url_for("admin_questions"))

@app.route("/admin/questions/toggle/<question_id>", methods=["POST"])
@admin_required
def admin_toggle_question(question_id):
    q = fetch_question_by_id(question_id)
    if q:
        q["active"] = not q.get("active", True)
        save_question_document(q, is_new=False)
        status_str = "activated" if q["active"] else "deactivated"
        flash(f"Question has been {status_str}.", "success")
    return redirect(url_for("admin_questions"))

@app.route("/admin/questions/move/<question_id>/<direction>", methods=["POST"])
@admin_required
def admin_move_question(question_id, direction):
    questions = fetch_all_questions()
    idx = next((i for i, q in enumerate(questions) if q.get("id") == question_id), -1)
    
    if idx != -1:
        target_idx = idx - 1 if direction == "up" else idx + 1
        if 0 <= target_idx < len(questions):
            order_curr = questions[idx].get("display_order", idx + 1)
            order_target = questions[target_idx].get("display_order", target_idx + 1)
            
            if order_curr == order_target:
                order_curr, order_target = idx + 1, target_idx + 1
            
            questions[idx]["display_order"] = order_target
            questions[target_idx]["display_order"] = order_curr
            
            save_question_document(questions[idx], is_new=False)
            save_question_document(questions[target_idx], is_new=False)
            flash("Question order updated.", "success")
            
    return redirect(url_for("admin_questions"))

@app.route("/admin/responses")
@admin_required
def admin_responses():
    responses = fetch_all_responses()
    return render_template("admin/responses.html", responses=responses)

@app.route("/admin/responses/<response_id>")
@admin_required
def admin_response_detail(response_id):
    response = fetch_response_by_id(response_id)
    if not response:
        flash("Response record not found.", "warning")
        return redirect(url_for("admin_responses"))
    
    questions = fetch_all_questions(only_active=False)
    q_map = {q.get("id"): q for q in questions}
    
    parsed_answers = []
    for q_id, ans in response.get("responses", {}).items():
        q_obj = q_map.get(q_id, {})
        parsed_answers.append({
            "question_id": q_id,
            "question_text": q_obj.get("question", f"Question ID: {q_id}"),
            "type": q_obj.get("type", "text"),
            "answer": ans
        })
    
    return render_template(
        "admin/response_detail.html",
        response=response,
        parsed_answers=parsed_answers
    )

@app.errorhandler(404)
def not_found_error(error):
    return render_template("error.html", error_code=404, error_message="Page Not Found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template("error.html", error_code=500, error_message="Internal Application Error"), 500

if __name__ == "__main__":
    os.makedirs(os.path.join(app.root_path, "static", "uploads"), exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
