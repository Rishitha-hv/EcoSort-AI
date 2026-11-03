
import os
import json
import numpy as np
from PIL import Image
from tensorflow.keras.models import load_model, Model

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "waste_classifier.keras")
CLASS_PATH = os.path.join(BASE_DIR, "class_names.json")
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
OUTPUT_PATH = os.path.join(BASE_DIR, "open_set_reference.npz")

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def load_classes():
    with open(CLASS_PATH, "r", encoding="utf-8") as f:
        classes = json.load(f)

    if isinstance(classes, dict):
        classes = [
            name for name, index in sorted(
                classes.items(), key=lambda item: item[1]
            )
        ]

    return [str(c) for c in classes]


def make_embedding(vector):
    vector = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(vector)
    if norm > 1e-10:
        vector = vector / norm
    return vector


def main():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Missing model: {MODEL_PATH}")

    if not os.path.exists(CLASS_PATH):
        raise FileNotFoundError(f"Missing class file: {CLASS_PATH}")

    if not os.path.isdir(DATASET_DIR):
        raise FileNotFoundError(f"Missing dataset folder: {DATASET_DIR}")

    model = load_model(MODEL_PATH)
    classes = load_classes()

    if len(classes) != int(model.output_shape[-1]):
        raise ValueError(
            "class_names.json does not match the model output size."
        )

    # Use the layer just before the final classification layer
    # as the image feature representation.
    feature_model = Model(
        inputs=model.inputs,
        outputs=model.layers[-2].output
    )

    input_shape = model.input_shape
    image_height = int(input_shape[1])
    image_width = int(input_shape[2])

    centroids = []
    thresholds = []

    for class_name in classes:
        folder = os.path.join(DATASET_DIR, class_name)

        if not os.path.isdir(folder):
            raise FileNotFoundError(
                f"Missing class folder: {folder}"
            )

        embeddings = []
        files = [
            os.path.join(folder, name)
            for name in os.listdir(folder)
            if name.lower().endswith(IMAGE_EXTENSIONS)
        ]

        if len(files) < 2:
            raise ValueError(
                f"Add at least 2 images to {folder}"
            )

        print(f"Processing {class_name}: {len(files)} images")

        for path in files:
            try:
                with Image.open(path) as image:
                    image = image.convert("RGB").resize(
                        (image_width, image_height)
                    )
                    array = np.asarray(
                        image, dtype=np.float32
                    )[None, ...]

                feature = feature_model.predict(
                    array, verbose=0
                )[0]

                embeddings.append(make_embedding(feature))

            except Exception as error:
                print(f"Skipping {path}: {error}")

        if len(embeddings) < 2:
            raise ValueError(
                f"Not enough readable images in {folder}"
            )

        embeddings = np.asarray(embeddings, dtype=np.float32)

        # Average features into a reference for this known class.
        centroid = make_embedding(np.mean(embeddings, axis=0))

        # Measure how far the training images are from their class reference.
        distances = 1.0 - np.clip(
            embeddings @ centroid, -1.0, 1.0
        )

        # Set a class-specific rejection threshold.
        threshold = float(np.percentile(distances, 99) + 0.05)
        threshold = min(threshold, 1.0)

        centroids.append(centroid)
        thresholds.append(threshold)

        print(
            f"  Reference built. Distance threshold: "
            f"{threshold:.4f}"
        )

    np.savez(
        OUTPUT_PATH,
        centroids=np.asarray(centroids, dtype=np.float32),
        thresholds=np.asarray(thresholds, dtype=np.float32),
        class_names=np.asarray(classes)
    )

    print("\nUnknown-object reference saved:")
    print(OUTPUT_PATH)
    print("Classes:", classes)
    print("\nNext, update predict_image() in app.py.")


if __name__ == "__main__":
    main()
