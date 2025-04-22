from flask import Flask, request, jsonify
import pytesseract
from PIL import Image
import base64
import io
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    indicaciones = "No se envió orden médica."
    
    if "orden_medica" in data:
        image_data = base64.b64decode(data["orden_medica"])
        image = Image.open(io.BytesIO(image_data))
        texto_ocr = pytesseract.image_to_string(image)

        prompt = f"Extrae los estudios de esta orden y da indicaciones:
{texto_ocr}"
        respuesta = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        indicaciones = respuesta["choices"][0]["message"]["content"]

    domicilio = data.get("domicilio", "").strip()
    if not domicilio:
        return jsonify({"status": "error", "message": "Falta ingresar domicilio"})

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json = base64.b64decode(os.getenv("GOOGLE_CREDENTIALS_BASE64")).decode()
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
    client = gspread.authorize(creds)
    sheet = client.open(os.getenv("SPREADSHEET_NAME")).sheet1

    nombre = data.get("nombre", "Sin nombre")
    telefono = data.get("telefono", "Sin teléfono")
    sheet.append_row([nombre, telefono, domicilio, indicaciones])

    return jsonify({"status": "success", "mensaje": f"Turno registrado. Indicaciones: {indicaciones}"})

if __name__ == "__main__":
    app.run()