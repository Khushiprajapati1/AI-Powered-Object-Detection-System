# yolo_detect.py

import cv2
from ultralytics import YOLO
from sentence_transformers import SentenceTransformer, util

# ==================== LOAD YOLO HIGH ACCURACY MODEL ====================
model = YOLO("yolov9c.pt")  # or YOLO("yolov8x.pt")

# ==================== SENTENCE TRANSFORMER ====================
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Precompute embeddings for YOLO classes
yolo_class_names = [model.names[i].lower() for i in model.names]
yolo_embeddings = embedder.encode(yolo_class_names, convert_to_tensor=True)

# ==================== SMART MATCH ====================
def smart_match(target: str):
    """
    Matches user target to closest YOLO class using sentence embeddings.
    Returns the best matching class name or None if confidence is low.
    """
    target_embedding = embedder.encode(target, convert_to_tensor=True)
    similarity_scores = util.cos_sim(target_embedding, yolo_embeddings)[0]

    best_idx = similarity_scores.argmax().item()
    best_score = similarity_scores[best_idx].item()

    if best_score < 0.30:
        return None

    return yolo_class_names[best_idx]

# ==================== DIRECTION ====================
def get_direction(cx, width):
    """
    Returns 'left', 'right', or 'center' based on object's x-center position.
    """
    center = width // 2
    if cx < center - 80:
        return "left"
    elif cx > center + 80:
        return "right"
    else:
        return "center"

# ==================== DISTANCE ESTIMATION ====================
def estimate_distance(box_width_pixels, known_width=15, focal_length=600):
    """
    Approximates distance in cm using simple pinhole camera formula.
    """
    if box_width_pixels == 0:
        return None
    distance_cm = (known_width * focal_length) / box_width_pixels
    return int(distance_cm)

# ==================== DETECTION FUNCTION ====================
def detect_frame(frame, target_class):
    """
    Detects objects in a given frame and returns detection info.
    """
    results = model(frame)
    detections = []

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id].lower()

            if label == target_class:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx = (x1 + x2) // 2
                direction = get_direction(cx, frame.shape[1])
                distance = estimate_distance(x2 - x1)

                detections.append({
                    "label": label,
                    "bbox": [x1, y1, x2, y2],
                    "center": cx,
                    "direction": direction,
                    "distance_cm": distance
                })

    return detections

# ==================== VIDEO CAPTURE HELPER ====================
def detect_from_camera(target_class):
    """
    Captures frames from webcam and detects target object in real-time.
    Returns list of detection dictionaries for each frame.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open camera")

    all_detections = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            detections = detect_frame(frame, target_class)
            all_detections.append(detections)

            # Optional: show frame with bounding boxes
            for det in detections:
                x1, y1, x2, y2 = det["bbox"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
                label = det["label"]
                dist = det["distance_cm"]
                cv2.putText(frame, f"{label} {dist}cm", (x1, y1-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

            cv2.imshow("YOLO Detection", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return all_detections
