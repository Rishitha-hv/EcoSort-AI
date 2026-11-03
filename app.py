
import os

# ==================================================
# 1. LIMIT CPU AND THREAD USAGE
# Must be configured before importing TensorFlow.
# ==================================================

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TF_NUM_INTRAOP_THREADS"] = "1"
os.environ["TF_NUM_INTEROP_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import io
import csv
import json
import base64
import sqlite3

from datetime import datetime
from collections import Counter

import numpy as np
import cv2
import tensorflow as tf

from PIL import Image, UnidentifiedImageError

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    Response,
    send_from_directory
)

from werkzeug.utils import secure_filename
from tensorflow.keras.models import load_model


# ==================================================
# 2. TENSORFLOW CONFIGURATION
# ==================================================

tf.config.threading.set_intra_op_parallelism_threads(1)
tf.config.threading.set_inter_op_parallelism_threads(1)


# ==================================================
# 3. FLASK CONFIGURATION
# ==================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "ecosort-ai-secret-key-change-this"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "waste_classifier_render.h5"
)

CLASS_FILE = os.path.join(
    BASE_DIR,
    "class_names.json"
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

DATABASE = os.path.join(
    BASE_DIR,
    "database.db"
)

IMAGE_SIZE = (160, 160)

CONFIDENCE_THRESHOLD = 0.65
MARGIN_THRESHOLD = 0.15

ALLOWED_IMAGES = {
    "jpg", "jpeg", "png", "webp"
}

ALLOWED_VIDEOS = {
    "mp4", "avi", "mov", "mkv"
}

EXPECTED_CLASSES = {
    "cardboard",
    "food",
    "glass",
    "metal",
    "paper",
    "plastic"
}


# ==================================================
# 4. LOAD TRAINED MODEL
# ==================================================

print("Loading EcoSort AI model...")

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}"
    )

if not os.path.exists(CLASS_FILE):
    raise FileNotFoundError(
        f"Class file not found: {CLASS_FILE}"
    )

model = load_model(
    MODEL_PATH,
    compile=False
)

with open(
    CLASS_FILE,
    "r",
    encoding="utf-8"
) as file:

    class_names = json.load(file)

if isinstance(class_names, dict):

    class_names = [
        name for name, index in
        sorted(
            class_names.items(),
            key=lambda item: item[1]
        )
    ]

class_names = [
    str(name).lower()
    for name in class_names
]

if len(class_names) != model.output_shape[-1]:

    raise ValueError(
        "Number of class names does not match model output."
    )

if set(class_names) != EXPECTED_CLASSES:

    raise ValueError(
        f"Expected classes: {sorted(EXPECTED_CLASSES)}. "
        f"Found: {class_names}"
    )

print("Model loaded successfully!")
print("Classes:", class_names)


# ==================================================
# 5. DATABASE
# ==================================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE,
        timeout=20
    )

    connection.row_factory = sqlite3.Row

    return connection


def create_database():

    connection = get_connection()

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
    connection.close()


def save_history(
    filename,
    waste_type,
    confidence,
    source
):

    connection = get_connection()

    try:

        connection.execute("""
            INSERT INTO history
            (filename, waste_type, confidence, source, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            filename,
            waste_type,
            round(confidence * 100, 2),
            source,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

        connection.commit()

    finally:

        connection.close()


create_database()


# ==================================================
# 6. FILE VALIDATION
# ==================================================

def allowed_file(filename, extensions):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in extensions
    )


def create_unique_filename(original_name):

    safe_name = secure_filename(original_name)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    return f"{timestamp}_{safe_name}"


# ==================================================
# 7. IMAGE PREPROCESSING
# ==================================================

def prepare_image(image):

    image = image.convert("RGB")

    image = image.resize(
        IMAGE_SIZE,
        Image.Resampling.BILINEAR
    )

    image_array = np.asarray(
        image,
        dtype=np.float32
    )

    image_array = np.expand_dims(
        image_array,
        axis=0
    )

    return image_array


# ==================================================
# 8. WASTE CLASSIFICATION
# ==================================================

def classify_image(image):

    processed_image = prepare_image(image)

    # Direct inference instead of model.predict().
    predictions = model(
        processed_image,
        training=False
    ).numpy()[0]

    predictions = np.asarray(
        predictions,
        dtype=np.float32
    )

    if not np.all(np.isfinite(predictions)):

        return "Unknown Item", 0.0

    # Convert logits into probabilities if required.
    if (
        np.min(predictions) < 0
        or np.max(predictions) > 1
        or not np.isclose(
            np.sum(predictions),
            1.0,
            atol=0.01
        )
    ):

        shifted = predictions - np.max(predictions)

        exp_values = np.exp(shifted)

        predictions = (
            exp_values / np.sum(exp_values)
        )

    sorted_indices = np.argsort(
        predictions
    )[::-1]

    best_index = int(
        sorted_indices[0]
    )

    confidence = float(
        predictions[best_index]
    )

    second_confidence = float(
        predictions[sorted_indices[1]]
    )

    margin = (
        confidence - second_confidence
    )

    predicted_class = class_names[best_index]

    # Unknown item rejection.
    if (
        confidence < CONFIDENCE_THRESHOLD
        or margin < MARGIN_THRESHOLD
    ):

        return "Unknown Item", confidence

    return predicted_class.title(), confidence


# ==================================================
# 9. SAVE IMAGE
# ==================================================

def save_image(image, filename):

    filepath = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    image.save(
        filepath,
        format="JPEG",
        quality=85
    )

    return filepath


# ==================================================
# 10. HOME PAGE
# ==================================================

@app.route("/")
def home():

    connection = get_connection()

    try:

        total = connection.execute(
            "SELECT COUNT(*) FROM history"
        ).fetchone()[0]

        records = connection.execute("""
            SELECT * FROM history
            ORDER BY id DESC
            LIMIT 5
        """).fetchall()

        counts = connection.execute("""
            SELECT waste_type, COUNT(*) AS total
            FROM history
            GROUP BY waste_type
        """).fetchall()

    finally:

        connection.close()

    waste_counts = {
        row["waste_type"]: row["total"]
        for row in counts
    }

    return render_template(
        "index.html",
        total=total,
        records=records,
        waste_counts=waste_counts
    )


# ==================================================
# 11. IMAGE CLASSIFICATION
# ==================================================

@app.route("/classify", methods=["GET", "POST"])
def classify():

    if request.method == "POST":

        file = request.files.get("image")

        if not file or not file.filename:

            flash("Please select an image.")

            return redirect(
                url_for("classify")
            )

        if not allowed_file(
            file.filename,
            ALLOWED_IMAGES
        ):

            flash("Please upload a valid image.")

            return redirect(
                url_for("classify")
            )

        try:

            image = Image.open(
                file.stream
            ).convert("RGB")

            filename = create_unique_filename(
                file.filename
            )

            save_image(
                image,
                filename
            )

            predicted_class, confidence = classify_image(
                image
            )

            save_history(
                filename,
                predicted_class,
                confidence,
                "Image Upload"
            )

            return render_template(
                "result.html",
                filename=filename,
                image_url=url_for(
                    "uploaded_file",
                    filename=filename
                ),
                predicted_class=predicted_class,
                confidence=round(
                    confidence * 100,
                    2
                )
            )

        except (UnidentifiedImageError, OSError):

            flash("The uploaded file is not a valid image.")

            return redirect(
                url_for("classify")
            )

        except Exception:

            app.logger.exception(
                "Image classification error"
            )

            flash("Unable to process the image.")

            return redirect(
                url_for("classify")
            )

    return render_template(
        "classify.html"
    )


# ==================================================
# 12. CAMERA CAPTURE
# ==================================================

@app.route("/camera", methods=["GET", "POST"])
def camera():

    if request.method == "POST":

        image_data = request.form.get(
            "camera_image"
        )

        if (
            not image_data
            or "," not in image_data
        ):

            flash("Please capture an image.")

            return redirect(
                url_for("camera")
            )

        try:

            encoded_image = image_data.split(
                ",",
                1
            )[1]

            image_bytes = base64.b64decode(
                encoded_image,
                validate=True
            )

            image = Image.open(
                io.BytesIO(image_bytes)
            ).convert("RGB")

            filename = create_unique_filename(
                "camera.jpg"
            )

            save_image(
                image,
                filename
            )

            predicted_class, confidence = classify_image(
                image
            )

            save_history(
                filename,
                predicted_class,
                confidence,
                "Camera"
            )

            return render_template(
                "result.html",
                filename=filename,
                image_url=url_for(
                    "uploaded_file",
                    filename=filename
                ),
                predicted_class=predicted_class,
                confidence=round(
                    confidence * 100,
                    2
                )
            )

        except (UnidentifiedImageError, OSError, ValueError):

            flash("The captured image is invalid. Please try again.")

            return redirect(
                url_for("camera")
            )

        except Exception:

            app.logger.exception(
                "Camera processing error"
            )

            flash("Unable to process the captured image.")

            return redirect(
                url_for("camera")
            )

    return render_template(
        "camera.html"
    )


# ==================================================
# 13. VIDEO CLASSIFICATION
# ==================================================

@app.route("/video", methods=["GET", "POST"])
def video():

    if request.method == "POST":

        file = request.files.get("video")

        if not file or not file.filename:

            flash("Please select a video.")

            return redirect(
                url_for("video")
            )

        if not allowed_file(
            file.filename,
            ALLOWED_VIDEOS
        ):

            flash("Please upload a supported video.")

            return redirect(
                url_for("video")
            )

        filename = create_unique_filename(
            file.filename
        )

        filepath = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        capture = None

        try:

            file.save(filepath)

            capture = cv2.VideoCapture(
                filepath
            )

            if not capture.isOpened():

                flash("Unable to open video.")

                return redirect(
                    url_for("video")
                )

            results = []

            frame_number = 0

            # Limit video processing to 300 frames.
            max_frames = 300

            while frame_number < max_frames:

                success, frame = capture.read()

                if not success:
                    break

                frame_number += 1

                # Process every 30th frame.
                if frame_number % 30 != 0:
                    continue

                frame_rgb = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB
                )

                image = Image.fromarray(
                    frame_rgb
                )

                predicted_class, confidence = classify_image(
                    image
                )

                results.append({
                    "frame": frame_number,
                    "waste_type": predicted_class,
                    "confidence": round(
                        confidence * 100,
                        2
                    )
                })

                save_history(
                    filename,
                    predicted_class,
                    confidence,
                    f"Video Frame {frame_number}"
                )

            if not results:

                flash(
                    "No video frames were available for analysis."
                )

                return redirect(
                    url_for("video")
                )

            summary = dict(
                Counter(
                    item["waste_type"]
                    for item in results
                )
            )

            return render_template(
                "video_result.html",
                results=results,
                summary=summary,
                total_frames=len(results)
            )

        except Exception:

            app.logger.exception(
                "Video processing error"
            )

            flash("Unable to analyze the video.")

            return redirect(
                url_for("video")
            )

        finally:

            if capture is not None:
                capture.release()

    return render_template(
        "video.html"
    )


# ==================================================
# 14. CLASSIFICATION HISTORY
# ==================================================

@app.route("/history")
def history():

    connection = get_connection()

    try:

        records = connection.execute("""
            SELECT * FROM history
            ORDER BY id DESC
        """).fetchall()

    finally:

        connection.close()

    return render_template(
        "history.html",
        records=records
    )


# ==================================================
# 15. REPORTS
# ==================================================

@app.route("/reports")
def reports():

    connection = get_connection()

    try:

        counts = connection.execute("""
            SELECT waste_type, COUNT(*) AS total
            FROM history
            GROUP BY waste_type
        """).fetchall()

        total = connection.execute(
            "SELECT COUNT(*) FROM history"
        ).fetchone()[0]

    finally:

        connection.close()

    waste_counts = {
        row["waste_type"]: row["total"]
        for row in counts
    }

    return render_template(
        "reports.html",
        counts=waste_counts,
        total=total
    )


# ==================================================
# 16. CSV REPORT DOWNLOAD
# ==================================================

@app.route("/download-report")
def download_report():

    connection = get_connection()

    try:

        records = connection.execute("""
            SELECT * FROM history
            ORDER BY id DESC
        """).fetchall()

    finally:

        connection.close()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Filename",
        "Waste Type",
        "Confidence",
        "Source",
        "Timestamp"
    ])

    for row in records:

        writer.writerow([
            row["id"],
            row["filename"],
            row["waste_type"],
            row["confidence"],
            row["source"],
            row["timestamp"]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=EcoSort_AI_Report.csv"
        }
    )


# ==================================================
# 17. DISPLAY UPLOADED IMAGES
# ==================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# ==================================================
# 18. CLEAR HISTORY
# ==================================================

@app.route("/clear-history", methods=["POST"])
def clear_history():

    connection = get_connection()

    try:

        connection.execute(
            "DELETE FROM history"
        )

        connection.commit()

    finally:

        connection.close()

    flash("Classification history cleared.")

    return redirect(
        url_for("history")
    )


# ==================================================
# 19. HEALTH CHECK
# ==================================================

@app.route("/health")
def health():

    return {
        "status": "running",
        "application": "EcoSort AI",
        "model_loaded": model is not None,
        "classes": class_names
    }


# ==================================================
# 20. ERROR HANDLERS
# ==================================================

@app.errorhandler(413)
def file_too_large(error):

    flash(
        "File size exceeds the 100 MB limit."
    )

    return redirect(
        url_for("home")
    )


# ==================================================
# 21. RUN APPLICATION
# ==================================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    print("-----------------------------------")
    print("          ECOSORT AI WEBSITE")
    print("-----------------------------------")
    print(f"Port: {port}")
    print("Application starting...")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        threaded=False
    )
