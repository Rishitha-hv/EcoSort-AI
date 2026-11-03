
import tensorflow as tf
import os

MODEL_PATH = "waste_classifier_render.h5"
OUTPUT_PATH = "waste_classifier.tflite"

print("Loading existing model...")

model = tf.keras.models.load_model(
    MODEL_PATH,
    compile=False
)

print("Model loaded successfully!")

print("Converting to TensorFlow Lite...")

converter = tf.lite.TFLiteConverter.from_keras_model(model)

# Enable default optimization.
converter.optimizations = [
    tf.lite.Optimize.DEFAULT
]

tflite_model = converter.convert()

with open(OUTPUT_PATH, "wb") as file:
    file.write(tflite_model)

print("Conversion completed!")

print(
    "TFLite model size:",
    round(os.path.getsize(OUTPUT_PATH) / (1024 * 1024), 2),
    "MB"
)

# Verify that the model can be loaded.
interpreter = tf.lite.Interpreter(
    model_path=OUTPUT_PATH,
    num_threads=1
)

interpreter.allocate_tensors()

print("TFLite model verification successful!")
print("Input:", interpreter.get_input_details()[0]["shape"])
print("Output:", interpreter.get_output_details()[0]["shape"])
