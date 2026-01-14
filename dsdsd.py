from flask import Flask, render_template, request
from google import genai
from google.genai.types import HttpOptions

# Initialize Gemini AI client
client = genai.Client(api_key="AIzaSyCfwzy7_lUqmU93KfPLIX9CWQ7OBX3lLlE")

app = Flask(__name__)

# --- Gemini AI Helper ---
def get_gemini_insights(prompt):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Error fetching insights: {e}"

# --- Smart suggestions logic ---
def smart_suggestions(crop_name, area_ha, fertilizer_kg, pesticide_kg, irrigation_efficiency=0.7, previous_crop=None):
    suggestions = []

    # Fertilizer optimization
    if fertilizer_kg > 150:
        suggestions.append(f"🌱 Consider reducing fertilizer for {crop_name} to lower cost and prevent soil nutrient overload.")
    else:
        suggestions.append(f"✅ Fertilizer usage for {crop_name} is within optimal range.")

    # Pesticide optimization
    if pesticide_kg > 50:
        suggestions.append(f"🛡 Reduce pesticide usage or use integrated pest management (IPM) for {crop_name}.")
    else:
        suggestions.append(f"✅ Pesticide usage is reasonable.")

    # Irrigation efficiency
    if irrigation_efficiency < 0.7:
        suggestions.append("💧 Improve irrigation efficiency: consider drip irrigation or scheduling to reduce water loss.")
    else:
        suggestions.append("✅ Irrigation efficiency is good.")

    # Crop rotation recommendations
    rotation_dict = {
        "Wheat": ["Legumes", "Barley", "Maize"],
        "Rice": ["Legumes", "Maize", "Vegetables"],
        "Tomato": ["Legumes", "Cucumber", "Brinjal"],
        "Potato": ["Legumes", "Corn", "Spinach"],
        "Maize": ["Legumes", "Soybean", "Sunflower"]
    }

    if previous_crop:
        if previous_crop in rotation_dict:
            if crop_name not in rotation_dict[previous_crop]:
                suggestions.append(f"🔄 Consider rotating {crop_name} after {previous_crop} to improve soil fertility.")
            else:
                suggestions.append(f"✅ Crop rotation after {previous_crop} is optimal.")
        else:
            suggestions.append(f"ℹ️ No specific rotation data for {previous_crop}. General crop rotation is advised.")

    # Gemini AI insights
    prompt = f"Provide cost optimization strategies for {crop_name} farming, including fertilizer reduction, irrigation scheduling, and crop rotation. it is derived verify it is clear {suggestions} give few key points like subtitlte and points in 25 lines give some examples get from online " 
    gemini_insights = get_gemini_insights(prompt)
    suggestions.append(f"💡 AI Insights: {gemini_insights}")

    return suggestions

# --- Flask routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    suggestions = []
    if request.method == "POST":
        crop_name = request.form.get("crop_name")
        area = float(request.form.get("area"))
        fertilizer = float(request.form.get("fertilizer"))
        pesticide = float(request.form.get("pesticide"))
        irrigation_efficiency = float(request.form.get("irrigation_efficiency"))
        previous_crop = request.form.get("previous_crop")

        suggestions = smart_suggestions(
            crop_name, area, fertilizer, pesticide, irrigation_efficiency, previous_crop
        )

    return render_template("rock.html", suggestions=suggestions)
# API endpoint for dynamic translation
from flask import Flask, render_template, request, jsonify
from google import genai
def get_translation(text, target_language):
    prompt = f"Translate the following text into {target_language}:\n{text}"
    response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
    return response.text.strip()

@app.route("/translate", methods=["POST"])
def translate():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        text_list = data.get("suggestions", [])
        language = data.get("language", "English")
        translated = []

        for t in text_list:
            try:
                translated_text = get_translation(t, language)
                translated.append(translated_text)
            except Exception as e:
                print(f"Translation failed for '{t}': {e}")
                translated.append(t)  # fallback to original

        return jsonify({"translated": translated})
    except Exception as e:
        print(f"Translate endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True,port=5005)
