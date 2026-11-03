
import os
import json
import uuid
import base64
import sqlite3
import threading
import io

from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
from PIL import Image

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
    flash
)

from werkzeug.utils import secure_filename
from ai_edge_litert.interpreter import Interpreter


# --------------------------------------------------
# 1. PROJECT CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "waste_classifier.tflite"
CLASS_FILE = BASE_DIR / "class_names.json"
DATABASE = BASE_DIR / "database.db"
UPLOAD_FOLDER = BASE_DIR / "uploads"

UPLOAD_FOLDER.mkdir(exist_ok=True)

IMAGE_SIZE = (160, 160)

CONFIDENCE_THRESHOLD = 0.65
MARGIN_THRESHOLD = 0.15

ALLOWED_IMAGES = {"jpg", "jpeg", "png"}
ALLOWED_VIDEOS = {"mp4", "avi", "mov", "mkv"}

EXPECTED_CLASSES = ["glass", "metal", "paper", "plastic"]


# --------------------------------------------------
# 2. FLASK APPLICATION
# --------------------------------------------------

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "ecosort-ai-secret-key"
)

app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


# --------------------------------------------------
# 3. LOAD FOUR-CLASS MODEL
# --------------------------------------------------

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}"
    )

if not CLASS_FILE.exists():
    raise FileNotFoundError(
        f"Class file not found: {CLASS_FILE}"
    )

with open(CLASS_FILE, "r", encoding="utf-8") as file:
    CLASS_NAMES = json.load(file)

if CLASS_NAMES != EXPECTED_CLASSES:
    raise ValueError(
        f"Expected classes: {EXPECTED_CLASSES}, "
        f"but found: {CLASS_NAMES}"
    )

print("Loading EcoSort AI four-class model...")

interpreter = Interpreter(
    model_path=str(MODEL_PATH),
    num_threads=1
)

interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

if int(output_details[0]["shape"][-1]) != 4:
    raise ValueError(
        "The TFLite model must have exactly four outputs."
    )

inference_lock = threading.Lock()

print("EcoSort AI model loaded successfully!")


# --------------------------------------------------
# 4. DATABASE FUNCTIONS
# --------------------------------------------------

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                waste_type TEXT,
                confidence REAL,
                source TEXT,
                timestamp TEXT
            )
        """)

        connection.commit()


def save_history(filename, waste_type, confidence, source):
    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    with get_db() as connection:
        connection.execute("""
            INSERT INTO history
            (filename, waste_type, confidence, source, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            filename,
            waste_type,
            confidence,
            source,
            timestamp
        ))

        connection.commit()


init_db()


# --------------------------------------------------
# 5. MODEL PREDICTION
# --------------------------------------------------

def softmax(values):
    values = values - np.max(values)
    exp_values = np.exp(values)
    return exp_values / np.sum(exp_values)


def predict_waste(image):

    image = image.convert("RGB").resize(IMAGE_SIZE)

    image_array = np.expand_dims(
        np.asarray(image, dtype=np.float32),
        axis=0
    )

    input_info = input_details[0]
    output_info = output_details[0]

    # Handle quantized model input
    if input_info["dtype"] in (np.uint8, np.int8):

        scale, zero_point = input_info["quantization"]

        if scale > 0:
            image_array = np.round(
                image_array / scale + zero_point
            )

        limits = np.iinfo(input_info["dtype"])

        image_array = np.clip(
            image_array,
            limits.min,
            limits.max
        ).astype(input_info["dtype"])

    else:
        image_array = image_array.astype(
            input_info["dtype"]
        )

    # Run model prediction
    with inference_lock:

        interpreter.set_tensor(
            input_info["index"],
            image_array
        )

        interpreter.invoke()

        predictions = interpreter.get_tensor(
            output_info["index"]
        )[0]

    # Handle quantized model output
    if output_info["dtype"] in (np.uint8, np.int8):

        scale, zero_point = output_info["quantization"]

        if scale > 0:
            predictions = (
                predictions.astype(np.float32) - zero_point
            ) * scale

    predictions = predictions.astype(np.float32)

    # Convert logits into probabilities if necessary
    if (
        np.any(predictions < 0)
        or np.any(predictions > 1)
        or not np.isclose(
            np.sum(predictions),
            1.0,
            atol=0.02
        )
    ):
        predictions = softmax(predictions)

    # Find highest and second-highest predictions
    order = np.argsort(predictions)[::-1]

    best_index = int(order[0])

    confidence = float(predictions[best_index])

    second_confidence = float(
        predictions[order[1]]
    )

    margin = confidence - second_confidence

    # Unknown-item decision
    if (
        confidence < CONFIDENCE_THRESHOLD
        or margin < MARGIN_THRESHOLD
    ):

        return {
            "class": "Unknown Item",
            "confidence": round(confidence * 100, 2),
            "status": "unknown"
        }

    return {
        "class": CLASS_NAMES[best_index],
        "confidence": round(confidence * 100, 2),
        "status": "success"
    }


# --------------------------------------------------
# 6. FILE FUNCTIONS
# --------------------------------------------------

def allowed_file(filename, extensions):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in extensions
    )


def unique_filename(filename):

    safe_name = secure_filename(filename)

    extension = Path(safe_name).suffix.lower()

    return f"{uuid.uuid4().hex}{extension}"


def save_upload(file):

    filename = unique_filename(file.filename)

    path = UPLOAD_FOLDER / filename

    file.save(path)

    return filename, path


# --------------------------------------------------
# 7. DISPLAY CLASSIFICATION RESULT
# --------------------------------------------------

def show_result(filename, prediction):

    return render_template(
        "result.html",
        filename=filename,
        waste_type=prediction["class"],
        confidence=prediction["confidence"]
    )


# --------------------------------------------------
# 8. HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():

    return render_template("index.html")


# --------------------------------------------------
# 9. IMAGE CLASSIFICATION
# --------------------------------------------------

@app.route("/classify", methods=["GET", "POST"])
def classify():

    if request.method == "GET":
        return render_template("classify.html")

    file = request.files.get("image")

    if not file or not file.filename:
        flash("Please select an image.")
        return redirect(url_for("classify"))

    if not allowed_file(file.filename, ALLOWED_IMAGES):
        flash("Please upload JPG, JPEG or PNG images.")
        return redirect(url_for("classify"))

    filename = None

    try:

        filename, path = save_upload(file)

        with Image.open(path) as source_image:
            image = source_image.convert("RGB")

        prediction = predict_waste(image)

        save_history(
            filename,
            prediction["class"],
            prediction["confidence"],
            "upload"
        )

        return show_result(filename, prediction)

    except Exception:

        app.logger.exception(
            "Image classification failed"
        )

        if filename and (UPLOAD_FOLDER / filename).exists():
            (UPLOAD_FOLDER / filename).unlink()

        flash(
            "Unable to analyse this image. Please try another file."
        )

        return redirect(url_for("classify"))


# --------------------------------------------------
# 10. CAMERA CLASSIFICATION
# --------------------------------------------------

@app.route("/camera", methods=["GET", "POST"])
def camera():

    if request.method == "GET":
        return render_template("camera.html")

    camera_data = request.form.get(
        "camera_image",
        ""
    )

    if not camera_data:
        flash("Please capture an image first.")
        return redirect(url_for("camera"))

    filename = None

    try:

        if "," in camera_data:
            camera_data = camera_data.split(",", 1)[1]

        image_bytes = base64.b64decode(
            camera_data,
            validate=True
        )

        with Image.open(
            io.BytesIO(image_bytes)
        ) as source_image:

            image = source_image.convert("RGB")

        filename = f"{uuid.uuid4().hex}.jpg"

        image.save(
            UPLOAD_FOLDER / filename,
            format="JPEG",
            quality=92
        )

        prediction = predict_waste(image)

        save_history(
            filename,
            prediction["class"],
            prediction["confidence"],
            "camera"
        )

        return show_result(filename, prediction)

    except Exception:

        app.logger.exception(
            "Camera classification failed"
        )

        if filename and (UPLOAD_FOLDER / filename).exists():
            (UPLOAD_FOLDER / filename).unlink()

        flash("Unable to process camera image.")

        return redirect(url_for("camera"))


# --------------------------------------------------
# 11. VIDEO CLASSIFICATION
# --------------------------------------------------

@app.route("/video", methods=["GET", "POST"])
def video():

    if request.method == "GET":
        return render_template("video.html")

    file = request.files.get("video")

    if not file or not file.filename:
        flash("Please select a video.")
        return redirect(url_for("video"))

    if not allowed_file(file.filename, ALLOWED_VIDEOS):
        flash("Unsupported video format.")
        return redirect(url_for("video"))

    video_filename, video_path = save_upload(file)

    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():

        capture.release()

        flash("Unable to open the video.")

        return redirect(url_for("video"))

    analysed_frames = 0
    recognised_count = 0
    unknown_count = 0

    results = []

    frame_number = 0

    try:

        while len(results) < 30:

            success, frame = capture.read()

            if not success:
                break

            frame_number += 1

            # Analyse every 15th frame
            if frame_number % 15 != 0:
                continue

            analysed_frames += 1

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            image = Image.fromarray(rgb)

            prediction = predict_waste(image)

            if prediction["status"] == "success":
                recognised_count += 1
            else:
                unknown_count += 1

            image_filename = f"{uuid.uuid4().hex}.jpg"

            image.save(
                UPLOAD_FOLDER / image_filename,
                format="JPEG",
                quality=90
            )

            save_history(
                image_filename,
                prediction["class"],
                prediction["confidence"],
                "video"
            )

            # These keys match video_result.html
            results.append({
                "frame": frame_number,
                "waste_type": prediction["class"],
                "confidence": prediction["confidence"],
                "image_url": url_for(
                    "uploaded_file",
                    filename=image_filename
                )
            })

    finally:

        capture.release()

    if not results:

        flash(
            "No frames were sampled. Try a longer video."
        )

        return redirect(url_for("video"))

    return render_template(
        "video_result.html",
        total_frames=analysed_frames,
        recognised_count=recognised_count,
        unknown_count=unknown_count,
        results=results
    )


# --------------------------------------------------
# 12. CLASSIFICATION HISTORY
# --------------------------------------------------

@app.route("/history")
def history():

    with get_db() as connection:

        records = connection.execute("""
            SELECT *
            FROM history
            ORDER BY id DESC
        """).fetchall()

    # This variable matches history.html
    return render_template(
        "history.html",
        history=records
    )


# --------------------------------------------------
# 13. REPORTS
# --------------------------------------------------

@app.route("/reports")
def reports():

    with get_db() as connection:

        records = connection.execute("""
            SELECT waste_type, COUNT(*) AS count
            FROM history
            GROUP BY waste_type
        """).fetchall()

        total = connection.execute(
            "SELECT COUNT(*) FROM history"
        ).fetchone()[0]

    categories = {
        name: 0 for name in EXPECTED_CLASSES
    }

    unknown_count = 0

    for record in records:

        category = record["waste_type"]

        if category in categories:
            categories[category] = record["count"]
        else:
            unknown_count += record["count"]

    return render_template(
        "reports.html",
        total=total,
        categories=categories,
        unknown_count=unknown_count
    )


# --------------------------------------------------
# 14. SERVE UPLOADED FILES
# --------------------------------------------------

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# --------------------------------------------------
# 15. CLEAR HISTORY
# --------------------------------------------------

@app.route("/clear-history", methods=["POST"])
def clear_history():

    with get_db() as connection:

        connection.execute(
            "DELETE FROM history"
        )

        connection.commit()

    flash("Classification history cleared.")

    return redirect(url_for("history"))


# --------------------------------------------------
# 16. HEALTH CHECK
# --------------------------------------------------

@app.route("/health")
def health():

    return {
        "status": "healthy",
        "model": "loaded",
        "classes": CLASS_NAMES
    }


# --------------------------------------------------
# 17. RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
