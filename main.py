import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="face_recognition_models")

import cv2
import os
import time
from datetime import datetime
import sqlite3
import ai_model
import mse_model

# OPTIONAL SMS - Comment out if not needed
# from twilio.rest import Client
# account_sid = "YOUR_SID"
# auth_token = "YOUR_TOKEN"
# client = Client(account_sid, auth_token)

# def send_sms(msg):
#     client.messages.create(
#         body=msg,
#         from_="+1234567890",
#         to="+91XXXXXXXXXX"
#     )

MODE = "MSE"  # or "AI"

if not os.path.exists("unauthorized"):
    os.makedirs("unauthorized")

def log_entry(name):
    with open("log.txt", "a") as f:
        f.write(f"{datetime.now()} - {name}\n")

def check_db(name):
    conn = sqlite3.connect("students.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM students WHERE name=?", (name,))
    res = cur.fetchone()
    conn.close()
    return res is not None

video = cv2.VideoCapture(0)
last_saved = 0

while True:
    ret, frame = video.read()

    if MODE == "AI":
        results = ai_model.recognize(frame)
    else:
        import face_recognition
        rgb = frame[:, :, ::-1]
        locs = face_recognition.face_locations(rgb)
        results = mse_model.recognize(frame, locs)

    for (top, right, bottom, left, name) in results:

        status = "Authorized" if check_db(name) else "Unauthorized"
        color = (0,255,0) if status=="Authorized" else (0,0,255)

        cv2.rectangle(frame,(left,top),(right,bottom),color,2)
        cv2.putText(frame,f"{name}-{status}",(left,top-10),
                    cv2.FONT_HERSHEY_SIMPLEX,0.7,color,2)

        log_entry(f"{name}-{status}")

        if status == "Unauthorized":
            if time.time() - last_saved > 5:
                filename = datetime.now().strftime("%Y%m%d_%H%M%S.jpg")
                cv2.imwrite(f"unauthorized/{filename}", frame)
                print("🚨 ALERT")

                # SMS - Comment out if not using
                # send_sms("Unauthorized access detected!")

                last_saved = time.time()

    cv2.imshow("Security System", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video.release()
cv2.destroyAllWindows()