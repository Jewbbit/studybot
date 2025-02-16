import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS  # CORS 설정

# Flask 앱 생성
app = Flask(__name__)
CORS(app)  # 모든 도메인에서 API 접근 허용

# ✅ Google Gemini API 키 리스트
API_KEYS = [
    os.getenv("GOOGLE_GEMINI_API_KEY_1"),
    os.getenv("GOOGLE_GEMINI_API_KEY_2"),
    os.getenv("GOOGLE_GEMINI_API_KEY_3"),
    os.getenv("GOOGLE_GEMINI_API_KEY_4"),
    os.getenv("GOOGLE_GEMINI_API_KEY_5"),
    os.getenv("GOOGLE_GEMINI_API_KEY_6"),
    os.getenv("GOOGLE_GEMINI_API_KEY_7"),
    os.getenv("GOOGLE_GEMINI_API_KEY_8")
]
CURRENT_API_INDEX = 0  # API 키 순환 인덱스

# ✅ Notion API 설정
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

@app.route("/")
def home():
    return "Studybot API is running!"

@app.route('/api/explain_concept', methods=['POST'])
def explain_concept():
    global CURRENT_API_INDEX
    data = request.json
    concept = data.get("개념", "미지정")

    if not concept:
        return jsonify({"error": "개념이 입력되지 않았습니다."}), 400

    # ✅ AI API 호출 (Google Gemini 사용)
    ai_response = None
    for _ in range(len(API_KEYS)):  # API 키를 순환하며 사용
        api_key = API_KEYS[CURRENT_API_INDEX]
        if not api_key:
            CURRENT_API_INDEX = (CURRENT_API_INDEX + 1) % len(API_KEYS)
            continue

        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateText?key={api_key}",
                json={"prompt": f"'{concept}' 개념을 쉽게 설명해줘."}
            )
            ai_response = response.json().get("text", "AI 응답이 없습니다.")
            break  # 응답이 성공하면 반복문 종료
        except Exception as e:
            print(f"API 호출 실패: {e}")
            CURRENT_API_INDEX = (CURRENT_API_INDEX + 1) % len(API_KEYS)  # 다음 키 사용

    if not ai_response:
        return jsonify({"error": "AI 응답을 가져오지 못했습니다."}), 500

    # ✅ Notion에 저장
    notion_success = save_to_notion(concept, ai_response)

    return jsonify({
        "개념": concept,
        "설명": ai_response,
        "Notion 저장": "성공" if notion_success else "실패"
    })

@app.route('/save_study', methods=['POST'])
def save_study():
    try:
        data = request.json
        subject = data.get("과목", "알 수 없음")
        concept = data.get("개념", "알 수 없음")
        importance = data.get("중요도", 0)
        review_date = data.get("복습 날짜", None)
        memo = data.get("메모", "")

        notion_data = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "과목": {"title": [{"text": {"content": subject}}]},
                "개념": {"rich_text": [{"text": {"content": concept}}]},
                "중요도": {"number": importance},
                "메모": {"rich_text": [{"text": {"content": memo}}]}
            }
        }

        if review_date:
            notion_data["properties"]["복습 날짜"] = {"date": {"start": review_date}}

        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=HEADERS,
            json=notion_data
        )

        if response.status_code == 200:
            return jsonify({"message": "공부 기록 저장 성공!", "data": notion_data}), 200
        else:
            return jsonify({"error": "Notion 저장 실패", "details": response.json()}), response.status_code

    except Exception as e:
        return jsonify({"error": "서버 오류 발생", "details": str(e)}), 500

def save_to_notion(concept, explanation):
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        print("❌ Notion API 키 또는 데이터베이스 ID가 설정되지 않음")
        return False

    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "개념": {"title": [{"text": {"content": concept}}]},
            "설명": {"rich_text": [{"text": {"content": explanation}}]}
        }
    }

    response = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=data)
    return response.status_code == 200

if __name__ == "__main__":
    app.run(debug=True)
