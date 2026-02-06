from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route("/")
def hello():
    return "converter alive"

@app.route("/convert", methods=["POST"])
def convert():
    file = request.files["file"]
    input_path = "/tmp/input.xlsx"
    file.save(input_path)

    # converter実行
    subprocess.run(["python", "converter_v10.py", input_path], check=True)

    # 生成されたJSONを読む
    with open("output.json", "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "application/json"}
