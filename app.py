from flask import Flask, request, jsonify
from google.cloud import storage
import os
import subprocess

app = Flask(__name__)

BUCKET_NAME = "nekobi-data-bucket"
OUTPUT_FILE = "neko_data.json"


@app.route("/", methods=["GET"])
def health():
    return "converter alive"


@app.route("/convert", methods=["POST"])
def convert():
    try:
        if "file" not in request.files:
            return jsonify({"error": "no file"}), 400

        file = request.files["file"]
        filepath = "/tmp/input.xlsx"
        file.save(filepath)

        # converter実行
        result = subprocess.run(
            ["python", "converter_v10.py", filepath],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return jsonify({"error": result.stderr}), 500

        # Cloud Storageへ保存
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(OUTPUT_FILE)
        blob.upload_from_filename("/tmp/neko_data.json")

        return jsonify({"status": "ok"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
