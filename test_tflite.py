
import json
import numpy as np
import tensorflow as tf

from PIL import Image

# Load class names
with open("class_names.json", "r") as f:
    class_names = json.load(f)

if isinstance(class_names, dict):
    class_names = [
        name for name, index in
        sorted(class_names.items(), key=lambda x: x[1])
    ]

# Load original model
original_model = tf.keras.models.load_model(
    "waste_classifier_render.h5",
    compile=False
)

# Load TFLite model
interpreter = tf.lite.Interpreter(
    model_path="waste_classifier.tflite",
    num_threads=1
)

interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Change this to an existing JPG image
IMAGE_PATH = "test.jpg"

image = Image.open(IMAGE_PATH).convert("RGB")
image = image.resize((160, 160))

image_array = np.asarray(
    image,
    dtype=np.float32
)

image_array = np.expand_dims(image_array, axis=0)

# Original prediction
original_prediction = original_model(
    image_array,
    training=False
).numpy()[0]

# TFLite prediction
interpreter.set_tensor(
    input_details[0]["index"],
    image_array
)

interpreter.invoke()

tflite_prediction = interpreter.get_tensor(
    output_details[0]["index"]
)[0]

# Compare predictions
print("\nORIGINAL MODEL:")
original_index = int(np.argmax(original_prediction))
print("Class:", class_names[original_index])
print("Confidence:", round(float(original_prediction[original_index]) * 100, 2), "%")

print("\nTFLITE MODEL:")
tflite_index = int(np.argmax(tflite_prediction))
print("Class:", class_names[tflite_index])
print("Confidence:", round(float(tflite_prediction[tflite_index]) * 100, 2), "%")

print("\nPREDICTION COMPARISON:")
print("Same predicted class:", original_index == tflite_index)
print(
    "Maximum probability difference:",
    float(np.max(np.abs(original_prediction - tflite_prediction)))
)
