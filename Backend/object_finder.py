import cv2
import speech_recognition as sr
from ultralytics import YOLO
from gtts import gTTS
import playsound
import uuid
import os
import time
from sentence_transformers import SentenceTransformer, util
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware


# ==================== LOAD YOLO MODEL ====================
model = YOLO("yolov9c.pt")

# ==================== SENTENCE TRANSFORMER ====================
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Precompute embeddings
yolo_class_names = [model.names[i].lower() for i in model.names]
yolo_embeddings = embedder.encode(yolo_class_names, convert_to_tensor=True)


def smart_match(target):
    target_embedding = embedder.encode(target, convert_to_tensor=True)
    similarity_scores = util.cos_sim(target_embedding, yolo_embeddings)[0]

    best_idx = similarity_scores.argmax().item()
    best_score = similarity_scores[best_idx].item()

    if best_score < 0.30:
        return None

    return yolo_class_names[best_idx]


# ==================== SPEAK ====================
def speak(text):
    print("AI:", text)
    filename = f"voice_{uuid.uuid4().hex}.mp3"
    tts = gTTS(text=text, lang="en")
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


# ==================== DISTANCE (APPROX) ====================
def estimate_distance(box_width_pixels, known_width=15, focal_length=600):
    if box_width_pixels == 0:
        return None
    distance_cm = (known_width * focal_length) / box_width_pixels
    return int(distance_cm)


# ==============================================
# 🚀 MAIN DETECTION — SHOW CAMERA POPUP WINDOW
# ==============================================
async def start_detection(target, websocket):

    mapped_target = smart_match(target)
    if mapped_target is None:
        await websocket.send_text("Object not found in YOLO model.")
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

                if mapped_target == label:
                    found_object = True

                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx = (x1 + x2) // 2

                    direction = get_direction(cx, frame.shape[1])
                    distance = estimate_distance(x2 - x1)

                    msg = (
                        f"{mapped_target} on your {direction}, "
                        f"{distance} centimeters away"
                        if distance
                        else f"{mapped_target} on your {direction}"
                    )

                    # Send message to frontend
                    await websocket.send_text(msg)

                    # Speak every 2 seconds
                    if time.time() - last_speak > 2:
                        speak(msg)
                        last_speak = time.time()

                    # Draw on camera
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    cv2.putText(
                        frame,
                        msg,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )

        if not found_object:
            await websocket.send_text("Scanning...")

        # Show camera popup window
        cv2.imshow("Object Finder Camera", frame)

        # Allow FastAPI async loop to breathe
        await asyncio.sleep(0.01)

        # Press Q to stop (still works)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


# ==============================================
# 🚀 FASTAPI BACKEND + WEBSOCKET
# ==============================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/find")
async def ws_find(websocket: WebSocket):
    await websocket.accept()
    target = await websocket.receive_text()
    await websocket.send_text(f"Searching for {target}...")
    await start_detection(target, websocket)
