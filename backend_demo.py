import json
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf

MODEL_PATH = Path("waste_classifier.keras")
CLASS_FILE = Path("class_names.json")

IMAGE_SIZE = (160, 160)

CONFIDENCE_THRESHOLD = 0.65
MINIMUM_MARGIN = 0.15

if not MODEL_PATH.exists():
    raise FileNotFoundError("waste_classifier.keras not found.")

if not CLASS_FILE.exists():
    raise FileNotFoundError("class_names.json not found.")

with open(CLASS_FILE, "r", encoding="utf-8") as f:
    CLASS_NAMES = json.load(f)

model = tf.keras.models.load_model(str(MODEL_PATH))

if model.output_shape[-1] != len(CLASS_NAMES):
    raise ValueError("Model and class names do not match.")


def predict_image(frame):

    # OpenCV BGR to RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Resize image
    resized = cv2.resize(rgb, IMAGE_SIZE)

    # Convert to float32
    image = resized.astype(np.float32)

    # Add batch dimension
    image = np.expand_dims(image, axis=0)

    # Predict
    predictions = model.predict(image, verbose=0)[0]

    order = np.argsort(predictions)[::-1]

    best_index = int(order[0])

    confidence = float(predictions[best_index])

    second_confidence = float(predictions[order[1]])

    margin = confidence - second_confidence

    if (
        confidence >= CONFIDENCE_THRESHOLD
        and margin >= MINIMUM_MARGIN
    ):
        label = CLASS_NAMES[best_index].upper()
    else:
        label = "UNKNOWN ITEM"

    return label, confidence, predictions


def main():

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        camera.release()
        raise RuntimeError(
            "Webcam not available. Try camera index 1."
        )

    print("Webcam started. Press Q to quit.")

    try:

        while True:

            success, frame = camera.read()

            if not success:
                print("Unable to read webcam.")
                break

            height, width = frame.shape[:2]

            crop_size = int(min(height, width) * 0.80)

            x1 = (width - crop_size) // 2
            y1 = (height - crop_size) // 2

            crop = frame[
                y1:y1 + crop_size,
                x1:x1 + crop_size
            ]

            label, confidence, predictions = predict_image(crop)

            if label == "UNKNOWN ITEM":
                color = (0, 0, 255)
            else:
                color = (0, 200, 0)

            cv2.rectangle(
                frame,
                (x1, y1),
                (x1 + crop_size, y1 + crop_size),
                color,
                2
            )

            cv2.putText(
                frame,
                label,
                (15, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                color,
                2
            )

            cv2.putText(
                frame,
                f"Top score: {confidence * 100:.1f}%",
                (15, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 0),
                2
            )

            cv2.imshow(
                "Waste Classification System",
                frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:

        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()