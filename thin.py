import streamlit as st
import cv2
import numpy as np
from skimage import feature
import google.genai as genai
import tempfile
import os

# ============================
# 🔑 CONFIGURE GEMINI API
# ============================
GEMINI_API_KEY = "AIzaSyCB3YnFiAoNP6FLSsm6CGXg6U1npmBZOiw"   # replace



# ============================
# 🧠 IMAGE ANALYSIS
# ============================
def analyze_leaf_image(image_path: str) -> dict:
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Image not found: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, w = img.shape[:2]

    result = {}
    result["width"], result["height"] = w, h
    result["mean_intensity"] = np.mean(gray)
    result["std_intensity"] = np.std(gray)

    # Green ratio
    green_mask = (hsv[:, :, 0] > 35) & (hsv[:, :, 0] < 85)
    result["green_ratio"] = np.sum(green_mask) / (h * w)

    # Yellow ratio
    yellow_mask = (hsv[:, :, 0] > 20) & (hsv[:, :, 0] < 35)
    result["yellow_ratio"] = np.sum(yellow_mask) / (h * w)

    # Brown/black spots
    brown_mask = (hsv[:, :, 0] > 10) & (hsv[:, :, 0] < 25) & (hsv[:, :, 2] < 120)
    result["brown_ratio"] = np.sum(brown_mask) / (h * w)

    # Dark spot area
    _, thresh = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)
    result["dark_spot_ratio"] = np.sum(thresh > 0) / (h * w)

    # Shape features
    contours, _ = cv2.findContours(
        cv2.Canny(gray, 50, 150), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if contours:
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        perimeter = cv2.arcLength(largest, True)
        result["leaf_area"] = area
        result["leaf_perimeter"] = perimeter
        result["leaf_compactness"] = (4 * np.pi * area) / (perimeter ** 2 + 1e-6)
    else:
        result["leaf_area"] = result["leaf_perimeter"] = result["leaf_compactness"] = 0

    # Texture features
    glcm = feature.graycomatrix(gray, [5], [0], 256, symmetric=True, normed=True)
    result["texture_contrast"] = feature.graycoprops(glcm, "contrast")[0, 0]
    result["texture_dissimilarity"] = feature.graycoprops(glcm, "dissimilarity")[0, 0]
    result["texture_homogeneity"] = feature.graycoprops(glcm, "homogeneity")[0, 0]
    result["texture_energy"] = feature.graycoprops(glcm, "energy")[0, 0]
    result["texture_correlation"] = feature.graycoprops(glcm, "correlation")[0, 0]

    # Edge density
    edges = cv2.Canny(gray, 100, 200)
    result["edge_density"] = np.sum(edges > 0) / (h * w)

    # Hole detection
    im_floodfill = thresh.copy()
    mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(im_floodfill, mask, (0, 0), 255)
    im_floodfill_inv = cv2.bitwise_not(im_floodfill)
    holes = thresh | im_floodfill_inv
    result["hole_ratio"] = np.sum(holes > 0) / (h * w)

    # Color deviation
    mean_color = np.mean(img.reshape(-1, 3), axis=0)
    std_color = np.std(img.reshape(-1, 3), axis=0)
    result["mean_color_r"], result["mean_color_g"], result["mean_color_b"] = mean_color
    result["std_color_r"], result["std_color_g"], result["std_color_b"] = std_color

    return result


# =============================
# 📝 FEATURE TRANSLATION
# =============================
def generate_symptom_description(features: dict) -> str:
    desc = []
    if features["green_ratio"] < 0.5:
        desc.append("Leaf is losing green color.")
    if features["yellow_ratio"] > 0.15:
        desc.append("Yellow patches detected.")
    if features["brown_ratio"] > 0.05 or features["dark_spot_ratio"] > 0.1:
        desc.append("Brown/black necrotic spots visible.")
    if features["hole_ratio"] > 0.02:
        desc.append("Holes or tears detected (possible pest damage).")
    if features["texture_contrast"] > 100:
        desc.append("High texture contrast (possible fungal surface impact).")
    if features["edge_density"] > 0.1:
        desc.append("High edge density indicating structural damage.")

    desc.append(
        f"Leaf size: {features['width']}x{features['height']} px; "
        f"Mean color RGB: ({features['mean_color_r']:.1f}, {features['mean_color_g']:.1f}, {features['mean_color_b']:.1f})."
    )
    desc.append("Multi-crop diagnosis.")

    return "\n".join(desc)


# =============================
# 🤖 GEMINI DIAGNOSIS
# =============================
def ask_gemini(symptom_description, image_path):
    client = genai.Client(api_key=GEMINI_API_KEY)
    uploaded = client.files.upload(file=image_path)

    prompt = f"""
You are an expert plant pathologist.
Diagnose the crop disease based on image + extracted features.

Symptoms:
{symptom_description}

Respond with:
- Most likely diseases
- Biological cause (fungus/virus/bacteria/pest/nutrient)
- Treatment (organic + inorganic)
- Recommended fertilizer
- Prevention tips
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[uploaded, prompt],
    )

    return response.text


# =============================
# 🎨 STREAMLIT UI
# =============================
st.title("🌿 AI-Powered Leaf Disease Diagnosis")
st.write("Upload a leaf image to detect diseases using CV +  AI.")

uploaded_file = st.file_uploader("Upload Leaf Image", type=["png", "jpg", "jpeg"])

if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Leaf", use_column_width=True)

    # Save temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(uploaded_file.read())
        image_path = tmp.name

    st.info("✅ Image uploaded. Ready for analysis.")

    if st.button("🔍 Analyze Leaf"):
        with st.spinner("Extracting features..."):
            features = analyze_leaf_image(image_path)

        st.success("✅ Feature Extraction Completed")
        st.json(features)

        symptom_desc = generate_symptom_description(features)

        st.subheader("📝 Extracted Symptoms")
        st.text(symptom_desc)

        with st.spinner("🤖 Asking  for diagnosis..."):
            diagnosis = ask_gemini(symptom_desc, image_path)

        st.subheader("🌿 Diagnosis")
        st.write(diagnosis)

        os.unlink(image_path)
