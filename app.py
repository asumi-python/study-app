import os
import base64
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def generate_questions(image_bytes, mime_type, subject, count):
    prompt = f"""
あなたは{subject}の優秀な教師です。
この画像は高校生の{subject}のワークやノートです。

この内容から穴埋め問題を{count}問作成してください。

【出力形式】必ず以下の形式で出力してください。各問題を同じ形式で繰り返してください。

Q1.
問題文：〇〇は＿＿＿＿である。
答え：〇〇

Q2.
問題文：〇〇は＿＿＿＿である。
答え：〇〇

【ルール】
- 穴埋め部分は「＿＿＿＿」で表す
- 重要な用語・人物名・年号・数値などを穴埋めにする
- 問題文は自然な日本語で
- 答えは簡潔に
"""
    image_part = {
        "inline_data": {
            "mime_type": mime_type,
            "data": base64.b64encode(image_bytes).decode("utf-8")
        }
    }
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, image_part]
    )
    return response.text

def parse_questions(text):
    questions = []
    blocks = text.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        question_line = ""
        answer_line = ""
        for line in lines:
            if "問題文：" in line:
                question_line = line.replace("問題文：", "").strip()
            elif "答え：" in line:
                answer_line = line.replace("答え：", "").strip()
        if question_line and answer_line:
            questions.append({"question": question_line, "answer": answer_line})
    return questions

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    image = request.files.get("image")
    subject = request.form.get("subject", "社会")
    count = request.form.get("count", "5")

    if not image:
        return jsonify({"error": "画像がありません"}), 400

    image_bytes = image.read()
    mime_type = image.mimetype

    raw_text = generate_questions(image_bytes, mime_type, subject, count)
    questions = parse_questions(raw_text)

    return jsonify({"questions": questions, "raw": raw_text})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
