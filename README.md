# Unauthorized Entry

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://reactjs.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000)](https://flask.palletsprojects.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8)](https://opencv.org/)

A professional security monitoring and access-verification platform built with Python, Flask, OpenCV, React, and facial recognition technology. The system identifies people in a live camera stream, compares them with known records, logs outcomes, and raises alerts for suspicious or unauthorized access. It combines a real-time camera pipeline with a polished web dashboard for administrators and security operators.

<p align="center">
  <img src="test_snapshot.jpg" alt="Unauthorized Entry dashboard preview" width="100%" />
</p>

## 🚀 Features at a Glance

- Live face detection and recognition
- Authorized vs unauthorized access classification
- Admin dashboard for student registration and verification
- Real-time logs, analytics, and incident gallery
- Email and Telegram alert integration
- Camera snapshot and video streaming support

## Quick Start

```powershell
git clone <repository-url>
cd "unauthorized entry"
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install flask flask-cors pymongo opencv-python numpy python-dotenv requests face-recognition
cd frontend
npm install
cd ..
python app.py
```

## Overview

Unauthorized Entry is designed for secure entrances, campus monitoring, and admin-controlled access verification. It brings together:

- Live camera monitoring and face detection
- Recognition for authorized and unauthorized entry
- A polished dashboard for operators and administrators
- Real-time event logging, analytics, and incident review
- Email and Telegram alerting
- Student registration, verification, and roll-based lookups

## Why This Project Matters

This solution is ideal for:

- Campus security and student access control
- Office entrance monitoring
- Visitor verification systems
- Smart surveillance demonstrations
- Research and prototyping around real-time biometric systems
- Lightweight demo deployments for access-management workflows

## Core Features

### 1. Intelligent Monitoring
- Continuous camera feed processing
- Face detection and recognition using either an AI-based or lightweight MSE-based approach
- Instant classification into authorized or unauthorized access
- Snapshot and gallery support for flagged incidents
- Recognition results and status updates reflected in the live dashboard

### 2. Admin and Operator Dashboard
- Role-based access for admin and security users
- Student registration through camera capture or image upload
- Roll-number verification and student lookup
- Modern UI panels for live feed, logs, alerts, and analytics
- Voice-guided experience and animated dashboard components

### 3. Alerting and Notifications
- Email notifications for suspicious entry attempts
- Telegram alert delivery with image support
- Cooldown logic to reduce repeated alerts
- Built-in test endpoints for notification validation
- Support for demo reset and alert reconfiguration

### 4. Analytics and Reporting
- Recent access logs
- Trend visualization for incident activity
- Unauthorized event gallery for review
- AI-generated observation summaries for security context
- Optional report export and storage in the ai_reports directory

## Application Architecture

The project is organized into three main layers:

1. Backend service
   - Flask application in [app.py](app.py)
   - Authentication, REST routes, logging, alert orchestration, and camera endpoints
   - Supports SQLite fallback and optional MongoDB persistence

2. Recognition engine
   - [ai_model.py](ai_model.py) for AI-based recognition
   - [mse_model.py](mse_model.py) for a lightweight fallback approach
   - [ai/afferens.py](ai/afferens.py) for alert message generation and report management
   - Face images are stored under the known_faces and alumni_faces directories

3. Frontend experience
   - React-based dashboard in [frontend/src](frontend/src)
   - Modern glass-style interface with live monitoring widgets, forms, charts, and gallery panels

## Technology Stack

### Backend
- Python
- Flask
- Flask-CORS
- OpenCV
- NumPy
- face_recognition
- SQLite or MongoDB support
- Requests

### Frontend
- React
- Axios
- Framer Motion
- Recharts
- React Icons

## Project Structure

```text
.
├── app.py                  # Main Flask backend
├── ai_model.py             # AI face recognition flow
├── mse_model.py            # Lightweight fallback recognition model
├── main.py                 # Standalone monitoring script
├── log.txt                 # Activity log output
├── tests/                  # Alert and detection tests
├── alerts/                 # Email and Telegram modules
├── ai/                     # AI reporting utilities
├── frontend/               # React dashboard application
├── known_faces/            # Registered face images
├── unauthorized/           # Captured unauthorized images
├── alumni_faces/           # Alumni/student registration images
└── ai_reports/             # AI-generated reports
```

## Installation

### Prerequisites
- Python 3.9+
- Node.js 18+
- A working webcam
- Optional: MongoDB server (SQLite works as a fallback)

### 1. Clone the Repository

```powershell
git clone <repository-url>
cd "unauthorized entry"
```

### 2. Create a Python Environment

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Python Dependencies

```powershell
pip install flask flask-cors pymongo opencv-python numpy python-dotenv requests face-recognition
```

### 4. Install Frontend Dependencies

```powershell
cd frontend
npm install
cd ..
```

## Configuration

Create a .env file in the project root:

```env
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
ADMIN_EMAIL=admin@example.com
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
MONGO_URI=mongodb://localhost:27017
```

> Email and Telegram alerts are optional. The system will continue to function without them.

## Afferens / AI Reporting Note

The current implementation of the Afferens-based reporting flow does not use any external API key or cloud service. It generates observation summaries and alert content locally inside the project using the logic in [ai/afferens.py](ai/afferens.py). If you later connect this module to an external AI service, you can add the required credentials to your environment variables at that time.

## Running the Application

### Start the Backend

```powershell
python app.py
```

Backend URL:
- http://127.0.0.1:5000

### Start the Frontend

```powershell
cd frontend
npm start
```

The React dashboard will open in the browser and connect to the backend API. If the camera is unavailable, the system will still serve the UI and show a placeholder preview.

## Default Login

For local testing, the system creates an admin account automatically:

- Username: admin
- Password: admin123

## How It Works

1. The camera feed is captured continuously from the local device.
2. Each frame is analyzed for faces.
3. Detected faces are matched against known images stored in the project directories.
4. Authorized users are marked as recognized, while unknown persons are flagged.
5. Alerts, logs, and snapshots are generated for suspicious incidents.
6. The dashboard updates the live status, unauthorized gallery, analytics panels, and admin controls in real time.

## API Highlights

The backend exposes routes for:

- Authentication: /login, /logout, /me
- Dashboard data: /logs, /status, /trend
- Student management: /add_student, /verify
- Alert controls: /settings/alerts, /test/email, /test/telegram
- Camera endpoints: /snapshot, /video, /video_feed
- Gallery access: /unauthorized-gallery, /unauthorized-image/<filename>

## Screenshots

The dashboard preview included above provides a clear view of the interface and its live monitoring experience.

- Main UI preview: [test_snapshot.jpg](test_snapshot.jpg)
- Sample known face image: [known_faces/TEAM.jpg](known_faces/TEAM.jpg)
- Additional generated reports and flagged images are stored in [ai_reports](ai_reports) and [unauthorized](unauthorized)

## Testing

Run the test suite with:

```powershell
pytest -q
```

## Notes

- Recognition accuracy depends on camera quality, lighting, and the quality of stored face images.
- The system is suitable for demonstration and controlled environments.
- For production deployment, use stronger security practices, secrets management, and a hardened hosting setup.
- The current release is designed as a polished prototype and can be extended for enterprise-grade access control workflows.

## License

This project is intended for educational, prototyping, and security demonstration use.
