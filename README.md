# Online Survey Application &bull; Azure Cloud Computing Project

A complete, production-ready, customizable customer survey and feedback platform developed with **Python Flask**, **Azure Cosmos DB for NoSQL**, **Azure Files**, and **Microsoft Entra ID (MSAL)**, containerized with **Docker** and built for **Azure Container Apps**.

---

## 1. Architectural Overview & Viva Concepts

This project demonstrates a cloud-native, decoupled web architecture where survey forms and questions are **100% dynamic**. Question structure, options, ordering, and activation are stored in **Azure Cosmos DB**, allowing business administrators to modify survey questions in real-time through the web UI with **zero code modifications or redeployments**.

```
[ Customer / End-User ] ──────────┐
                                  ▼
[ Administrator ] ───────► [ Microsoft Entra ID ] (OAuth 2.0 / OIDC)
                                  │
                                  ▼
                     [ Azure Container Apps ]
                     (Flask App via Gunicorn)
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
    [ Azure Cosmos DB (NoSQL) ]           [ Azure Files ]
         (Database: SurveyDB)          (File Share: surveyfiles)
     ├── Container: Questions                      │
     └── Container: Responses             (Uploaded Feedback Docs / Images)
```

---

## 2. Key Features

- **Dynamic Question Engine**: Fully data-driven survey powered by Azure Cosmos DB. If an admin adds, edits, deletes, or activates/deactivates a question, the change is reflected immediately on the live survey.
- **Rich Question Types Supported**:
  - `radio`: Single choice multiple choice.
  - `checkbox`: Multi-selection with multiple choices.
  - `yes_no`: Binary Yes/No decision.
  - `rating`: 1 to 5 visual rating scale.
  - `text`: Short text input.
  - `textarea`: Long multi-line feedback.
- **Automatic Seed Initialization**: Automatically initializes the default 10 Customer Experience & Satisfaction Survey questions on the first run if the `Questions` container is empty (prevents duplicates).
- **Azure Files Integration**: Secure upload and storage of feedback attachments (PNG, JPG, PDF, DOCX) directly into Azure File Shares.
- **Enterprise Security**: Single sign-on with Microsoft Entra ID (MSAL) and email-based Role-Based Access Control (RBAC) via `ADMIN_EMAILS`.
- **Admin Dashboard & Analytics**: Metric summary cards (Total Responses, Active Questions, Inactive Questions, Total Questions), dynamic percentage response calculations, question reordering, and submission inspection.
- **Modern & Responsive UI/UX**: Indigo/Purple theme with sticky live completion progress bar, glassmorphism cards, and mobile-friendly design.
- **Zero Hard-Coded Secrets**: Fully configured via environment variables and Container App Secrets.

---

## 3. Project Structure

```
OnlineSurvey/
│
├── app.py                     # Main Flask application & Azure adapters
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Multi-stage production container setup
├── .dockerignore              # Docker build exclusions
├── .gitignore                 # Git ignore rules (protects .env and secrets)
├── .env.example               # Environment variable blueprint
├── README.md                  # Local setup & architecture guide
├── AZURE_DEPLOYMENT.md        # Step-by-step Azure Portal deployment guide
│
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Base layout with navbar, alerts & footer
│   ├── index.html             # Landing page with hero & feature overview
│   ├── login.html             # Microsoft Entra & dev sign-in portal
│   ├── survey.html            # Dynamic survey page with progress bar
│   ├── result.html            # Submission confirmation & reference receipt
│   ├── error.html             # User-friendly error page (404/500)
│   │
│   └── admin/
│       ├── base_admin.html    # Dedicated admin layout
│       ├── dashboard.html     # Metrics & response percentage charts
│       ├── questions.html     # Question table with actions & reordering
│       ├── add_question.html  # Dynamic question creator with option builder
│       ├── edit_question.html # Question editor
│       ├── responses.html     # Submission log table
│       └── response_detail.html # Comprehensive Q&A answer inspector
│
└── static/
    ├── style.css              # Custom CSS design system
    ├── script.js              # Live progress bar & dynamic DOM helpers
    └── uploads/               # Local upload directory (.gitkeep)
```

---

## 4. Local Development Setup

The application works seamlessly in local development. When Azure credentials are not yet specified, it gracefully uses local memory/disk storage for development, and automatically connects to Azure once credentials are provided in `.env`.

### Step 1: Create Virtual Environment

**Windows (PowerShell / Command Prompt):**
```powershell
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```

Edit `.env` with your Azure configuration or leave placeholders for demo mode:
```ini
COSMOS_ENDPOINT=https://online-survey-rg.documents.azure.com:443/
COSMOS_KEY=<your-primary-key>
COSMOS_DATABASE=SurveyDB
COSMOS_QUESTIONS_CONTAINER=Questions
COSMOS_RESPONSES_CONTAINER=Responses

AZURE_STORAGE_CONNECTION_STRING=<your-connection-string>
AZURE_FILE_SHARE=surveyfiles

CLIENT_ID=<your-entra-client-id>
CLIENT_SECRET=<your-entra-client-secret>
TENANT_ID=<your-entra-tenant-id>
REDIRECT_URI=http://localhost:5000/auth/callback

ADMIN_EMAILS=admin@example.com
FLASK_SECRET_KEY=dev-secret-key-2026
```

### Step 4: Run the Application

```bash
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 5. Running with Docker Locally

```bash
# Build the Docker image
docker build -t onlinesurvey:latest .

# Run the container locally
docker run -p 5000:5000 --env-file .env onlinesurvey:latest
```

Open: `http://127.0.0.1:5000`

---

## 6. Testing Key Application Scenarios

1. **Take Survey**: Visit `/survey`, fill in customer details, answer the 10 questions, optionally attach a file, and click **Submit Response**.
2. **Dynamic Admin Customization**:
   - Log in at `/login` (use Demo login `admin@example.com` or Microsoft Entra ID).
   - Navigate to `/admin/questions`.
   - Click **+ Add New Question**, choose Question Type `radio`, add choices, and click Save.
   - Go to `/survey` — the new question appears immediately!
   - Click **Edit** or toggle **Status** (Active/Inactive) — the live survey updates instantly without touching code.
3. **Response Analytics**:
   - Go to `/admin`.
   - View the calculated percentage distributions, count per option, and total submissions.
   - Click **Responses** &rarr; **View Details** to inspect an individual customer's submitted answers.
