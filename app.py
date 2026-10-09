import os
import io
import time

from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors
from PIL import Image, UnidentifiedImageError



load_dotenv()

app = Flask(
    __name__,
    static_folder="public",
    static_url_path=""
)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp"
}

MODEL_NAME = "gemini-3.8-flash"

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. "
        "Please add it to your .env file."
    )

client = genai.Client(api_key=api_key)



@app.route("/", methods=["GET"])
def home():
    return send_from_directory("public", "index.html")



@app.route("/api/classify", methods=["POST"])
def classify_image():

    if "image" not in request.files:
        return jsonify({
            "error": "Please upload an image."
        }), 400

    file = request.files["image"]

    if not file or not file.filename:
        return jsonify({
            "error": "Please select an image first."
        }), 400

    if file.mimetype not in ALLOWED_TYPES:
        return jsonify({
            "error": "Only JPG, PNG, and WEBP images are allowed."
        }), 400

    try:
        image_bytes = file.read()

        if not image_bytes:
            return jsonify({
                "error": "The uploaded file is empty."
            }), 400

        image = Image.open(io.BytesIO(image_bytes))
        image.verify()

        image = Image.open(io.BytesIO(image_bytes))

        if image.width * image.height > 25_000_000:
            return jsonify({
                "error": "Image dimensions are too large."
            }), 400

        image.load()

        image = image.convert("RGB")

        image_buffer = io.BytesIO()
        image.save(
            image_buffer,
            format="JPEG",
            quality=85
        )

        jpeg_bytes = image_buffer.getvalue()

        prompt = """
                   Analyze the uploaded image and provide a complete answer.

                   Follow this exact format:

                   1. Main subject:
                   Describe the main object, animal, person, or scene in 2-3 sentences.

                   2. Important visible features:
                   List at least 3 visible features, if identifiable.

                   3. Other notable details:
                   Describe the background, surroundings, colors, or other visible objects.

                   4. Summary:
                   Give a short, clear summary of the image.

                   IMPORTANT:
                   - Complete all four sections.
                   - Do not stop after the first heading.
                   - Use simple English.
                   - If a detail is unclear, say "Not clearly identifiable."
                """


        response = None

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=jpeg_bytes,
                            mime_type="image/jpeg"
                        )
                    ],
                    config=types.GenerateContentConfig(
                        max_output_tokens=500,
                        temperature=0.2
                    )
                )

                break

            except errors.APIError as error:

                status_code = getattr(
                    error,
                    "code",
                    None
                )

                retryable = status_code in (429, 500, 502, 503, 504)

                if retryable and attempt < 2:
                    wait_seconds = 2 ** (attempt + 1)

                    app.logger.warning(
                        "Gemini API returned %s. "
                        "Retry %s/2 in %s seconds.",
                        status_code,
                        attempt + 1,
                        wait_seconds
                    )

                    time.sleep(wait_seconds)

                else:
                    raise

        result = response.text if response else None

        if not result:
            return jsonify({
                "error": (
                    "The AI returned an empty response. "
                    "Please try again."
                )
            }), 502

        return jsonify({
            "result": result
        }), 200

    except UnidentifiedImageError:
        return jsonify({
            "error": "The uploaded file is not a valid image."
        }), 400

    except errors.APIError as error:
        app.logger.exception("Gemini API request failed")

        status_code = getattr(error, "code", None)

        if status_code == 429:
            message = (
                "Gemini API request limit reached. "
                "Please wait and try again."
            )
        elif status_code == 503:
            message = (
                "Gemini is temporarily busy. "
                "Please try again in a little while."
            )
        elif status_code in (401, 403):
            message = (
                "Gemini API authentication failed. "
                "Check your API key and API access."
            )
        elif status_code == 404:
            message = (
                "The Gemini model is unavailable for your API key. "
                "Check the available model names in Google AI Studio."
            )
        else:
            message = (
                "Gemini could not analyze the image. "
                "Check the server terminal for details."
            )

        return jsonify({
            "error": message
        }), 502

    except Exception:
        app.logger.exception("Image classification failed")

        return jsonify({
            "error": (
                "Image analysis failed. "
                "Check your internet connection and server terminal."
            )
        }), 500




@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "error": "Image is too large. Maximum size is 10 MB."
    }), 413




if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
