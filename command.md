# Practical 9: Step-by-Step Command & Setup Guide

This guide contains every exact command required to run and demonstrate the DevSecOps practical from start to finish on Windows (PowerShell), macOS, or Linux.

---

## 0. Prerequisites & Tool Installation

Ensure you have the following tools installed. Run these verification commands:

```powershell
docker --version
kubectl version --client
kind --version
helm version
git --version
```

### Installation (if missing on Windows):
Using **Winget** (Windows Package Manager) in PowerShell (Admin):
```powershell
winget install Docker.DockerDesktop
winget install Kubernetes.kubectl
winget install Kubernetes.kind
winget install Helm.Helm
```
*(After installing Docker Desktop, open Docker Desktop and wait until the status displays "Docker Desktop is running".)*

---

## 1. Setup GitHub Repository & Slack Alert Webhook

### Step 1.1: Create your Personal GitHub Repository
1. Go to [GitHub.com](https://github.com) -> Click **New Repository**.
2. Name it `devsecops-demo` (can be **Public** or **Private**).
3. **Do NOT** initialize with a README, .gitignore, or license (we already have files locally).
4. Click **Create repository**.

### Step 1.2: Create the Slack Webhook (5 Minutes)
1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) -> Click **Create New App** -> Select **From scratch**.
2. Name the app: `devsecops-demo` and select your Slack workspace.
3. In the left sidebar, click **Incoming Webhooks** -> Toggle the switch to **On**.
4. Click **Add New Webhook to Workspace** at the bottom.
5. Select a channel (e.g., `#demo-alerts` or `#general`) and click **Allow**.
6. Copy the generated **Webhook URL** (format: `https://hooks.slack.com/services/T.../B.../...`).

### Step 1.3: Add Slack Webhook to GitHub Actions Secrets
1. In your newly created GitHub repository, click **Settings** (top tab).
2. In the left sidebar, expand **Secrets and variables** -> Click **Actions**.
3. Click the green button: **New repository secret**.
   - **Name**: `SLACK_WEBHOOK`
   - **Secret**: *(Paste your copied Slack Webhook URL here)*
4. Click **Add secret**.
*(Note: `GITHUB_TOKEN` is built into GitHub Actions automatically; no manual secret needed for Gitleaks).*

---

## 2. Push Code to Your GitHub Repository

In PowerShell inside your project folder (`c:\Users\Dharm\OneDrive\Desktop\CN_DEVOPS\Prac_9`):

```powershell
# Verify git status
git status

# Point origin to your personal repo
git remote set-url origin https://github.com/<YOUR-GITHUB-USERNAME>/devsecops-demo.git

# Or if starting fresh:
git branch -M main
git push -u origin main
```

---

## 3. Live Demonstration Part 1: Observing Pipeline Failures (Security Gates)

### Step 3.1: Trigger Initial Vulnerability Failure (Trivy & Hadolint)
1. By default, `Dockerfile` is unhardened (runs as root without `USER`) and `requirements.txt` contains legacy versions (`Flask 1.1.2`, `Werkzeug 1.0.1`, `Jinja2 2.11.3`) containing known CVEs.
2. Push your initial code to trigger the GitHub Actions pipeline:
```powershell
git add .
git commit -m "chore: initial push with vulnerable baseline"
git push
```
3. Open your repository on GitHub -> Go to the **Actions** tab.
4. Click on the running workflow: **DevSecOps Pipeline**.
5. **Expected Results**:
   - **Hadolint** fails with `DL3002: Last user should not be root`.
   - **Trivy (filesystem scan)** fails detecting `HIGH` and `CRITICAL` vulnerabilities.
   - The build stops at the failing step.
   - Step 7 **Slack alert** triggers (`if: failure()`).
6. Check your Slack channel: You will see the incoming alert:
   > `🚨 DevSecOps pipeline FAILED on <user>/devsecops-demo — commit <sha> by <user>`

---

### Step 3.2: Trigger Secret Leak Detection (Gitleaks)
To demonstrate Gitleaks catching hardcoded credentials:

1. Create a file named `config.py` in the root folder with the following AWS key pattern:
```powershell
Set-Content -Path config.py -Value @'
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
'@
```
2. Commit and push:
```powershell
git add config.py
git commit -m "feat: add cloud storage config"
git push
```
3. Check the **Actions** tab on GitHub:
   - **Gitleaks** fails immediately at Step 1:
     `leaks found: 1 | rule: aws-access-token`
   - The pipeline fails before compiling or running any code.
   - Another Slack notification is dispatched immediately.

---

## 4. Live Demonstration Part 2: Vulnerability Remediation (Going Green)

Now, remediate each issue step-by-step:

### Step 4.1: Remove Leaked Secrets
```powershell
Remove-Item config.py
```

### Step 4.2: Fix Dockerfile (Enforce Non-Root User)
Replace `Dockerfile` with `Dockerfile.fixed`:
```powershell
Copy-Item Dockerfile.fixed Dockerfile
```
*(This adds `RUN adduser ...` and `USER appuser` satisfying Hadolint rule DL3002).*

### Step 4.3: Fix Dependency Vulnerabilities
Replace `requirements.txt` with `requirements.fixed.txt`:
```powershell
Copy-Item requirements.fixed.txt requirements.txt
```

### Step 4.4: Fix SQL Injection in Source Code (`app.py`)
In `app.py` around line 32, replace the raw string concatenation with a parameterized SQL query:
```python
# Before (vulnerable to SQLi CWE-89):
# query = "SELECT id, username, role FROM users WHERE username = '" + name + "'"
# cursor = conn.execute(query)

# After (remediated with parameterized query):
query = "SELECT id, username, role FROM users WHERE username = ?"
cursor = conn.execute(query, (name,))
```
*(Or use PowerShell to automatically apply this fix):*
```powershell
(Get-Content app.py) -replace 'query = "SELECT id, username, role FROM users WHERE username = \''" \+ name \+ "\''"', 'query = "SELECT id, username, role FROM users WHERE username = ?"`n    cursor = conn.execute(query, (name,)) #' | Set-Content app.py
```

### Step 4.5: Commit & Push Remediated Code
```powershell
git add Dockerfile requirements.txt app.py
git commit -m "fix(sec): resolve secret leak, sql injection, cves, and non-root user"
git push
```

### Step 4.6: Verify Green Pipeline
1. Check the GitHub **Actions** tab.
2. Watch all stages turn **GREEN**:
   - `Gitleaks`: No leaks found.
   - `Semgrep`: 0 findings.
   - `Trivy FS`: 0 high/critical CVEs.
   - `Hadolint`: Valid Dockerfile linting passed.
   - `Docker build`: Successful container image build.
   - `Trivy Image Scan`: Container layers verified.
   - `Slack alert`: Skipped (no failures).

---

## 5. Local Kubernetes Cluster & GitOps Setup (ArgoCD)

### Step 5.1: Create Local Kubernetes Cluster with Kind
```powershell
kind create cluster --name devsecops-demo
```
Verify the cluster is active:
```powershell
kubectl cluster-info --context kind-devsecops-demo
kubectl get nodes
```

---

### Step 5.2: Install ArgoCD in Cluster
```powershell
# Create dedicated namespace
kubectl create namespace argocd

# Apply official ArgoCD installation manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Monitor pods until all are Running (wait ~1-2 minutes)
kubectl get pods -n argocd -w
```
*(Press `Ctrl + C` once all ArgoCD pods show status `Running`).*

---

### Step 5.3: Access the ArgoCD Web Dashboard
In a **new PowerShell terminal window**, start port-forwarding:
```powershell
kubectl port-forward svc/argocd-server -n argocd 8080:443
```
*(Keep this terminal open in the background).*

Now, retrieve the auto-generated initial admin password:
```powershell
# PowerShell command to decode initial admin password:
$secret = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($secret))
```

1. Open your browser to: `https://localhost:8080`
2. Accept the self-signed SSL certificate warning (`Advanced` -> `Proceed to localhost`).
3. Username: `admin`
4. Password: *(The decoded string from the command above)*.

---

### Step 5.4: Deploy Application in ArgoCD (GitOps)
You can deploy via the ArgoCD Web UI or CLI:

#### Option A: Via ArgoCD Web UI (Recommended for Viva)
1. Click **+ NEW APP** in the top left.
2. Application Name: `demo-app`
3. Project Name: `default`
4. Sync Policy: `Automatic` (check `Prune Resources` and `Self Heal`).
5. **Source**:
   - Repository URL: `https://github.com/<YOUR-GITHUB-USERNAME>/devsecops-demo.git`
   - Revision: `main`
   - Path: `k8s`
6. **Destination**:
   - Cluster URL: `https://kubernetes.default.svc`
   - Namespace: `default`
7. Click **CREATE**.
8. Click **SYNC** if not automatically syncing.

---

## 6. Kyverno Admission Controller & Policy Enforcement

Kyverno provides runtime defense against unhardened pods entering the cluster.

### Step 6.1: Install Kyverno via Helm
```powershell
# Add Kyverno Helm repository
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update

# Install Kyverno in dedicated namespace
helm install kyverno kyverno/kyverno -n kyverno --create-namespace

# Verify Kyverno admission controller pods are Running
kubectl get pods -n kyverno
```

---

### Step 6.2: Apply the Admission Policy (`disallow-root`)
Deploy the cluster-wide policy:
```powershell
kubectl apply -f kyverno/disallow-root.yaml
```
Verify policy status:
```powershell
kubectl get clusterpolicy
```
Expected output:
```
NAME            BACKGROUND   VALIDATE ACTION   READY   AGE   MESSAGE
disallow-root   false        Enforce           true    15s   Ready
```

---

### Step 6.3: Test Policy Enforcement (Admission Rejection)
Attempt to deploy the intentionally broken deployment ([k8s/deployment.yaml](file:///c:/Users/Dharm/OneDrive/Desktop/CN_DEVOPS/Prac_9/k8s/deployment.yaml)) which lacks `securityContext.runAsNonRoot`:

```powershell
kubectl apply -f k8s/deployment.yaml
```

**Expected Kyverno Block Output**:
```text
Error from server: error when creating "k8s/deployment.yaml": admission webhook "validate.kyverno.svc" denied the request: 

resource Deployment/default/demo-app was blocked by rule "check-runAsNonRoot": 
Running as root is not allowed. Set spec.securityContext.runAsNonRoot: true.
```
*(This proves Kyverno intercepted and blocked the deployment at the API level!)*

---

### Step 6.4: Deploy Compliant Manifest (`deployment.fixed.yaml`)
Now apply the hardened manifest ([k8s/deployment.fixed.yaml](file:///c:/Users/Dharm/OneDrive/Desktop/CN_DEVOPS/Prac_9/k8s/deployment.fixed.yaml)) containing `runAsNonRoot: true`:

```powershell
kubectl apply -f k8s/deployment.fixed.yaml
```

**Expected Output**:
```text
deployment.apps/demo-app created
```

Verify the pods are running securely:
```powershell
kubectl get pods -l app=demo-app
```

---

## 7. Cleanup & Teardown Commands

Once your practical examination and viva demo are finished:

```powershell
# 1. Delete Kind Cluster (removes all containers, ArgoCD, and Kyverno automatically)
kind delete cluster --name devsecops-demo

# 2. Stop any active port-forward terminal tabs (Ctrl + C)

# 3. Clean local git branch if needed
git reset --hard HEAD
```
