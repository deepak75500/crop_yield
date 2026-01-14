import os
import cv2
import numpy as np
from skimage import feature
import sys
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
GEMINI_API_KEY = "AIzaSyA5DCaqLjR3S9n8dpwxfuMwdDhqxk_4qm8"  
genai.configure(api_key=GEMINI_API_KEY)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
def analyze_leaf_image(image_path: str) -> dict:
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Image not found: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, w = img.shape[:2]

    result = {}
    result['width'], result['height'] = w, h
    result['mean_intensity'] = np.mean(gray)
    result['std_intensity'] = np.std(gray)

    green_mask = (hsv[:, :, 0] > 35) & (hsv[:, :, 0] < 85)
    result['green_ratio'] = np.sum(green_mask) / (h * w)

    yellow_mask = (hsv[:, :, 0] > 20) & (hsv[:, :, 0] < 35)
    result['yellow_ratio'] = np.sum(yellow_mask) / (h * w)

    brown_mask = (hsv[:, :, 0] > 10) & (hsv[:, :, 0] < 25) & (hsv[:, :, 2] < 120)
    result['brown_ratio'] = np.sum(brown_mask) / (h * w)

    _, thresh = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)
    result['dark_spot_ratio'] = np.sum(thresh > 0) / (h * w)

    contours, _ = cv2.findContours(cv2.Canny(gray, 50, 150), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        perimeter = cv2.arcLength(largest, True)
        result['leaf_area'] = area
        result['leaf_perimeter'] = perimeter
        result['leaf_compactness'] = (4 * np.pi * area) / (perimeter ** 2 + 1e-6)
    else:
        result['leaf_area'] = result['leaf_perimeter'] = result['leaf_compactness'] = 0

    glcm = feature.graycomatrix(gray, [5], [0], 256, symmetric=True, normed=True)
    result['texture_contrast'] = feature.graycoprops(glcm, 'contrast')[0, 0]
    result['texture_dissimilarity'] = feature.graycoprops(glcm, 'dissimilarity')[0, 0]
    result['texture_homogeneity'] = feature.graycoprops(glcm, 'homogeneity')[0, 0]
    result['texture_energy'] = feature.graycoprops(glcm, 'energy')[0, 0]
    result['texture_correlation'] = feature.graycoprops(glcm, 'correlation')[0, 0]

    edges = cv2.Canny(gray, 100, 200)
    result['edge_density'] = np.sum(edges > 0) / (h * w)

    im_floodfill = thresh.copy()
    mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(im_floodfill, mask, (0, 0), 255)
    im_floodfill_inv = cv2.bitwise_not(im_floodfill)
    holes = thresh | im_floodfill_inv
    result['hole_ratio'] = np.sum(holes > 0) / (h * w)

    mean_color = np.mean(img.reshape(-1, 3), axis=0)
    std_color = np.std(img.reshape(-1, 3), axis=0)
    result['mean_color_r'], result['mean_color_g'], result['mean_color_b'] = mean_color
    result['std_color_r'], result['std_color_g'], result['std_color_b'] = std_color
    print(result)
    return result

# ========== 📝 FEATURE DESCRIPTION ==========
def generate_symptom_description(features: dict) -> str:
    desc = []
    if features['green_ratio'] < 0.5:
        desc.append("Leaf is losing green color indicating possible nutrient deficiency or disease.")
    if features['yellow_ratio'] > 0.15:
        desc.append("Yellow patches detected suggesting chlorosis or viral infection.")
    if features['brown_ratio'] > 0.05 or features['dark_spot_ratio'] > 0.1:
        desc.append("Brown or black necrotic spots are visible.")
    if features['hole_ratio'] > 0.02:
        desc.append("Visible holes or tears indicate pest damage.")
    if features['texture_contrast'] > 100:
        desc.append("High texture contrast indicating uneven leaf surface or fungal growth.")
    if features['edge_density'] > 0.1:
        desc.append("High edge density detected suggesting structural damage.")
    desc.append(f"Leaf size: {features['width']}x{features['height']} px")
    desc.append(f"Mean color RGB: ({features['mean_color_r']:.1f}, {features['mean_color_g']:.1f}, {features['mean_color_b']:.1f})")
    desc.append("This is a multi-crop diagnosis request.")
    return "\n".join(desc)

# ========== 🤖 GEMINI DIAGNOSIS ==========
def ask_gemini_for_diagnosis(symptom_description: str, image_path: str) -> str:
    prompt = f"""
You are an expert agricultural plant pathologist.
Based on the following leaf image and its analytical features, identify the disease and suggest treatment.

Symptom description:
{symptom_description}

Provide:
- Most probable diseases (consider multiple crops)
- Cause (fungal, viral, bacterial, pest, nutrient deficiency, etc.)
- Control measures and prevention methods
- Recommended organic and inorganic treatments/fertilizers
- Preventive measures for farmers
"""
    from google import genai

    client = genai.Client(api_key="AIzaSyCfwzy7_lUqmU93KfPLIX9CWQ7OBX3lLlE")
    print(image_path)
    my_file = client.files.upload(file=image_path)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[my_file, prompt],
    )
    print(response.text)
    return response.text

# ========== Flask Routes ==========
@app.route("/")
def index():
    return render_template("tamil.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    if "leaf_image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["leaf_image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(path)
    print(path)

    # Analyze image
    features = analyze_leaf_image(path)
    symptom_text = generate_symptom_description(features)
    diagnosis = ask_gemini_for_diagnosis(symptom_text, path)
    print(diagnosis)
    return jsonify({
        "features": features,
        "symptoms": symptom_text,
        "diagnosis": diagnosis
    })

if __name__ == "__main__":
    app.run(debug=True,port=5012)
