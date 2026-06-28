from flask import Flask, request, jsonify, Response, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import cv2
import numpy as np
import os
import sqlite3
import threading
import time
import warnings
import json
import base64
import requests
from datetime import datetime, timedelta

def load_env_file(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.strip().startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.strip().split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ[key] = value

try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(env_path)
except ImportError:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        print("[ENV] python-dotenv not installed, manually loading .env")
        load_env_file(env_path)

from alerts.email_service import send_security_alert
from alerts.telegram import send_telegram_alert, send_telegram_image, validate_telegram_credentials
from ai.afferens import build_alert_message, generate_ai_observation, save_ai_report, should_send_alert

warnings.filterwarnings("ignore", category=UserWarning, module="face_recognition_models")

warnings.filterwarnings("ignore", category=UserWarning, module="face_recognition_models")

MODE = "MSE"  # Change to "AI" if you want to use AI model (requires face_recognition)

if MODE == "AI":
    import ai_model
    face_cascade = None
else:
    import mse_model
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

app = Flask(__name__, static_folder="frontend/build", static_url_path="")
CORS(app, supports_credentials=True)
app.secret_key = 'your-secret-key-change-this-in-production'
app.config.update({
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'SESSION_COOKIE_SECURE': False,
    'PERMANENT_SESSION_LIFETIME': timedelta(days=7),
})

BUILD_DIR = os.path.join(app.root_path, "frontend", "build")

# MongoDB Configuration
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://raghava3113:Thaanunenu@cluster0.bkbjf4r.mongodb.net/?appName=Cluster0"
)
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.security_db
    # Test the connection
    client.admin.command("ping")
except (ConnectionFailure, Exception):
    client = None
    db = None

MODE = "MSE"  # or "AI"

# Detection cooldown to prevent duplicate entries
detection_cooldown = {}  # {name: last_detection_time}
email_alerts_enabled = bool(EMAIL_ADDRESS and EMAIL_PASSWORD and ADMIN_EMAIL)


def is_telegram_configured() -> bool:
    from alerts.telegram import get_telegram_settings
    token, chat_id = get_telegram_settings()
    valid, _ = validate_telegram_credentials(token, chat_id)
    return valid


telegram_alerts_enabled = is_telegram_configured()
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def no_cache_response(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.after_request
def apply_no_cache_headers(response):
    if request.path.startswith("/static") or request.path in ["/", "/index.html", "/manifest.json", "/favicon.ico"]:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def require_auth(f):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def hash_password(password):
    return generate_password_hash(password)

def verify_password(hashed, password):
    return check_password_hash(hashed, password)

def open_camera():
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_VFW, cv2.CAP_ANY]
    for idx in range(5):
        for backend in backends:
            cap = cv2.VideoCapture(idx, backend)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                try:
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                except Exception:
                    pass
                return cap
            cap.release()
    return None

camera = open_camera()
output_frame = None
frame_lock = threading.Lock()
last_saved = 0
latest_detection_status = "Monitoring"
latest_ai_observation = None
latest_ai_report_path = None
last_alert_time = {}
face_reload_timestamp = 0

if not os.path.exists("unauthorized"):
    os.makedirs("unauthorized")

if not os.path.exists("alumni_faces"):
    os.makedirs("alumni_faces")


def reload_known_faces():
    global face_reload_timestamp
    try:
        if MODE == "AI" and 'ai_model' in globals() and hasattr(ai_model, "reload_faces"):
            ai_model.reload_faces()
            face_reload_timestamp = time.time()
        elif MODE == "MSE" and 'mse_model' in globals() and hasattr(mse_model, "reload_faces"):
            mse_model.reload_faces()
            face_reload_timestamp = time.time()
        
        # Ensure database records exist for all known faces
        ensure_known_face_records()
    except Exception as e:
        print(f"[RELOAD] Failed to reload known faces: {e}")


def ensure_known_face_records():
    """Ensure all known face files have corresponding database records"""
    if not os.path.exists("known_faces"):
        return
    
    for filename in os.listdir("known_faces"):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            continue
        
        name = filename.rsplit(".", 1)[0]
        
        if db is not None:
            existing = db.students.find_one({"name": name, "status": "PRESENT"})
            if not existing:
                roll = f"{name[:3].lower()}{len(list(db.students.find())) + 1:03d}"
                db.students.update_one(
                    {"name": name},
                    {"$set": {
                        "status": "PRESENT",
                        "enrollment_date": datetime.now().strftime("%Y-%m-%d")
                    }},
                    upsert=True
                )
                pass


def ensure_database():
    if db is None:
        conn = sqlite3.connect("students.db")
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS students (roll TEXT PRIMARY KEY, name TEXT, status TEXT, enrollment_date TEXT, graduation_date TEXT, created_at TEXT)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, created_at TEXT)"
        )
        conn.commit()
        cur.execute("SELECT id FROM users WHERE username = ?", ("admin",))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
                ("admin", hash_password("admin123"), "admin", datetime.now().isoformat()),
            )
            conn.commit()
        conn.close()
        return
    
    # Create collections if they don't exist
    collections = db.list_collection_names()
    
    if 'students' not in collections:
        # Create indexes for better performance
        db.students.create_index([("roll", 1)], unique=True)
        db.students.create_index([("name", 1)])
        db.students.create_index([("status", 1)])
        
        # Add some default admin user
        admin_user = {
            "username": "admin",
            "password": hash_password("admin123"),
            "role": "admin",
            "created_at": datetime.now()
        }
        db.users.insert_one(admin_user)
    
    if 'logs' not in collections:
        db.logs.create_index([("timestamp", -1)])
        db.logs.create_index([("name", 1)])
    
    # Ensure all known face files have database records
    ensure_known_face_records()
    known_names = [os.path.splitext(f)[0] for f in os.listdir("known_faces") if f.lower().endswith((".jpg", ".png"))]
    for idx, name in enumerate(known_names, start=1):
        roll = f"{name[:3].lower()}{idx:03d}"
        if not db.students.find_one({"name": name}) and not db.students.find_one({"roll": roll}):
            student = {
                "roll": roll,
                "name": name,
                "status": "PRESENT",
                "enrollment_date": datetime.now().strftime("%Y-%m-%d"),
                "created_at": datetime.now()
            }
            db.students.insert_one(student)
    
    # Process alumni (PAST)
    alumni_names = [os.path.splitext(f)[0] for f in os.listdir("alumni_faces") if f.lower().endswith((".jpg", ".png"))]
    for idx, name in enumerate(alumni_names, start=1):
        roll = f"{name[:3].lower()}{idx:03d}"
        if not db.students.find_one({"name": name, "status": "PAST"}) and not db.students.find_one({"roll": roll}):
            student = {
                "roll": roll,
                "name": name,
                "status": "PAST",
                "graduation_date": datetime.now().strftime("%Y-%m-%d"),
                "created_at": datetime.now()
            }
            db.students.insert_one(student)


def log_entry(name, status):
    if db is not None:
        log_entry = {
            "name": name,
            "status": status,
            "timestamp": datetime.now()
        }
        db.logs.insert_one(log_entry)
    else:
        # Fallback to file logging
        with open("log.txt", "a") as f:
            f.write(f"{datetime.now()} - {name} - {status}\n")


def check_db(name, status="PRESENT"):
    if db is not None:
        student = db.students.find_one({"name": name, "status": status})
        return student is not None
    else:
        # Fallback to SQLite
        try:
            conn = sqlite3.connect("students.db")
            cur = conn.cursor()
            cur.execute("SELECT * FROM students WHERE name=? AND status=?", (name, status))
            res = cur.fetchone()
            conn.close()
            return res is not None
        except:
            return False




def process_frame(frame):
    global last_saved, latest_detection_status, face_reload_timestamp

    if time.time() - face_reload_timestamp > 15:
        reload_known_faces()

    latest_detection_status = "Monitoring"

    if MODE == "AI":
        results = ai_model.recognize(frame)
    else:
        results = []
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            locs = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
            detections = [(y, x+w, y+h, x) for (x, y, w, h) in locs]
            results = mse_model.recognize(frame, detections)
        except Exception:
            results = []

    for (top, right, bottom, left, name) in results:
        current_time = time.time()

        # Check status hierarchy: PRESENT (Authorized) > PAST (Alumni) > ADMISSION (Applicant) > Unauthorized
        if check_db(name, "PRESENT"):
            status = "Authorized"
            color = (0, 255, 0)  # Green
        elif check_db(name, "PAST"):
            status = "Alumni"
            color = (255, 165, 0)  # Orange
        elif check_db(name, "ADMISSION"):
            status = "Applicant"
            color = (255, 255, 0)  # Yellow
        else:
            status = "Unauthorized"
            color = (0, 0, 255)  # Red

        if latest_detection_status != "Unauthorized":
            latest_detection_status = status

        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.putText(frame, f"{name} - {status}", (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        allow_log = False
        if name not in detection_cooldown:
            allow_log = True
        else:
            elapsed = current_time - detection_cooldown[name]
            allow_log = elapsed > (10 if status == "Unauthorized" else 3)

        if allow_log:
            log_entry(name, status)
            detection_cooldown[name] = current_time

        if status == "Unauthorized":
            person_id = f"{name}:{status}"
            should_send, _ = should_send_alert(person_id, last_alert_time, cooldown_seconds=30, now=current_time)
            if should_send:
                filename = datetime.now().strftime("%Y%m%d_%H%M%S.jpg")
                image_path = f"unauthorized/{filename}"
                cv2.imwrite(image_path, frame)

                observation = generate_ai_observation(
                    people=1,
                    objects=["Laptop", "Backpack"],
                    environment="Indoor",
                    lighting="Normal",
                    risk="LOW",
                )
                latest_ai_observation = observation
                latest_ai_report_path = save_ai_report(observation)

                email_subject = "🚨 Unauthorized Person"
                email_body = (
                    "🚨 Unauthorized Person\n\n"
                    "AI Analysis\n\n"
                    "• One person detected\n"
                    "• Carrying Laptop\n"
                    "• Wearing Backpack\n"
                    "• Indoor Environment\n"
                    "Lighting: Normal\n"
                    "Risk: LOW\n"
                )
                if email_alerts_enabled:
                    email_sent, email_error = send_security_alert(email_subject, email_body, image_path)
                    if not email_sent:
                        print(f"[ALERT] Email send failed: {email_error}")

                if telegram_alerts_enabled and is_telegram_configured():
                    telegram_message = build_alert_message(name, observation, datetime.now().strftime("%I:%M %p"))
                    telegram_sent, telegram_error = send_telegram_alert(telegram_message)
                    if not telegram_sent:
                        print(f"[ALERT] Telegram send failed: {telegram_error}")
                    else:
                        telegram_image_sent, telegram_image_error = send_telegram_image(image_path)
                        if not telegram_image_sent:
                            print(f"[ALERT] Telegram image send failed: {telegram_image_error}")

                last_saved = current_time


    return frame


def capture_loop():
    global output_frame
    frame_count = 0

    while True:
        if camera is None or not camera.isOpened():
            new_camera = open_camera()
            if new_camera:
                pass
                globals()['camera'] = new_camera
            else:
                pass
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame = cv2.putText(frame, "Camera unavailable", (25, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                with frame_lock:
                    output_frame = frame.copy()
                time.sleep(1)
                continue

        ret, frame = camera.read()
        if not ret or frame is None:
            pass
            camera.release()
            time.sleep(1)
            continue

        frame = process_frame(frame)

        with frame_lock:
            output_frame = frame.copy()
        
        frame_count += 1
        if frame_count % 120 == 0:
            pass

        time.sleep(0.02)


def build_trend_data():
    if not os.path.exists("log.txt"):
        return []

    with open("log.txt") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    points = {}
    for line in lines[-100:]:
        date_text, _ = line.split(" - ", 1)
        try:
            ts = datetime.fromisoformat(date_text.strip())
            label = ts.strftime("%H:%M")
            points[label] = points.get(label, 0) + 1
        except ValueError:
            continue

    trend = [{"time": k, "count": v} for k, v in sorted(points.items())]
    if not trend:
        trend = [
            {"time": "00:00", "count": 0},
            {"time": "00:01", "count": 0},
            {"time": "00:02", "count": 0},
        ]
    return trend


# Authentication Routes
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    requested_role = data.get("role")
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    def check_role(stored_role):
        if requested_role and stored_role and requested_role != stored_role:
            return False
        return True

    if db is not None:
        user = db.users.find_one({"username": username})
        if user and verify_password(user["password"], password):
            if not check_role(user.get("role", "security")):
                return jsonify({"error": "Role mismatch. Select the correct login role."}), 401
            session.permanent = True
            session["user"] = username
            session["role"] = user.get("role", "security")
            return jsonify({"message": "Login successful", "role": session["role"]})
    else:
        try:
            conn = sqlite3.connect("students.db")
            cur = conn.cursor()
            cur.execute("SELECT username, password, role FROM users WHERE username = ?", (username,))
            row = cur.fetchone()
            conn.close()
            if row and verify_password(row[1], password):
                stored_role = row[2] if row[2] else "security"
                if not check_role(stored_role):
                    return jsonify({"error": "Role mismatch. Select the correct login role."}), 401
                session.permanent = True
                session["user"] = username
                session["role"] = stored_role
                return jsonify({"message": "Login successful", "role": session["role"]})
        except Exception:
            pass
        if username == "admin" and password == "admin123":
            stored_role = "admin"
            if not check_role(stored_role):
                return jsonify({"error": "Role mismatch. Select the correct login role."}), 401
            session["user"] = username
            session["role"] = "admin"
            return jsonify({"message": "Login successful", "role": "admin"})
    
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/me")
def me():
    if 'user' in session:
        return jsonify({"user": {"username": session["user"], "role": session.get("role", "security")}})
    return jsonify({"error": "Not authenticated"}), 401


@app.route("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "security")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if role not in ["admin", "security"]:
        role = "security"

    if db is not None:
        if db.users.find_one({"username": username}):
            return jsonify({"error": "User already exists"}), 400

        user = {
            "username": username,
            "password": hash_password(password),
            "role": role,
            "created_at": datetime.now()
        }
        db.users.insert_one(user)
        return jsonify({"message": "Signup successful", "role": role})

    try:
        conn = sqlite3.connect("students.db")
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, created_at TEXT)"
        )
        conn.commit()
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            return jsonify({"error": "User already exists"}), 400
        cur.execute(
            "INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), role, datetime.now().isoformat()),
        )
        conn.commit()
        return jsonify({"message": "Signup successful", "role": role})
    except sqlite3.IntegrityError:
        return jsonify({"error": "User already exists"}), 400
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/register", methods=["POST"])
@require_auth
def register():
    if session.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "user")
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    if db is not None:
        if db.users.find_one({"username": username}):
            return jsonify({"error": "User already exists"}), 400
        
        user = {
            "username": username,
            "password": hash_password(password),
            "role": role,
            "created_at": datetime.now()
        }
        db.users.insert_one(user)
        return jsonify({"message": "User created successfully"})
    
    return jsonify({"error": "Database not available"}), 500


@app.route("/")
def root():
    return send_from_directory(BUILD_DIR, "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory(os.path.join(BUILD_DIR, "static"), path)


@app.errorhandler(404)
def not_found(_error):
    return send_from_directory(BUILD_DIR, "index.html")


@app.route("/logs")
@require_auth
def logs():
    if db is not None:
        # Get logs from MongoDB, sorted by timestamp descending, limit to last 1000
        logs_data = list(db.logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(1000))
        # Convert to string format for frontend compatibility
        formatted_logs = [f"{log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {log['name']} - {log['status']}" for log in logs_data]
        return no_cache_response(jsonify(formatted_logs))
    else:
        # Fallback to file
        if not os.path.exists("log.txt"):
            return no_cache_response(jsonify([]))
        with open("log.txt") as f:
            return no_cache_response(jsonify([line.strip() for line in f.readlines()]))


@app.route("/status")
@require_auth
def status():
    payload = {"status": latest_detection_status}
    if latest_ai_observation is not None:
        payload["ai_observation"] = latest_ai_observation
        payload["ai_report_path"] = latest_ai_report_path
    return no_cache_response(jsonify(payload))


@app.route("/reset_demo", methods=["POST"])
@require_auth
def reset_demo():
    global latest_detection_status, detection_cooldown, latest_ai_observation, latest_ai_report_path, last_alert_time

    if db is not None:
        db.logs.delete_many({})
    else:
        open("log.txt", "w").close()

    folder = os.path.join(app.root_path, "unauthorized")
    if os.path.exists(folder):
        for filename in os.listdir(folder):
            if allowed_file(filename):
                try:
                    os.remove(os.path.join(folder, filename))
                except Exception:
                    pass

    latest_detection_status = "Monitoring"
    latest_ai_observation = None
    latest_ai_report_path = None
    detection_cooldown.clear()
    last_alert_time.clear()
    return jsonify({"message": "Demo reset complete"})


@app.route("/settings/alerts", methods=["GET", "POST"])
@require_auth
def alert_settings():
    global email_alerts_enabled, telegram_alerts_enabled
    if request.method == "POST":
        data = request.get_json() or {}
        email_alerts_enabled = bool(data.get("email", email_alerts_enabled))
        telegram_alerts_enabled = bool(data.get("telegram", is_telegram_configured()))
        return jsonify({"email": email_alerts_enabled, "telegram": telegram_alerts_enabled})
    return jsonify({"email": email_alerts_enabled, "telegram": is_telegram_configured()})


@app.route("/test/email", methods=["POST"])
@require_auth
def test_email():
    if not email_alerts_enabled:
        return jsonify({"error": "Email alerts are disabled or not configured."}), 400

    test_subject = "🚨 Unauthorized Person Detected"
    test_body = (
        f"Time:{datetime.now().strftime('%d-%b-%Y %I:%M %p')}\n"
        f"Location:Main Entrance\n"
        f"Detection:Unauthorized Person\n"
        f"System:Face Recognition Security System\n"
        f"Status:Email alert test generated successfully\n"
    )
    email_sent, email_error = send_security_alert(test_subject, test_body, None)
    if email_sent:
        return jsonify({"message": "Test email alert sent! Check your inbox."})
    return jsonify({"error": "Failed to send test email alert.", "details": email_error}), 500


@app.route("/test/telegram", methods=["POST"])
@require_auth
def test_telegram():
    if not is_telegram_configured():
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        valid, error = validate_telegram_credentials(token, chat_id)
        return jsonify({"error": "Telegram alerts are disabled or not configured.", "details": error}), 400

    telegram_sent, telegram_error = send_telegram_alert("🚨 Telegram alert test: unauthorized access notification.")
    if telegram_sent:
        return jsonify({"message": "Test telegram alert sent! Check your Telegram."})
    return jsonify({"error": "Failed to send test telegram alert.", "details": telegram_error}), 500


@app.route("/unauthorized-gallery")
@require_auth
def unauthorized_gallery():
    gallery = []
    folder = os.path.join(app.root_path, "unauthorized")
    if not os.path.exists(folder):
        return no_cache_response(jsonify(gallery))

    files = [f for f in os.listdir(folder) if allowed_file(f)]
    files.sort(reverse=True)

    for filename in files[:12]:
        file_path = os.path.join(folder, filename)
        timestamp = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
        gallery.append({
            "filename": filename,
            "timestamp": timestamp,
            "url": f"/unauthorized-image/{filename}?ts={int(time.time())}"
        })

    return no_cache_response(jsonify(gallery))


@app.route("/unauthorized-image/<path:filename>")
@require_auth
def unauthorized_image(filename):
    safe_name = secure_filename(filename)
    return send_from_directory(os.path.join(app.root_path, "unauthorized"), safe_name)


@app.route("/trend")
@require_auth
def trend():
    if db is not None:
        # Get trend data from MongoDB logs
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%H:%M",
                            "date": "$timestamp"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        results = list(db.logs.aggregate(pipeline))
        trend_data = [{"time": result["_id"], "count": result["count"]} for result in results]
        if not trend_data:
            trend_data = [
                {"time": "00:00", "count": 0},
                {"time": "00:01", "count": 0},
                {"time": "00:02", "count": 0},
            ]
        return no_cache_response(jsonify(trend_data))
    else:
        return no_cache_response(jsonify(build_trend_data()))


@app.route("/add_student", methods=["POST"])
@require_auth
def add_student():
    data = request.get_json() or {}
    roll = data.get("roll")
    name = data.get("name")
    status = data.get("status", "PRESENT")
    image_data = data.get("image")

    if not roll or not name:
        return jsonify("Missing roll or name"), 400

    if db is not None and db.students.find_one({"roll": roll}):
        return jsonify("Roll already exists"), 400

    if image_data:
        try:
            if "," in image_data:
                image_data = image_data.split(",", 1)[1]
            image_bytes = base64.b64decode(image_data)
            upload_dir = "alumni_faces" if status == "PAST" else "known_faces"
            os.makedirs(upload_dir, exist_ok=True)
            safe_name = secure_filename(name)
            filename = f"{safe_name}.jpg"
            file_path = os.path.join(upload_dir, filename)
            with open(file_path, "wb") as f:
                f.write(image_bytes)
        except Exception as e:
            return jsonify("Failed to save captured image"), 500

    if db is not None:
        student = {
            "roll": roll,
            "name": name,
            "status": status,
            "created_at": datetime.now()
        }
        if status == "PRESENT":
            student["enrollment_date"] = datetime.now().strftime("%Y-%m-%d")
        elif status == "PAST":
            student["graduation_date"] = datetime.now().strftime("%Y-%m-%d")

        db.students.insert_one(student)
        if image_data:
            reload_known_faces()
        return jsonify(f"Student added as {status}")
    else:
        # Fallback to SQLite
        try:
            conn = sqlite3.connect("students.db")
            cur = conn.cursor()
            if status == "PRESENT":
                cur.execute("INSERT INTO students (roll, name, status, enrollment_date) VALUES (?, ?, ?, ?)",
                           (roll, name, status, datetime.now().strftime("%Y-%m-%d")))
            elif status == "PAST":
                cur.execute("INSERT INTO students (roll, name, status, graduation_date) VALUES (?, ?, ?, ?)",
                           (roll, name, status, datetime.now().strftime("%Y-%m-%d")))
            else:
                cur.execute("INSERT INTO students (roll, name, status) VALUES (?, ?, ?)",
                           (roll, name, status))
            conn.commit()
            if image_data:
                reload_known_faces()
            return jsonify(f"Student added as {status}")
        except sqlite3.IntegrityError:
            return jsonify("Roll already exists"), 400
        finally:
            if 'conn' in locals():
                conn.close()

@app.route("/upload_image", methods=["POST"])
@require_auth
def upload_image():
    if 'file' not in request.files:
        return jsonify("No file part")
    file = request.files['file']
    name = request.form.get('name')
    status = request.form.get('status', 'PRESENT')
    roll = request.form.get('roll')
    
    if file.filename == '' or not name:
        return jsonify("No selected file or name")
    
    if file and allowed_file(file.filename):
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        if status == 'PAST':
            upload_dir = "alumni_faces"
        else:
            upload_dir = "known_faces"
            
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        safe_name = secure_filename(name)
        filename = f"{safe_name}.{file_ext}"
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Update database if using MongoDB - use safe_name for consistency
        if db is not None:
            generated_roll = roll if roll else f"{safe_name[:3].lower()}{len(list(db.students.find())) + 1:03d}"
            db.students.update_one(
                {"name": safe_name},
                {"$set": {
                    "name": safe_name,
                    "status": status,
                    "roll": generated_roll,
                    "created_at": datetime.now()
                }},
                upsert=True
            )
            if status == "PRESENT":
                db.students.update_one({"name": safe_name}, {"$set": {"enrollment_date": datetime.now().strftime("%Y-%m-%d")}})
            elif status == "PAST":
                db.students.update_one({"name": safe_name}, {"$set": {"graduation_date": datetime.now().strftime("%Y-%m-%d")}})
        else:
            # SQLite fallback: minimal record update if available
            try:
                conn = sqlite3.connect("students.db")
                cur = conn.cursor()
                if roll:
                    cur.execute("INSERT OR IGNORE INTO students (roll, name, status) VALUES (?, ?, ?)", (roll, safe_name, status))
                conn.commit()
            except Exception:
                pass
            finally:
                if 'conn' in locals():
                    conn.close()

        reload_known_faces()
        return jsonify({"message": "Image uploaded successfully"})
    return jsonify({"error": "Invalid file"}), 400
@app.route("/verify", methods=["POST"])
@require_auth
def verify():
    data = request.get_json()
    roll = data.get("roll")

    if not roll:
        return jsonify("Missing roll")

    if db is not None:
        student = db.students.find_one({"roll": roll}, {"name": 1, "status": 1})
        if student:
            return jsonify(f"Student found: {student['name']} ({student['status']})")
        else:
            return jsonify("Student not found")
    else:
        # Fallback to SQLite
        try:
            conn = sqlite3.connect("students.db")
            cur = conn.cursor()
            cur.execute("SELECT name FROM students WHERE roll = ?", (roll,))
            result = cur.fetchone()
            conn.close()
            if result:
                return jsonify(f"Student found: {result[0]}")
            else:
                return jsonify("Student not found")
        except:
            return jsonify("Database error")


@app.route('/snapshot')
def snapshot():
    pass
    with frame_lock:
        if output_frame is None:
            pass
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder, "Waiting for camera...", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            ret, buf = cv2.imencode('.jpg', placeholder)
            if not ret:
                return Response(status=500)
            response = Response(buf.tobytes(), mimetype='image/jpeg')
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        ret, buf = cv2.imencode('.jpg', output_frame)
        if not ret:
            return Response(status=500)
        response = Response(buf.tobytes(), mimetype='image/jpeg')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response


@app.route('/video')
@app.route('/video_feed')
def video():
    def gen():
        while True:
            with frame_lock:
                frame = output_frame.copy() if output_frame is not None else None

            if frame is None:
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder, "Waiting for camera...", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                frame = placeholder

            ret, buf = cv2.imencode('.jpg', frame)
            if not ret:
                time.sleep(0.1)
                continue

            try:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            except GeneratorExit:
                break
            except Exception:
                break

            time.sleep(0.03)

    pass
    response = Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


if __name__ == "__main__":
    ensure_database()
    thread = threading.Thread(target=capture_loop, daemon=True)
    thread.start()
    pass
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
