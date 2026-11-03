import json
import threading
import numpy as np
from PIL import Image
from ai_edge_litert.interpreter import Interpreter

MODEL_PATH = "waste_classifier.tflite"
CLASS_FILE = "class_names.json"

CONFIDENCE_THRESHOLD = 0.65
MARGIN_THRESHOLD = 0.15

with open(CLASS_FILE, "r") as file:
    CLASS_NAMES = json.load(file)

interpreter = Interpreter(
    model_path=MODEL_PATH,
    num_threads=1
)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

inference_lock = threading.Lock()


def predict_waste(image):
    # Convert to RGB and resize
    image = image.convert("RGB")
    image = image.resize((160, 160))

    # Model expects float32 RGB pixels in the 0–255 range
    image_array = np.asarray(image, dtype=np.float32)
    image_array = np.expand_dims(image_array, axis=0)

    input_info = input_details[0]
    output_info = output_details[0]

    # Handle quantized model input if necessary
    if input_info["dtype"] in (np.uint8, np.int8):
        scale, zero_point = input_info["quantization"]
        if scale > 0:
            image_array = np.round(image_array / scale + zero_point)

        limits = np.iinfo(input_info["dtype"])
        image_array = np.clip(
            image_array, limits.min, limits.max
        ).astype(input_info["dtype"])
    else:
        image_array = image_array.astype(input_info["dtype"])

    with inference_lock:
        interpreter.set_tensor(input_info["index"], image_array)
        interpreter.invoke()
        predictions = interpreter.get_tensor(output_info["index"])[0]

    # Dequantize output if required
    if output_info["dtype"] in (np.uint8, np.int8):
        scale, zero_point = output_info["quantization"]
        if scale > 0:
            predictions = (predictions.astype(np.float32) - zero_point) * scale

    predictions = predictions.astype(np.float32)

    # Convert logits to probabilities if output is not already softmax
    if (
        np.any(predictions < 0)
        or np.any(predictions > 1)
        or not np.isclose(np.sum(predictions), 1.0, atol=0.02)
    ):
        predictions = tf_softmax(predictions)

    # Sort probabilities
    order = np.argsort(predictions)[::-1]
    best_index = int(order[0])

    confidence = float(predictions[best_index])
    second_confidence = float(predictions[order[1]])
    margin = confidence - second_confidence

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


def tf_softmax(values):
    values = values - np.max(values)
    exp_values = np.exp(values)
    return exp_values / np.sum(exp_values)