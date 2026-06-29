import cv2
import sqlite3
import os
import time
from datetime import datetime
from ultralytics import YOLO

# ─── Config ────────────────────────────────────────────────────────────────────
MODEL_PATH = "runs/detect/runs/train/safety_model-4/weights/best.pt"
VIDEO_PATH = "demo_video.mp4"
DB_PATH    = "backend/violations.db"
SNAP_DIR   = "snapshots"
# CONF_THRESH = 0.25
# HARDHAT_CONF = 0.6 # to avoid false cap flag 
FRAME_SKIP  = 1   # process every 3rd frame to keep it real-time

# Class IDs from data.yaml
CLASS_NAMES = {
    0: "Hardhat",
    2: "NO-Hardhat",
    4: "NO-Safety Vest",
    5: "Person",
    7: "Safety Vest"
}
CLASS_CONF = {
    0: 0.25,   # Hardhat — high threshold to avoid cap false positives
    2: 0.15,   # NO-Hardhat
    4: 0.25,   # NO-Safety Vest
    5: 0.40,   # Person
    7: 0.40    # safety vest 
}
CLASSES_TO_DETECT = list(CLASS_NAMES.keys())

# Violation classes
VIOLATION_CLASSES = {2: "No Hardhat", 4: "No Safety Vest"}

# Zone map — divide frame width into zones
ZONES = ["Entry Gate", "Scaffolding Area", "Material Yard", "Crane Zone", "Office Block"]

# Cooldown — don't log same violation repeatedly (seconds)
COOLDOWN = 10


# ─── Database setup ────────────────────────────────────────────────────────────
def init_db():
    os.makedirs("backend", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            zone        TEXT NOT NULL,
            violation   TEXT NOT NULL,
            confidence  REAL NOT NULL,
            snapshot    TEXT,
            acknowledged INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] Database initialized")


def log_violation(zone, violation, confidence, snapshot_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO violations (timestamp, zone, violation, confidence, snapshot, acknowledged)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (datetime.now().isoformat(), zone, violation, confidence, snapshot_path))
    conn.commit()
    conn.close()


# ─── Helpers ───────────────────────────────────────────────────────────────────
def get_zone(x_center, frame_width):
    """Map x position to a site zone."""
    ratio = x_center / frame_width
    idx = min(int(ratio * len(ZONES)), len(ZONES) - 1)
    return ZONES[idx]


def save_snapshot(frame, violation_type):
    """Save a cropped frame snapshot when a violation is detected."""
    os.makedirs(SNAP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{SNAP_DIR}/{violation_type.replace(' ', '_')}_{ts}.jpg"
    cv2.imwrite(filename, frame)
    return filename


def draw_violation_overlay(frame, violations_this_frame):
    """Draw a red banner at the top if violations detected."""
    if violations_this_frame:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], 50), (0, 0, 200), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        text = f"⚠ VIOLATION: {', '.join(violations_this_frame)}"
        cv2.putText(frame, text, (10, 33),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    return frame


# ─── Main detection loop ───────────────────────────────────────────────────────
def run_detector():
    print("[INFO] Loading model...")
    model = YOLO(MODEL_PATH)

    print(f"[INFO] Opening video: {VIDEO_PATH}")
    cap = cv2.VideoCapture(VIDEO_PATH)

    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {VIDEO_PATH}")
        return

    init_db()

    frame_count = 0
    last_logged = {}   # {violation_type: timestamp} for cooldown

    print("[INFO] Starting detection loop. Press Q to quit.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("[INFO] Video ended — restarting for demo loop.")
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        frame_count += 1

        # Skip frames for performance
        if frame_count % FRAME_SKIP != 0:
            cv2.imshow("SafeWatch — Construction Safety Monitor", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        frame_h, frame_w = frame.shape[:2]

        # ── Run detection ──
        results = model.track(frame, conf=min(CLASS_CONF.values()), classes=CLASSES_TO_DETECT, verbose=False, persist=True, tracker="bytetrack.yaml")
        detections = results[0].boxes
        violations_this_frame = []

        if detections is not None:
            detected_classes = [int(b.cls[0]) for b in detections]

            for box in detections:
                cls_id     = int(box.cls[0])
                confidence = float(box.conf[0])
                if confidence < CLASS_CONF.get(cls_id, CLASS_CONF):
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                x_center   = (x1 + x2) // 2
                label      = CLASS_NAMES.get(cls_id, "Unknown")

                # ── Draw box ──
                color = (0, 0, 255) if cls_id in VIOLATION_CLASSES else (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{label} {confidence:.2f}",
                            (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, color, 2)

                # ── Violation logic ──
                if cls_id in VIOLATION_CLASSES:
                    violation_name = VIOLATION_CLASSES[cls_id]
                    zone = get_zone(x_center, frame_w)
                    now = time.time()

                    # Cooldown check — don't spam the DB
                    last_time = last_logged.get(violation_name, 0)
                    if now - last_time > COOLDOWN:
                        snap = save_snapshot(frame, violation_name)
                        log_violation(zone, violation_name, confidence, snap)
                        last_logged[violation_name] = now
                        print(f"[VIOLATION] {violation_name} | Zone: {zone} | Conf: {confidence:.2f}")

                    violations_this_frame.append(violation_name)

        # ── Overlay ──
        frame = draw_violation_overlay(frame, list(set(violations_this_frame)))

        # ── FPS counter ──
        cv2.putText(frame, f"Frame: {frame_count}", (10, frame_h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

        cv2.imshow("SafeWatch — Construction Safety Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Detector stopped.")


if __name__ == "__main__":
    run_detector()