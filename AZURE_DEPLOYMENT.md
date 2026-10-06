# Azure Cloud Deployment & Architecture Guide

This guide provides step-by-step instructions for deploying the **Online Survey Application** to Microsoft Azure using the Azure Portal and Azure CLI.

---

## 1. Cloud Architecture Overview

| Azure Resource | Resource Type | Purpose in Application |
| :--- | :--- | :--- |
| **Azure Container Apps** | Serverless Container | Hosts and executes the containerized Flask/Gunicorn application. |
| **Azure Container Registry (ACR)** | Container Registry (`onlinesurveyacr2026`) | Stores and versions Docker container images. |
| **Azure Cosmos DB (NoSQL)** | Managed NoSQL Database (`SurveyDB`) | Stores survey questions (`Questions`) and user submissions (`Responses`). |
| **Azure Files** | Managed File Share (`surveyfiles`) | Stores user feedback file attachments (images, PDFs, documents). |
| **Microsoft Entra ID** | Identity & Access Management | Handles secure user authentication (OAuth 2.0 / OpenID Connect) and Admin RBAC. |

---

## 2. Step-by-Step Azure Resource Configuration

### Step A: Azure Cosmos DB for NoSQL
1. In the Azure Portal, create an **Azure Cosmos DB for NoSQL** account:
   - Account Name: `online-survey-rg` (or your chosen account name).
   - Capacity mode: **Serverless** or **Provisioned throughput**.
2. Create a Database:
   - Database ID: `SurveyDB`
3. Create two Containers inside `SurveyDB`:
   - Container 1: `Questions`, Partition Key: `/id`
   - Container 2: `Responses`, Partition Key: `/id`
4. Under **Settings &rarr; Keys**, copy:
   - **URI** &rarr; Set as `COSMOS_ENDPOINT`
   - **PRIMARY KEY** &rarr; Set as `COSMOS_KEY`

---

### Step B: Azure Storage Account & Azure Files
1. Create a standard Azure Storage Account (e.g., `surveystorage2026`).
2. Navigate to **Data storage &rarr; File shares**:
   - Click **+ File share**.
   - Name: `surveyfiles`.
3. Under **Security + networking &rarr; Access keys**, copy:
   - **Connection string** &rarr; Set as `AZURE_STORAGE_CONNECTION_STRING`

---

### Step C: Microsoft Entra ID App Registration
1. In the Azure Portal, search for **Microsoft Entra ID** &rarr; **App registrations** &rarr; **+ New registration**.
   - Name: `Online Survey Application`
   - Supported account types: **Accounts in this organizational directory only** (Single tenant) or Multitenant as preferred.
   - Redirect URI: Web &rarr; `https://<your-container-app-url>/auth/callback` (or `http://localhost:5000/auth/callback` for local testing).
2. Note down:
   - **Application (client) ID** &rarr; `CLIENT_ID`
   - **Directory (tenant) ID** &rarr; `TENANT_ID`
3. Under **Certificates & secrets** &rarr; **+ New client secret**:
   - Add a description and copy the **Value** &rarr; `CLIENT_SECRET`
4. Under **API permissions**, ensure `Microsoft Graph` &rarr; `User.Read` (Delegated) is enabled.

---

### Step D: Build & Push Docker Image to Azure Container Registry (ACR)

Using your Azure CLI or PowerShell:

```bash
# 1. Log in to Azure
az login

# 2. Set your active subscription
az account set --subscription "<Your-Subscription-ID>"

# 3. Build and push image directly in the cloud using ACR Tasks (no local docker daemon required)
az acr build --registry onlinesurveyacr2026 --image onlinesurvey:v1 .
```

*Alternatively, with local Docker:*
```bash
az acr login --name onlinesurveyacr2026
docker build -t onlinesurveyacr2026.azurecr.io/onlinesurvey:v1 .
docker push onlinesurveyacr2026.azurecr.io/onlinesurvey:v1
```

---

### Step E: Create & Configure Azure Container Apps

1. In the Azure Portal, search for **Container Apps** &rarr; **+ Create**.
   - Environment: Create or select a Container Apps Environment.
   - Container Image:
     - Registry: `onlinesurveyacr2026.azurecr.io`
     - Image: `onlinesurvey`
     - Tag: `v1`
2. **Ingress Configuration**:
   - Ingress: **Enabled**
   - Target Port: **`5000`**
   - Ingress Type: **Accepting traffic from anywhere** (External)
   - Transport: **Auto** or **HTTP/1.1**
3. **Secrets & Environment Variables**:

Configure secrets under **Secrets**:
| Secret Name | Value |
| :--- | :--- |
| `cosmos-key` | `<your-cosmos-db-primary-key>` |
| `storage-conn-str` | `<your-storage-connection-string>` |
| `entra-client-secret` | `<your-entra-client-secret>` |
| `flask-secret-key` | `<a-strong-random-string>` |

Configure Environment Variables under **Containers &rarr; Environment variables**:
| Name | Type | Value / Reference |
| :--- | :--- | :--- |
| `COSMOS_ENDPOINT` | Manual | `https://online-survey-rg.documents.azure.com:443/` |
| `COSMOS_DATABASE` | Manual | `SurveyDB` |
| `COSMOS_QUESTIONS_CONTAINER` | Manual | `Questions` |
| `COSMOS_RESPONSES_CONTAINER` | Manual | `Responses` |
| `COSMOS_KEY` | Secret Reference | `cosmos-key` |
| `AZURE_FILE_SHARE` | Manual | `surveyfiles` |
| `AZURE_STORAGE_CONNECTION_STRING` | Secret Reference | `storage-conn-str` |
| `CLIENT_ID` | Manual | `<your-client-id>` |
| `TENANT_ID` | Manual | `<your-tenant-id>` |
| `CLIENT_SECRET` | Secret Reference | `entra-client-secret` |
| `REDIRECT_URI` | Manual | `https://<your-container-app-domain>/auth/callback` |
| `ADMIN_EMAILS` | Manual | `admin@example.com,your-email@outlook.com` |
| `FLASK_SECRET_KEY` | Secret Reference | `flask-secret-key` |

4. Click **Review + create** &rarr; **Create**.

---

### Step F: Update Microsoft Entra Redirect URI
Once the Container App is deployed, copy its **Application URL** (e.g., `https://survey-app.yellowisland-xxxx.eastus.azurecontainerapps.io`).

1. Go to **Microsoft Entra ID** &rarr; **App registrations** &rarr; `Online Survey Application`.
2. Under **Authentication** &rarr; **Web** &rarr; **Redirect URIs**:
   - Add: `https://<your-container-app-domain>/auth/callback`
3. Save changes.

---

## 3. How the Application Works Under the Hood

### 1. Cosmos DB Data Flow
- Upon startup or first request, `app.py` checks if the `Questions` container is populated. If empty, it automatically seeds the initial 10 customer experience questions.
- When an end-user navigates to `/survey`, the app queries `SELECT * FROM c WHERE c.active = true ORDER BY c.display_order ASC`.
- When an admin adds or modifies questions at `/admin/questions`, Cosmos DB documents are updated dynamically via `upsert_item`.
- When a user submits their answers at `/submit`, a document is persisted into the `Responses` container.

### 2. Azure Files Attachment Flow
- If a customer uploads an image/document with their response, the server streams the file directly into Azure File Share (`surveyfiles`) using the `azure-storage-file-share` SDK.
- The unique path is referenced in the Cosmos DB response record.

### 3. Microsoft Entra ID Authentication Flow
- User clicks "Sign In" &rarr; MSAL generates authorization URL with `User.Read` scope.
- User signs in on Microsoft's portal &rarr; redirected back to `/auth/callback` with auth code.
- MSAL exchanges auth code for ID token & access token.
- Session is established and `ADMIN_EMAILS` is checked to authorize access to `/admin`.

---

## 4. Verification & Testing

1. Open `https://<your-container-app-domain>/` &rarr; Landing page loads cleanly.
2. Open `/survey` &rarr; 10 default customer experience questions load dynamically from Cosmos DB.
3. Submit a response &rarr; Confirmation page shows unique Response ID.
4. Sign in with admin email &rarr; Access `/admin` dashboard.
5. Add/Edit a question in `/admin/questions` &rarr; Revisit `/survey` to verify dynamic update.
