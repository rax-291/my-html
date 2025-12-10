from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import re
import difflib
import os

from .gemini_chat import ask_gemini

# =========================
# إنشاء التطبيق + CORS
# =========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # فقط للتجربة المحلية، ممكن تضيقينه لاحقًا
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# تحميل ملف الـ FAQ
# =========================

FAQ_DATA = []

faq_path = os.path.join(os.path.dirname(__file__), "faq.json")

try:
    with open(faq_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # إذا كان شكل الملف:
    # { "faq": [ { "question": "...", "answer": "..." }, ... ] }
    if isinstance(raw, dict) and "faq" in raw:
        FAQ_DATA = raw["faq"]
    # أو إذا كان مباشرة قائمة:
    # [ { "question": "...", "answer": "..." }, ... ]
    elif isinstance(raw, list):
        FAQ_DATA = raw
    else:
        FAQ_DATA = []

except Exception as e:
    print("⚠️ لم أتمكن من تحميل faq.json:", e)
    FAQ_DATA = []


class ChatRequest(BaseModel):
    message: str
    tone: Optional[str] = None  # نبرة اختيارية (ممكن تكون None)



# =========================
# دالة البحث في الأسئلة الشائعة
# =========================
# دوال مساعدة لتحليل النص

STOP_WORDS = [
    "كيف", "سوي", "وش", "ايش", "ابي", "ابغى", "عندي", "لو", "هل", "اقدر", 
    "طريقة", "الطريقة", "ابي", "طلب", "سؤال", "ارجو", "ممكن"
]

def normalize(text: str) -> str:
    """تطبيع قوي للنص العربي."""
    if not text:
        return ""

    text = text.lower()

    # إزالة الرموز
    text = re.sub(r"[^\w\s]", " ", text)

    # توحيد الحروف
    replacements = {
        "أ": "ا", "إ": "ا", "آ": "ا",
        "ة": "ه", "ى": "ي",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    # إزالة المسافات الزائدة
    text = re.sub(r"\s+", " ", text).strip()

    return text


def remove_stop_words(text: str) -> str:
    """يحذف الكلمات العامة اللي ما تساعد في المطابقة."""
    words = text.split()
    filtered = [w for w in words if w not in STOP_WORDS]
    return " ".join(filtered)


def find_answer(user_input: str):
    """يبحث عن أقرب جواب FAQ بتحليل قوي ومعالجة ذكية للنص."""

    if not FAQ_DATA:
        return None

    # 1) تطبيع سؤال المستخدم
    user_norm = normalize(user_input)
    user_clean = remove_stop_words(user_norm)

    # لو ما بقى كلمات مفيدة
    if not user_clean:
        user_clean = user_norm

    best_match = None
    best_score = 0.0

    # 2) قارن مع الأسئلة
    for item in FAQ_DATA:
        q = item.get("q") or item.get("question")
        a = item.get("a") or item.get("answer")
        if not q:
            continue

        q_norm = normalize(q)
        q_clean = remove_stop_words(q_norm)

        # 3) استخدم difflib
        score = difflib.SequenceMatcher(None, user_clean, q_clean).ratio()

        # 4) إذا شيء قوي (أفضل من 0.45)
        if score > best_score:
            best_score = score
            best_match = a

    # لو التشابه ضعيف جدًا → نرجع None → يخلي Gemini يجاوب
    if best_score < 0.45:
        return None

    return best_match

# =========================
# Endpoint الشات
# =========================
@app.post("/api/chat")
async def chat_endpoint(data: ChatRequest):
    user_message = data.message.strip()
    user_tone = data.tone  # ممكن تكون None

    # 1) جرّب FAQ أول
    answer = find_answer(user_message)
    if answer:
        return {"source": "faq", "reply": answer}

    # 2) لو ما فيه جواب، نروح لـ Gemini ونمرر النبرة
    ai_reply = ask_gemini(user_message, tone=user_tone)
    return {"source": "gemini", "reply": ai_reply}



# Endpoint بسيط للاختبار
@app.get("/")
def root():
    return {"message": "✅ Chatbot API تعمل بنجاح باستخدام Gemini AI!"}
