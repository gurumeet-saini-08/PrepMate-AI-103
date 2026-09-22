# ☁️ Azure Setup & Linking Guide for PrepMate
**Chitkara University / INBIOT | AI-103 Project Guide**

This guide provides step-by-step instructions on how to activate your **Microsoft Azure for Students ($100 credit)** benefit, provision the required Azure AI services, obtain API keys and endpoints from the Azure Portal, and link them to PrepMate.

---

## 📋 Overview of Required Azure Services

PrepMate utilizes two primary Azure AI components corresponding to the **AI Interview Coach (Project #19)** track:

| Service | Purpose | Azure Portal Resource |
| :--- | :--- | :--- |
| **Azure AI Speech** | Voice recording to text (STT) and question vocalization (TTS) | `Speech Services` (under Azure AI Services) |
| **Microsoft Foundry / Azure OpenAI** | Question generation, response correctness evaluation, and adaptive agent logic | `Azure OpenAI` or `Azure AI Foundry` |

---

## Step 1: Activate Microsoft Azure for Students

1. Visit [Azure for Students](https://azure.microsoft.com/en-us/free/students/).
2. Click **Activate Now**.
3. Sign in using your college student email (e.g. `@chitkara.edu.in`).
4. Complete the academic verification. You will receive **$100 in free Azure credits** valid for 12 months with no credit card required.

---

## Step 2: Provision Azure AI Speech Service

1. Open the [Azure Portal](https://portal.azure.com/).
2. In the top search bar, search for **Azure AI services** or **Speech Services** and select **Speech Services**.
3. Click **+ Create**.
4. Fill in the resource details:
   - **Subscription**: `Azure for Students`
   - **Resource Group**: Click *Create new* and name it `prepmate-rg` (or select an existing group).
   - **Region**: Choose a region close to you or with standard availability (e.g., `East US` or `Central India`).
   - **Name**: e.g., `prepmate-speech-service` (must be globally unique).
   - **Pricing Tier**: Select `Free F0` (if available) or `Standard S0`.
5. Click **Review + Create**, then **Create**.
6. Once deployment is complete, click **Go to resource**.
7. In the left-hand navigation under **Resource Management**, click **Keys and Endpoint**.
8. Copy:
   - **KEY 1** (e.g., `7a1b...3f`)
   - **Location/Region** (e.g., `eastus`)

---

## Step 3: Provision Microsoft Foundry / Azure OpenAI

1. In the Azure Portal search bar, search for **Azure OpenAI**.
   *(Alternatively, access the [Azure AI Foundry Portal](https://ai.azure.com/)).*
2. Click **+ Create** -> **Azure OpenAI**.
3. Fill in the basics:
   - **Subscription**: `Azure for Students`
   - **Resource Group**: `prepmate-rg`
   - **Region**: `East US` or `North Central US` (regions with high model quota).
   - **Name**: e.g., `prepmate-openai-instance`.
   - **Pricing Tier**: `Standard S0`.
4. Click **Next** through Network and Tags, then click **Create**.
5. Once created, click **Go to resource**.
6. Under **Resource Management**, click **Keys and Endpoint**:
   - Copy **KEY 1**.
   - Copy **Endpoint** (e.g., `https://prepmate-openai-instance.openai.azure.com/`).

### Deploying the Model:
1. In the overview page, click **Go to Azure AI Foundry portal** (or Azure OpenAI Studio).
2. On the left menu, select **Deployments** (under *Management*).
3. Click **+ Deploy model** -> **Deploy base model**.
4. Select or deploy your model (e.g., **gpt-5-mini**).
5. Set:
   - **Deployment name**: `gpt-5-mini`
   - **Model version**: Latest (default)
6. Click **Deploy**.

---

## Step 4: Link Keys to PrepMate (`.env`)

In the project root directory (`d:\Coding\PrepMate`):

1. Create a file named `.env` by copying `.env.example`:
   ```powershell
   copy .env.example .env
   ```
2. Open `.env` in your editor and paste the keys copied from the Azure Portal:
   ```ini
   # Flask Secret Key
   SECRET_KEY=prepmate-production-key-2026

   # Azure AI Speech Service
   AZURE_SPEECH_KEY=paste_your_copied_speech_key_here
   AZURE_SPEECH_REGION=eastus

   # Microsoft Foundry / Azure OpenAI Service
   AZURE_OPENAI_KEY=paste_your_copied_openai_key_here
   AZURE_OPENAI_ENDPOINT=https://prepmate-openai-instance.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
   AZURE_OPENAI_API_VERSION=2024-08-01-preview

   # Fallback setting (leave true to ensure live presentation never fails)
   ENABLE_FALLBACK_MODE=true
   ```
3. Save the `.env` file.

---

## Step 5: Verify the Live Connection

1. Run the application:
   ```powershell
   python app.py
   ```
2. Open your browser to `http://127.0.0.1:5000`.
3. Observe the **System Status Pill** in the top navigation bar:
   - If connected, it will display: **🟢 Azure Live**
   - If keys are pending, it displays: **🟠 Intelligent Fallback**
4. You can also inspect the JSON diagnostic endpoint anytime at:
   `http://127.0.0.1:5000/api/system-status`

---

## 🛡️ Presentation Safety (Dual-Mode Assurance)

Even if Azure credits expire mid-demo, or internet connection drops in class, PrepMate's built-in **Intelligent Fallback Engine** seamlessly takes over:
- Uses browser native Web Speech API for voice recognition.
- Uses PrepMate's rule-based NLP engine for scoring and adaptive decision making.
- **Your live classroom demonstration will never crash!**
