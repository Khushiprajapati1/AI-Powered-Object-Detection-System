import cv2
import speech_recognition as sr
from ultralytics import YOLO
from gtts import gTTS
import playsound
import uuid
import os
import time
from sentence_transformers import SentenceTransformer, util
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading

# ==================== LOAD YOLO MODEL ====================
model = YOLO("yolov9c.pt")

# ==================== SENTENCE TRANSFORMER ====================
embedder = SentenceTransformer('all-MiniLM-L6-v2')
yolo_class_names = [model.names[i].lower() for i in model.names]
yolo_embeddings = embedder.encode(yolo_class_names, convert_to_tensor=True)

def smart_match(target):
    target_embedding = embedder.encode(target, convert_to_tensor=True)
    similarity_scores = util.cos_sim(target_embedding, yolo_embeddings)[0] #consine similarity
    best_idx = similarity_scores.argmax().item()
    best_score = similarity_scores[best_idx].item()
    return yolo_class_names[best_idx] if best_score >= 0.30 else None

# ==================== SPEAK ====================
def speak(text):
    print("AI:", text)
    filename = f"voice_{uuid.uuid4().hex}.mp3"
    tts = gTTS(text=text, lang='en')
    tts.save(filename)
    playsound.playsound(filename)
    os.remove(filename)

# ==================== DIRECTION ====================
def get_direction(cx, width):
    center = width // 2
    if cx < center - 80:
        return "left"
    elif cx > center + 80:
        return "right"
    else:
        return "center"

# ==================== DISTANCE ====================
def estimate_distance(box_width_pixels, known_width=15, focal_length=600):
    if box_width_pixels == 0:
        return None
    return int((known_width * focal_length) / box_width_pixels)

# ==================== YOLO LOOP ====================
def run_detection(target):
    mapped_target = smart_match(target)
    if mapped_target is None:
        speak("Sorry, I cannot detect that object with this model.")
        return

    speak(f"I will look for {mapped_target}")

    cap = cv2.VideoCapture(0)
    speak("Camera started. Move around to scan the room.")

    last_speak = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        results = model(frame, stream=True)
        found_object = False

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                label = model.names[cls_id].lower()

                if label == mapped_target:
                    found_object = True

                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx = (x1 + x2) // 2

                    direction = get_direction(cx, frame.shape[1])
                    distance = estimate_distance(x2 - x1)

                    msg = (
                        f"{label} is on your {direction}, {distance} centimeters away"
                        if distance else f"{label} is on your {direction}"
                    )

                    if time.time() - last_speak > 2:
                        speak(msg)
                        last_speak = time.time()

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 3)
                    cv2.putText(frame, msg, (x1, y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

        if not found_object:
            cv2.putText(frame, "Scanning...", (20,40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

        cv2.imshow("YOLO Object Finder", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# ==================== FASTAPI ====================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/start")
def start_detection_api(request: dict):
    target = request["target"]

    # Run YOLO in background thread so FastAPI doesn’t freeze
    threading.Thread(target=run_detection, args=(target,), daemon=True).start()

    return {"status": "started", "target": target}
