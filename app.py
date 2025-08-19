import streamlit as st
import requests
import base64
import json
import os
from PIL import Image
import io
import streamlit as st
import streamlit.components.v1 as components

# --- Google Analytics tracking (place this near the top of your file) ---
ga_js = """
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-MT8S1SFPLB"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-MT8S1SFPLB');
</script>
"""
components.html(ga_js, height=0)

# --- Your normal Streamlit app below ---
st.title("My Streamlit App")
st.write("Google Analytics tracking has been added.")


# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Function to encode image to base64
def encode_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# Function to call OpenRouter API for image analysis
def analyze_image(image_base64, location, electricity_rate):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    Analyze the provided satellite image of a rooftop for solar panel installation potential.
    Provide the following in JSON format:
    {{
        "roof_area_sqm": float,
        "azimuth_degrees": float,
        "tilt_degrees": float,
        "shading_percentage": float,
        "suggested_panel_type": string,
        "estimated_annual_kwh": float
    }}

    Location: {location}
    Electricity rate: ${electricity_rate}/kWh
    """

    payload = {
        "model": "deepseek/deepseek-prover-v2:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ]
            }
        ],
        "response_format": "json"
    }

    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result_json = response.json()
        content = result_json["choices"][0]["message"]["content"]

        # Try to extract JSON from messy text
        try:
            # Extract valid JSON using regex or clean manually
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            json_text = content[json_start:json_end]
            return json.loads(json_text)
        except Exception as e:
            st.error("Failed to parse model's response as JSON.")
            st.text(content)
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse API JSON response: {str(e)}")
        return None

# ROI calculation
def calculate_roi(roof_area_sqm, estimated_annual_kwh, electricity_rate):
    panel_efficiency = 0.20
    cost_per_watt = 3.0
    incentive_rate = 0.30
    panel_watts_per_sqm = 200

    total_watts = roof_area_sqm * panel_watts_per_sqm
    installation_cost = total_watts * cost_per_watt
    incentive = installation_cost * incentive_rate
    net_cost = installation_cost - incentive
    annual_savings = estimated_annual_kwh * electricity_rate
    payback_period = net_cost / annual_savings if annual_savings > 0 else float("inf")

    return {
        "total_watts": total_watts,
        "installation_cost": installation_cost,
        "incentive": incentive,
        "net_cost": net_cost,
        "annual_savings": annual_savings,
        "payback_period_years": payback_period
    }

# Streamlit App
st.title("☀️ Solar Rooftop Analyzer")
st.write("Upload a satellite image of a rooftop to assess its solar panel installation potential and estimate return on investment (ROI).")

# User Inputs
uploaded_file = st.file_uploader("Choose a satellite image", type=["png", "jpg", "jpeg"])
location = st.text_input("📍 Location (City, State)", value="San Francisco, CA")
electricity_rate = st.number_input("💡 Electricity Rate ($/kWh)", min_value=0.0, value=0.15, step=0.01)

if uploaded_file and st.button("Analyze"):
    try:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Satellite Image", use_column_width=True)
        image_base64 = encode_image(image)
        analysis = analyze_image(image_base64, location, electricity_rate)

        if analysis:
            st.subheader("📊 Analysis Results")
            st.json(analysis)

            roi = calculate_roi(
                analysis["roof_area_sqm"],
                analysis["estimated_annual_kwh"],
                electricity_rate
            )

            st.subheader("💰 ROI Estimates")
            st.markdown(f"- **Total System Size**: {roi['total_watts']:.2f} W")
            st.markdown(f"- **Installation Cost**: ${roi['installation_cost']:.2f}")
            st.markdown(f"- **Incentive (30%)**: ${roi['incentive']:.2f}")
            st.markdown(f"- **Net Cost**: ${roi['net_cost']:.2f}")
            st.markdown(f"- **Estimated Annual Savings**: ${roi['annual_savings']:.2f}")
            st.markdown(f"- **Payback Period**: {roi['payback_period_years']:.2f} years")

            st.subheader("✅ Recommendations")
            st.write(f"**Suggested Panel Type**: {analysis['suggested_panel_type']}")
            st.write("Ensure compliance with local building codes and net metering policies.")
        else:
            st.error("Image analysis failed. Please try again.")

    except Exception as e:
        st.error(f"Unexpected error: {e}")

# Instructions
st.subheader("📘 How to Use")
st.markdown("""
1. Upload a **clear satellite image** of your rooftop (PNG, JPG).
2. Enter your **location** (city and state) for better solar irradiance estimation.
3. Input your **electricity rate** ($/kWh).
4. Click **Analyze** to get a detailed solar potential and ROI estimate.
""")

