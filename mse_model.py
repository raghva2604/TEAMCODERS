import cv2, os, numpy as np

faces=[]
names=[]


def load_known_faces():
    global faces, names
    faces = []
    names = []
    if not os.path.exists("known_faces"):
        os.makedirs("known_faces")
    for file in sorted(os.listdir("known_faces")):
        if not file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            continue
        img = cv2.imread(f"known_faces/{file}")
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face = cv2.resize(gray, (100, 100))
        faces.append(face)
        names.append(file.rsplit(".", 1)[0])


load_known_faces()

def reload_faces():
    load_known_faces()


def mse(a,b):
    return np.mean((a-b)**2)

def recognize(frame, locs):
    results=[]
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)

    for (top,right,bottom,left) in locs:
        face=gray[top:bottom,left:right]
        if face.size==0: continue
        face=cv2.resize(face,(100,100))

        name="Unauthorized"
        for i,f in enumerate(faces):
            if mse(f,face)<5000:
                name=names[i]

        results.append((top,right,bottom,left,name))

    return results