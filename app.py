from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health():
    return "converter alive"

@app.route("/run", methods=["POST"])
def run_converter():
    try:
        result = subprocess.run(
            ["python", "converter_v10.py"],
            capture_output=True,
            text=True
        )

        return jsonify({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
