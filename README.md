# TransAI - A Multi-Format Document Translation Tool

---

An AI-powered translation tool for various document formats, including DOCX, PPTX, XLSX, TXT, and MD (PDF/OCR planned). The project uses a decoupled frontend/backend architecture with a task queue for efficient and scalable translation services.

> **Documentation Portal**: Please prioritize the latest documents in the `docs/` directory (e.g., `docs/README.md`, `docs/SYSTEM_DOCUMENTATION.md`).

## 🚀 Features
### Latest Updates (2025-08)

- **Batch Translation UI Rework**: Removed redundant cards, keeping only the overall progress bar and action buttons. Status and download links are now shown per-item in the history list.
- **New Batch Management APIs**: Added `POST /api/batch/cancel/{batch_id}` and `POST /api/batch/prune/{batch_id}`.
- **PPTX Stability Fix**: Resolved a parameter conflict error during PPTX processing.
- **XLSX Quality Boost**: Implemented a "post-translation language check + secondary forced translation" step, significantly reducing target language drift caused by mixed-language contexts.
- **Frontend Console Cleanup**: Removed excessive debugging logs.

- **Multi-Format Support**: DOCX, PPTX, XLSX, TXT, MD (PDF & OCR coming soon).
- **Multi-Engine Support**: Qwen, DeepSeek, Tencent, Kimi, Youdao (extensible).
- **Intelligent Translation**: Supports batch JSON translation for improved efficiency.
- **User Management**: User registration, login, and role-based access control (Admin/User).
- **History Tracking**: Save, query, and delete translation history with user-based permissions. Supports per-user limits for text/document history and daily auto-cleanup of expired files/content.
- **Real-time Progress**: Live progress display for translation tasks.
- **File Downloads**: Download translated documents in various formats.
- **Terminology Management**: Maintain a glossary to ensure translation consistency.
- **Multi-language Support**: Supports Chinese, English, Japanese, Korean, and more.

## 👥 Default Accounts

### Admin Account
- **Username**: `admin`
- **Password**: `admin123`
- **Role**: Administrator
- **Permissions**: Can view all users' translation history, manage engine settings, and configure system parameters.

### Test Account
- **Username**: `testuser`
- **Password**: `testpass`
- **Role**: User
- **Permissions**: Can only view their own translation history.

## 🛠️ Quick Start

### 1. Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- At least 2GB of available RAM

### 2. Launch Services

```bash
# Clone the project
git clone <repository-url>
cd transai

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View service logs
docker-compose logs -f backend
```

### 3. Access the Application (Default for Dev)

- **Frontend UI**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Task Monitor**: http://localhost:8000/monitor

### 4. Log In (Default Account)

Use the default admin account to log in:
- **Username**: `admin`
- **Password**: `admin123`

## 🏗️ Tech Stack

### Frontend
- **Framework**: Vue 3 + Composition API
- **UI Library**: Element Plus
- **State Management**: Vue 3 Reactive
- **HTTP Client**: Axios
- **Build Tool**: Vite

### Backend
- **Framework**: FastAPI + Python 3.9+
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL (Production) / SQLite (Development)
- **Task Queue**: Celery + Redis
- **Authentication**: JWT + bcrypt
- **API Docs**: OpenAPI/Swagger

### AI Translation Engines
- **DeepSeek**: (Optional JSON mode; supports fault-tolerant object/array parsing)
- **Tencent**: (Enable by configuring credentials)
- **Kimi**: (Enable by configuring credentials)
- **Youdao**: (Enable by configuring credentials)

### Deployment Architecture
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx (Production)
- **Database**: PostgreSQL + Redis
- **File Storage**: Local filesystem
- **Monitoring**: Built-in health checks

## ⚙️ Configuration

### Environment Variables (Excerpt)

```bash
# Database Config
DATABASE_URL=postgresql://user:password@localhost/dbname
POSTGRES_DB=transai
POSTGRES_USER=transai_user
POSTGRES_PASSWORD=your_password

## DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_USE_JSON_FORMAT=true  # Can be toggled in system settings
DEEPSEEK_JSON_BATCH_SIZE=50

## Tencent
TENCENT_SECRET_ID=...
TENCENT_SECRET_KEY=...
TENCENT_REGION=ap-beijing

## Kimi
KIMI_API_KEY=...
KIMI_API_URL=https://api.moonshot.cn/v1/chat/completions

## Youdao
YOUDAO_APP_ID=...
YOUDAO_APP_SECRET=...

# Security
SECRET_KEY=your_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Service Ports
BACKEND_PORT=8000
FRONTEND_PORT=5173
WORKER_CONCURRENCY=2
```

### Why DeepSeek JSON Format is Default

The project supports both text and JSON modes for DeepSeek (toggleable in system settings). The advantages of JSON mode are:
- **Batch Processing**: Translate up to 50 text segments simultaneously.
- **Structured Output**: JSON format ensures consistent translation results.
- **Error Handling**: Better mechanisms for error identification and handling.
- **Performance**: Reduces the number of API calls, improving efficiency.

## 🔧 Development Guide

### Database Initialization

On startup, the application automatically:
1. Creates the database table structure.
2. Creates the default admin user account.
3. Initializes necessary settings (history limits, deletion policies, retention days, terminology toggle, etc.).

### User Permission System

- **admin**: Can view all records, manage settings, and configure engine parameters.
- **user**: Can only view their own records and use the translation service.

### Translation Workflow

1. **File Upload**: Drag-and-drop or click to upload.
2. **Format Detection**: Automatically identifies the document format.
3. **Content Extraction**: Extracts translatable text from the document.
4. **Batch Translation**: Translates the content using an AI engine.
5. **Result Generation**: Creates the translated document.
6. **File Download**: Provides the translated file for download.

### History & Cleanup (New)
- **Text Deletion**: Clears `source_text`/`translated_text` but retains metadata (language, engine, time, stats).
- **Document Deletion**: Deletes source (uploads) and result (downloads) files, clears `file_name`/`result_path`, but retains the record and stats.
- **Per-User History Limits**: Configurable limits for text/document history. A `409 Conflict` is returned if the limit is reached.
- **Scheduled Cleanup**: A daily job cleans up expired files/content based on retention days set in system settings.

### Translation Strategies
The project supports multiple strategies and automatically selects the best one based on the document type:
- `ooxml_direct`: Directly parses Office Open XML formats, preserving original styling.
- `text_direct`: High-efficiency processing for plain text documents.
- `aspose`: Optional document processing via the Aspose cloud service.

## 🚀 Deployment

### Development Environment

```bash
# Use the development configuration
docker-compose -f docker-compose.dev.yml up -d
```

### Production Environment

```bash
# Use the production configuration
docker-compose -f docker-compose.prod.yml up -d

# Configure environment variables
cp .env.example .env
# Edit the .env file with your production parameters
```

## 📁 Project Structure (Key Paths)

```
transai/
├── frontend/                 # Vue 3 Frontend App
│   ├── src/
│   │   ├── components/      # Vue components
│   │   └── ...
├── backend/                  # FastAPI Backend App
│   ├── app/
│   │   ├── services/        # Business logic
│   │   ├── models/          # Data models
│   │   └── ...
├── docker-compose.yml        # Docker orchestration
├── uploads/                  # Uploaded files
├── downloads/                # Translated files
└── README.md                 # Project documentation
```

## 🔍 Troubleshooting

### Common Issues

1. **Service Fails to Start**: Check Docker and Docker Compose versions.
2. **Database Connection Error**: Verify PostgreSQL service status and connection parameters.
3. **Translation Fails**: Check the API key configurations for the AI engines.
4. **File Upload Fails**: Confirm file format support and size limits.

### Viewing Logs

```bash
# View backend logs
docker-compose logs -f backend

# View worker logs
docker-compose logs -f worker
```

### Health Checks

```bash
# Check API status
curl http://localhost:8000/health

# Check database connection
curl http://localhost:8000/api/health/db
```

## 📚 Documentation

For detailed architecture and usage guides, please refer to the documents in the `docs/` directory.

## 🤝 Contributing Guide

We welcome issues and pull requests to improve the project!

## 📄 License
This project is dual-licensed:
- **Non-Commercial Use**: Licensed under the [GNU General Public License v3.0](LICENSE).
- **Commercial Use**: Please contact us for a commercial license.

## 📞 Contact

- Submit a GitHub Issue
- Email the project maintainer

---

**TransAI** - Making document translation smarter and more efficient! 🚀
