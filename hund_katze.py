import os

import numpy as np
import streamlit as st
import tensorflow as tf
from PIL import Image


# -----------------------------
# Einstellungen
# -----------------------------

MODEL_PATH = "katzen_hunde_modell.h5"

# Diese Zuordnung gegebenenfalls an dein Training anpassen.
# Bei sigmoid-Ausgabe gilt hier:
# 0 = Katze, 1 = Hund
CLASS_NAMES = ["Katze", "Hund"]


# -----------------------------
# Modell laden
# -----------------------------

@st.cache_resource
def load_model():
    """Lädt das Keras-Modell nur einmal."""
    return tf.keras.models.load_model(MODEL_PATH)


def get_image_size(model):
    """
    Ermittelt die erwartete Bildgröße des Modells.
    Fallback: 224 x 224 Pixel.
    """
    input_shape = model.input_shape

    # Typische Form: (None, Höhe, Breite, Kanäle)
    if isinstance(input_shape, list):
        input_shape = input_shape[0]

    if len(input_shape) == 4:
        height = input_shape[1] or 224
        width = input_shape[2] or 224
        return int(width), int(height)

    return 224, 224


def preprocess_image(image, model):
    """Bereitet das Bild für das Modell vor."""
    width, height = get_image_size(model)

    image = image.convert("RGB")
    image = image.resize((width, height))

    image_array = np.asarray(image).astype("float32")

    # Häufige Normalisierung für Bildmodelle:
    # Pixelwerte von 0-255 auf 0-1 skalieren.
    image_array = image_array / 255.0

    # Batch-Dimension hinzufügen:
    # (Höhe, Breite, Kanäle) -> (1, Höhe, Breite, Kanäle)
    image_array = np.expand_dims(image_array, axis=0)

    return image_array


def predict_image(model, image):
    """Erzeugt eine Vorhersage für ein Bild."""
    input_data = preprocess_image(image, model)
    prediction = model.predict(input_data, verbose=0)

    prediction = np.asarray(prediction)

    # Fall 1: Binäres Modell mit Sigmoid-Ausgabe
    # Beispielausgabe: [[0.83]]
    if prediction.size == 1:
        dog_probability = float(prediction.reshape(-1)[0])

        # Falls dein Training 0 = Hund und 1 = Katze verwendet,
        # diese beiden Zeilen entsprechend umkehren.
        probabilities = np.array([
            1.0 - dog_probability,  # Katze
            dog_probability         # Hund
        ])

    # Fall 2: Zwei Ausgabewerte mit Softmax
    # Beispielausgabe: [[0.15, 0.85]]
    else:
        probabilities = prediction.reshape(-1)[:2]

        # Falls dein Training die Reihenfolge [Hund, Katze] verwendet,
        # musst du probabilities hier umsortieren.
        probabilities = probabilities / np.sum(probabilities)

    predicted_index = int(np.argmax(probabilities))
    predicted_class = CLASS_NAMES[predicted_index]
    confidence = float(probabilities[predicted_index])

    return predicted_class, confidence, probabilities


# -----------------------------
# Streamlit-Oberfläche
# -----------------------------

st.set_page_config(
    page_title="Katzen- oder Hunde-Erkennung",
    page_icon="🐶",
    layout="centered"
)

st.title("🐶🐱 Katzen- und Hunde-Erkennung")
st.write("Lade ein Bild hoch. Das Modell versucht zu erkennen, ob darauf eine Katze oder ein Hund zu sehen ist.")

if not os.path.exists(MODEL_PATH):
    st.error(
        f"Das Modell wurde nicht gefunden: `{MODEL_PATH}`\n\n"
        "Lege deine H5-Datei in denselben Ordner wie `app.py` "
        "und benenne sie entsprechend um."
    )
    st.stop()

try:
    model = load_model()
except Exception as error:
    st.error(f"Das Modell konnte nicht geladen werden:\n\n{error}")
    st.stop()

uploaded_file = st.file_uploader(
    "Bild auswählen",
    type=["jpg", "jpeg", "png", "webp"]
)

if uploaded_file is not None:
    image = Image.open(uploaded_file)

    st.image(
        image,
        caption="Hochgeladenes Bild",
        use_container_width=True
    )

    if st.button("Bild analysieren", type="primary"):
        with st.spinner("Bild wird analysiert ..."):
            predicted_class, confidence, probabilities = predict_image(
                model,
                image
            )

        st.success(
            f"Ergebnis: **{predicted_class}** "
            f"({confidence * 100:.2f} % Sicherheit)"
        )

        st.subheader("Wahrscheinlichkeiten")

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Katze",
                f"{probabilities[0] * 100:.2f} %"
            )

        with col2:
            st.metric(
                "Hund",
                f"{probabilities[1] * 100:.2f} %"
            )

        st.progress(confidence)
