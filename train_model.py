import os
import json
import numpy as np
import tensorflow as tf

from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# Reduce resource usage on your computer
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
tf.config.threading.set_intra_op_parallelism_threads(2)
tf.config.threading.set_inter_op_parallelism_threads(2)

DATASET_DIR = "dataset"
IMAGE_SIZE = (160, 160)
BATCH_SIZE = 8
EPOCHS = 15
SEED = 42

# Only these four classes will be trained
CLASS_NAMES = ["glass", "metal", "paper", "plastic"]

# Verify folders
for class_name in CLASS_NAMES:
    folder = os.path.join(DATASET_DIR, class_name)
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Missing dataset folder: {folder}")

# Load training and validation datasets
train_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR,
    class_names=CLASS_NAMES,
    validation_split=0.2,
    subset="training",
    seed=SEED,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    label_mode="int"
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR,
    class_names=CLASS_NAMES,
    validation_split=0.2,
    subset="validation",
    seed=SEED,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    label_mode="int"
)

print("Class order:", train_ds.class_names)

# Improve input pipeline efficiency
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.prefetch(AUTOTUNE)
val_ds = val_ds.prefetch(AUTOTUNE)

# Data augmentation
augmentation = models.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.08),
    layers.RandomZoom(0.10),
], name="augmentation")

# MobileNetV2 base
base_model = MobileNetV2(
    weights="imagenet",
    include_top=False,
    input_shape=(160, 160, 3)
)
base_model.trainable = False

# The model receives RGB pixels in the 0–255 range.
# This rescaling layer is part of the saved model.
inputs = layers.Input(shape=(160, 160, 3))
x = augmentation(inputs)
x = layers.Rescaling(1.0 / 127.5, offset=-1)(x)
x = base_model(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.3)(x)
x = layers.Dense(128, activation="relu")(x)
x = layers.Dropout(0.2)(x)
outputs = layers.Dense(4, activation="softmax")(x)

model = models.Model(inputs, outputs)

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0005),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

callbacks = [
    EarlyStopping(
        monitor="val_loss",
        patience=4,
        restore_best_weights=True
    ),
    ModelCheckpoint(
        "best_four_class.keras",
        monitor="val_loss",
        save_best_only=True
    )
]

print("\nStarting four-class training...")

history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks
)

# Save best model
model = tf.keras.models.load_model("best_four_class.keras")
model.save("waste_classifier_four.keras")

# Save exact class order
with open("class_names.json", "w") as file:
    json.dump(CLASS_NAMES, file, indent=4)

# Convert to TensorFlow Lite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

with open("waste_classifier.tflite", "wb") as file:
    file.write(tflite_model)

print("\nTraining and conversion completed!")
print("Classes:", CLASS_NAMES)
print("Saved: waste_classifier_four.keras")
print("Saved: class_names.json")
print("Saved: waste_classifier.tflite")