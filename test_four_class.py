
import os
import json
import numpy as np
from PIL import Image
from ai_edge_litert.interpreter import Interpreter

# ---------------------------------
# CONFIGURATION
# ---------------------------------

MODEL_PATH = "waste_classifier.tflite"
CLASS_FILE = "class_names.json"

IMAGE_SIZE = (160, 160)

CONFIDENCE_THRESHOLD = 0.65
MARGIN_THRESHOLD = 0.15

# ---------------------------------
# LOAD CLASS NAMES
# ---------------------------------

if not os.path.exists(CLASS_FILE):
    raise FileNotFoundError(f"Missing file: {CLASS_FILE}")

with open(CLASS_FILE, "r") as file:
    classes = json.load(file)

EXPECTED_CLASSES = ["glass", "metal", "paper", "plastic"]

if classes != EXPECTED_CLASSES:
    raise ValueError(
        f"Incorrect class order in {CLASS_FILE}: {classes}"
    )

print("Classes loaded:", classes)

# ---------------------------------
# LOAD TFLITE MODEL
# ---------------------------------

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Missing model: {MODEL_PATH}")

interpreter = Interpreter(
    model_path=MODEL_PATH,
    num_threads=1
)

interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("TensorFlow Lite model loaded successfully!")

# ---------------------------------
# IMAGE PREPROCESSING
# ---------------------------------

def prepare_image(image_path):

    image = Image.open(image_path).convert("RGB")
    image = image.resize(IMAGE_SIZE)

    image_array = np.asarray(
        image,
        dtype=np.float32
    )

    image_array = np.expand_dims(image_array, axis=0)

    input_info = input_details[0]

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
        image_array = image_array.astype(input_info["dtype"])

    return image_array

# ---------------------------------
# MODEL PREDICTION
# ---------------------------------

def predict_image(image_path):

    image_array = prepare_image(image_path)

    input_info = input_details[0]
    output_info = output_details[0]

    interpreter.set_tensor(
        input_info["index"],
        image_array
    )

    interpreter.invoke()

    predictions = interpreter.get_tensor(
        output_info["index"]
    )[0]

    # Dequantize output if necessary
    if output_info["dtype"] in (np.uint8, np.int8):

        scale, zero_point = output_info["quantization"]

        if scale > 0:
            predictions = (
                predictions.astype(np.float32) - zero_point
            ) * scale

    predictions = predictions.astype(np.float32)

    # Convert logits to probabilities if necessary
    if (
        np.any(predictions < 0)
        or np.any(predictions > 1)
        or not np.isclose(
            np.sum(predictions),
            1.0,
            atol=0.02
        )
    ):

        predictions = predictions - np.max(predictions)

        exp_values = np.exp(predictions)

        predictions = exp_values / np.sum(exp_values)

    # ---------------------------------
    # UNKNOWN ITEM DETECTION
    # ---------------------------------

    order = np.argsort(predictions)[::-1]

    best_index = int(order[0])
    second_index = int(order[1])

    confidence = float(predictions[best_index])

    second_confidence = float(
        predictions[second_index]
    )

    margin = confidence - second_confidence

    if (
        confidence < CONFIDENCE_THRESHOLD
        or margin < MARGIN_THRESHOLD
    ):

        final_prediction = "Unknown Item"
        status = "UNKNOWN"

    else:

        final_prediction = classes[best_index]
        status = "CLASSIFIED"

    # ---------------------------------
    # DISPLAY RESULTS
    # ---------------------------------

    print("\n" + "=" * 40)
    print("         ECOSORT AI RESULTS")
    print("=" * 40)

    print("\nFinal Prediction:", final_prediction)

    print(
        "Confidence:",
        round(confidence * 100, 2),
        "%"
    )

    print(
        "Top-two margin:",
        round(margin * 100, 2),
        "%"
    )

    print("\nAll Class Probabilities:")

    for name, score in zip(classes, predictions):

        print(
            f"{name.capitalize():10s}: "
            f"{float(score) * 100:.2f}%"
        )

    print("\nStatus:", status)

    print("=" * 40)

    return final_prediction


# ---------------------------------
# MAIN PROGRAM
# ---------------------------------

if __name__ == "__main__":

    while True:

        image_path = input(
            "\nEnter image path (or type exit): "
        ).strip().strip('"').strip("'")

        if image_path.lower() == "exit":
            print("EcoSort AI testing completed.")
            break

        if not os.path.isfile(image_path):

            print("Error: Image file not found.")
            continue

        try:

            predict_image(image_path)

        except Exception as error:

            print("Prediction error:", error)
