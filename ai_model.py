import face_recognition
import os

known_encodings = []
known_names = []


def load_known_faces():
    global known_encodings, known_names
    known_encodings = []
    known_names = []
    if not os.path.exists("known_faces"):
        os.makedirs("known_faces")
    for file in sorted(os.listdir("known_faces")):
        if not file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            continue
        try:
            image = face_recognition.load_image_file(f"known_faces/{file}")
            enc = face_recognition.face_encodings(image)
            if len(enc) == 0:
                continue
            known_encodings.append(enc[0])
            known_names.append(file.rsplit(".", 1)[0])
        except Exception:
            continue


load_known_faces()

def reload_faces():
    load_known_faces()

def recognize(frame):
    rgb = frame[:,:,::-1]
    locs = face_recognition.face_locations(rgb)
    encs = face_recognition.face_encodings(rgb, locs)

    results = []

    for (top,right,bottom,left), e in zip(locs,encs):
        matches = face_recognition.compare_faces(known_encodings,e)
        name="Unauthorized"
        if True in matches:
            name=known_names[matches.index(True)]
        results.append((top,right,bottom,left,name))

    return results