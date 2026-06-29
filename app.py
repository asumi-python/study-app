import os
import json
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": [], "results": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def build_prompt(subject, question_type):
    important_note = """
【重要ポイントの見つけ方】
- 赤字・赤マーカー・太字・下線・囲み線などで強調されている箇所
- 表や図の中の重要な用語・数値
- 繰り返し登場するキーワード
これらを中心に、画像1枚あたり5〜15問程度を目安に、内容の量に応じて問題数を自分で決めてください。
"""
    if subject == "国語（漢字）":
        if question_type == "読み":
            return f"""
あなたは国語の優秀な教師です。
画像に登場する漢字・熟語の中から、特に重要そうなものを選んで「読み問題」を作成してください。

{important_note}

【出力形式】
Q1.
問題文：「〇〇」の読み方を答えなさい。
答え：よみかた

【ルール】
- 答えはひらがなで
"""
        elif question_type == "書き":
            return f"""
あなたは国語の優秀な教師です。
画像に登場する漢字・熟語の中から、特に重要そうなものを選んで「書き問題」を作成してください。

{important_note}

【出力形式】
Q1.
問題文：「よみかた」を漢字で書きなさい。
答え：漢字

【ルール】
- 問題文はひらがな・カタカナで、答えは漢字で
"""
        else:
            return f"""
あなたは国語の優秀な教師です。
画像に登場する漢字・熟語の中から、特に重要そうなものを選んで「読み問題」と「書き問題」を交互に作成してください。

{important_note}

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
画像に登場する英単語の中から、特に重要そうなものを選んで問題を作成してください。
日本語を見て英単語を答える問題を作ってください。

{important_note}

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
画像に登場する英単語の中から、特に重要そうなものを選んで問題を作成してください。
英単語を見て日本語の意味を答える問題を作ってください。

{important_note}

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
画像に登場する英単語の中から、特に重要そうなものを選んで問題を作成してください。
日本語→英語と英語→日本語を交互に出してください。

{important_note}

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
この内容から穴埋め問題を作成してください。

{important_note}

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

def generate_questions(images, subject, question_type):
    prompt = build_prompt(subject, question_type)
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

@app.route("/users", methods=["GET"])
def get_users():
    data = load_data()
    return jsonify({"users": data["users"]})

@app.route("/users", methods=["POST"])
def add_user():
    name = request.json.get("name", "").strip()
    if not name:
        return jsonify({"error": "名前を入力してください"}), 400
    data = load_data()
    if name in data["users"]:
        return jsonify({"error": "同じ名前がすでにあります"}), 400
    data["users"].append(name)
    data["results"][name] = []
    save_data(data)
    return jsonify({"ok": True})

@app.route("/generate", methods=["POST"])
def generate():
    images_files = request.files.getlist("images")
    subject = request.form.get("subject", "社会")
    question_type = request.form.get("question_type", "")

    if not images_files:
        return jsonify({"error": "画像がありません"}), 400

    images = []
    for f in images_files:
        images.append((f.read(), f.mimetype))

    raw_text = generate_questions(images, subject, question_type)
    questions = parse_questions(raw_text)

    return jsonify({"questions": questions, "raw": raw_text})

@app.route("/save_result", methods=["POST"])
def save_result():
    body = request.json
    user = body.get("user")
    subject = body.get("subject")
    wrong_questions = body.get("wrong_questions", [])

    if not user:
        return jsonify({"error": "ユーザーが未選択です"}), 400

    data = load_data()
    if user not in data["results"]:
        data["results"][user] = []

    today = datetime.now().strftime("%Y-%m-%d")
    for q in wrong_questions:
        data["results"][user].append({
            "date": today,
            "subject": subject,
            "question": q["question"],
            "answer": q["answer"],
            "user_answer": q["user_answer"]
        })
    save_data(data)
    return jsonify({"ok": True})

@app.route("/review", methods=["GET"])
def review():
    user = request.args.get("user")
    if not user:
        return jsonify({"error": "ユーザーが未選択です"}), 400
    data = load_data()
    wrong = data["results"].get(user, [])
    seen = set()
    unique = []
    for q in wrong:
        key = q["question"]
        if key not in seen:
            seen.add(key)
            unique.append({"question": q["question"], "answer": q["answer"], "subject": q["subject"]})
    return jsonify({"questions": unique})

@app.route("/review_correct", methods=["POST"])
def review_correct():
    body = request.json
    user = body.get("user")
    mastered = body.get("mastered_questions", [])

    data = load_data()
    if user in data["results"]:
        data["results"][user] = [
            r for r in data["results"][user]
            if r["question"] not in mastered
        ]
    save_data(data)
    return jsonify({"ok": True})

@app.route("/feedback", methods=["POST"])
def feedback():
    body = request.json
    user = body.get("user")
    wrong_questions = body.get("wrong_questions", [])

    if not wrong_questions:
        return jsonify({"feedback": "間違いがありませんでした。素晴らしい！"})

    wrong_summary = "\n".join([
        f"・科目：{q['subject']}　問題：{q['question']}　正解：{q['answer']}"
        for q in wrong_questions
    ])

    prompt = f"""
あなたは優しくて頼りになる家庭教師です。
{user}さんが今回間違えた問題は以下の通りです。

{wrong_summary}

以下の3点を、中高生にわかりやすく、励ましながら伝えてください：
1. 間違いの傾向（どんなパターンで間違えているか）
2. 具体的な対策・勉強方法
3. 応援メッセージ

200文字以内で簡潔にまとめてください。
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt]
    )
    return jsonify({"feedback": response.text})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
