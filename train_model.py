import json
from pathlib import Path

import tensorflow as tf
from tensorflow.keras import layers, models

# Configuration
DATASET_DIR = Path("dataset")
MODEL_PATH = "waste_classifier.keras"
CLASS_FILE = "class_names.json"

CLASS_NAMES = [
    "cardboard",
    "food",
    "glass",
    "metal",
    "paper",
    "plastic"
]

IMAGE_SIZE = (160, 160)
BATCH_SIZE = 8
EPOCHS = 12
SEED = 42

tf.keras.utils.set_random_seed(SEED)


# Check dataset
def check_dataset():

    if not DATASET_DIR.exists():
        raise FileNotFoundError("Dataset folder not found.")

    for class_name in CLASS_NAMES:

        folder = DATASET_DIR / class_name

        if not folder.exists():
            raise ValueError(f"Missing folder: {folder}")

        images = [
            p for p in folder.rglob("*")
            if p.suffix.lower() in
            [".jpg", ".jpeg", ".png", ".bmp", ".webp"]
        ]

        print(f"{class_name}: {len(images)} images")

        if len(images) < 2:
            raise ValueError(
                f"Not enough images in {folder}"
            )


# Load dataset
def load_datasets():

    train_ds = tf.keras.utils.image_dataset_from_directory(
        str(DATASET_DIR),
        labels="inferred",
        label_mode="int",
        class_names=CLASS_NAMES,
        validation_split=0.2,
        subset="training",
        seed=SEED,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        shuffle=True
    )

    val_ds = tf.keras.utils.image_dataset_from_directory(
        str(DATASET_DIR),
        labels="inferred",
        label_mode="int",
        class_names=CLASS_NAMES,
        validation_split=0.2,
        subset="validation",
        seed=SEED,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        shuffle=False
    )

    print("Class mapping:")
    print(dict(enumerate(train_ds.class_names)))

    return train_ds.prefetch(1), val_ds.prefetch(1)


# Build MobileNetV2 model
def build_model():

    augmentation = models.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.08),
        layers.RandomZoom(0.12),
        layers.RandomContrast(0.10)
    ])

    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(160, 160, 3),
        include_top=False,
        weights="imagenet"
    )

    base_model.trainable = False

    inputs = layers.Input(shape=(160, 160, 3))

    x = augmentation(inputs)

    # Normalize pixel values from 0-255 to -1 to 1.
    x = layers.Rescaling(
        1.0 / 127.5,
        offset=-1.0
    )(x)

    x = base_model(x, training=False)

    x = layers.GlobalAveragePooling2D()(x)

    x = layers.Dropout(0.30)(x)

    x = layers.Dense(
        128,
        activation="relu"
    )(x)

    x = layers.Dropout(0.20)(x)

    outputs = layers.Dense(
        len(CLASS_NAMES),
        activation="softmax"
    )(x)

    model = models.Model(inputs, outputs)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(
            learning_rate=0.0003
        ),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )

    return model


# Train model
def main():

    check_dataset()

    with open(CLASS_FILE, "w", encoding="utf-8") as f:
        json.dump(CLASS_NAMES, f, indent=4)

    train_ds, val_ds = load_datasets()

    model = build_model()

    model.summary()

    callbacks = [

        tf.keras.callbacks.ModelCheckpoint(
            MODEL_PATH,
            monitor="val_accuracy",
            save_best_only=True,
            mode="max",
            verbose=1
        ),

        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=3,
            restore_best_weights=True,
            verbose=1
        ),

        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=2,
            min_lr=0.00001,
            verbose=1
        )
    ]

    print("\nStarting training...")

    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS,
        callbacks=callbacks
    )

    model.save(MODEL_PATH)

    print("\nTraining completed successfully.")
    print("Model saved:", MODEL_PATH)
    print("Classes saved:", CLASS_FILE)


if __name__ == "__main__":
    main()