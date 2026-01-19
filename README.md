# 🚀 Semantic Agent – Workflow Automation with Semantic Kernel

A high-performance automation agent built using **Microsoft Semantic Kernel**, **FastAPI**, and **Pydantic**.  
Designed to orchestrate complex, multi-step workflows—**Assessment → Parsing → Mapping**—for both single requests and batch operations via a queue system.

---

## ✨ Key Features

### 🔄 Workflow Orchestration  
Strict linear workflow: **Assessment → Parsing → Mapping**

### 📦 Batch Processing  
Processes multiple `project_id` + `workbook_id` pairs using a **Queue Plugin**

### 🧠 Semantic Kernel Integration  
AI-powered tool selection, workflow execution, and chat-based interaction

### 🌐 External API Integrations  
- OpenRouter LLM  
- Assessment API  
- Parsing API  
- Mapping API  
- MongoDB Logging API  

### 📝 Centralized Logging  
All workflow results and errors logged to a MongoDB-backed service

---

## 📂 Project Structure

project-root/
│
├── main.py # FastAPI entry point
│
├── kernel/
│ └── kernel_setup.py # Semantic Kernel configuration
│
├── plugins/
│ ├── assessment.py # Assessment logic
│ ├── parsing.py # XML parsing logic
│ ├── mapping.py # Mapping execution
│ └── queue_handler.py # Batch queue processing + logging
│
├── config/
│ ├── settings.py # Env variables (Pydantic Settings)
│ └── prompts.py # SYSTEM_PROMPT for LLM
│
├── models/
│ └── schemas.py # Pydantic request/response models
│
└── services/
└── http_client.py # Shared async httpx client


---

## 📋 Prerequisites

- Python **3.10+**
- OpenRouter API Key  
- Access to: Assessment, Parsing, Mapping, and MongoDB API services

---

## ⚙️ Setup

### 1️⃣ Clone the repository
```bash
git clone <your-repo-url>
cd <project-folder>

2️⃣ Install dependencies
pip install -r requirements.txt

3️⃣ Create a .env file
OPENROUTER_API_KEY=your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

ASSESSMENT_API_URL=http://your-service-url
PARSING_API_URL=http://your-service-url
MAPPING_API_URL=http://your-service-url
MONGODB_LOG_API_URL=http://your-log-service-url

REQUEST_TIMEOUT=60.0

🚀 Running the Application

Start the API server:

python main.py


Server runs at:

http://0.0.0.0:9000

🔌 API Endpoints
1. Batch Invocation — /invoke-batch

Trigger batch processing without the LLM.

POST Body:

{
  "items": [
    {"project_id": "uuid1", "workbook_id": "uuid2"},
    {"project_id": "uuid3", "workbook_id": "uuid4"}
  ]
}

2. AI Chat — /chat

Use natural language; the agent decides single vs batch processing.

POST Body:

{"message": "Process these projects..."}

3. Health Check — /health

Returns kernel and conversation status.

🤖 Workflow Logic
Single Item

Assessment

Parsing

Mapping

Batch Mode

Extract all IDs

Queue processing via process_items_queue

Strict sequential execution

Full logging to MongoDB

⭐ Ideal For

Automated microservice workflows

AI-driven orchestration

Batch processing

Semantic Kernel developers