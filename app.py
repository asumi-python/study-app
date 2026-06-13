import os
import base64
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def build_prompt(subject, question_type, count):
    if subject == "国語（漢字）":
        if question_type == "読み":
            return f"""
あなたは国語の優秀な教師です。
画像から漢字の「読み問題」を{count}問作成してください。

【出力形式】
Q1.
問題文：「〇〇」の読み方を答えなさい。
答え：よみかた

【ルール】
- 画像に登場する漢字・熟語から出題する
- 答えはひらがなで
"""
        elif question_type == "書き":
            return f"""
あなたは国語の優秀な教師です。
画像から漢字の「書き問題」を{count}問作成してください。

【出力形式】
Q1.
問題文：「よみかた」を漢字で書きなさい。
答え：漢字

【ルール】
- 画像に登場する漢字・熟語から出題する
- 問題文はひらがな・カタカナで、答えは漢字で
"""
        else:
            return f"""
あなたは国語の優秀な教師です。
画像から漢字の「読み問題」と「書き問題」を合わせて{count}問作成してください。
読み問題と書き問題を交互に出してください。

【出力形式】
Q1.
問題文：「〇〇」の読み方を答えなさい。
答え：よみかた

Q2.
問題文：「よみかた」を漢字で書きなさい。
答え：漢字

【ルール】
- 答えは読み問題はひらがな、書き問題は漢字で
"""
    elif subject == "英語（英単語）":
        if question_type == "日本語→英語":
            return f"""
あなたは英語の優秀な教師です。
画像から英単語の問題を{count}問作成してください。
日本語を見て英単語を答える問題を作ってください。

【出力形式】
Q1.
問題文：「日本語の意味」を英語で書きなさい。
答え：english

【ルール】
- 答えは英単語（小文字）で
"""
        elif question_type == "英語→日本語":
            return f"""
あなたは英語の優秀な教師です。
画像から英単語の問題を{count}問作成してください。
英単語を見て日本語の意味を答える問題を作ってください。

【出力形式】
Q1.
問題文：「english」の日本語の意味を答えなさい。
答え：日本語の意味

【ルール】
- 答えは日本語で簡潔に
"""
        else:
            return f"""
あなたは英語の優秀な教師です。
画像から英単語の問題を{count}問作成してください。
日本語→英語と英語→日本語を交互に出してください。

【出力形式】
Q1.
問題文：「日本語の意味」を英語で書きなさい。
答え：english

Q2.
問題文：「english」の日本語の意味を答えなさい。
答え：日本語の意味
"""
    else:
        return f"""
あなたは{subject}の優秀な教師です。
画像は高校生の{subject}のワークやノートです。
この内容から穴埋め問題を{count}問作成してください。

【出力形式】
Q1.
問題文：〇〇は＿＿＿＿である。
答え：〇〇

【ルール】
- 穴埋め部分は「＿＿＿＿」で表す
- 重要な用語・人物名・年号・数値などを穴埋めにする
- 問題文は自然な日本語で
- 答えは簡潔に
"""

def generate_questions(images, subject, question_type, count):
    prompt = build_prompt(subject, question_type, count)
    contents = [prompt]
    for image_bytes, mime_type in images:
        contents.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(image_bytes).decode("utf-8")
            }
        })
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents
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
    images_files = request.files.getlist("images")
    subject = request.form.get("subject", "社会")
    question_type = request.form.get("question_type", "")
    count = request.form.get("count", "10")

    if not images_files:
        return jsonify({"error": "画像がありません"}), 400

    images = []
    for f in images_files:
        images.append((f.read(), f.mimetype))

    raw_text = generate_questions(images, subject, question_type, count)
    questions = parse_questions(raw_text)

    return jsonify({"questions": questions, "raw": raw_text})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
