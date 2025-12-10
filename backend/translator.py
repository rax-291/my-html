"""
نظام الترجمة باستخدام نماذج NLP (Transformers)
"""

from transformers import MarianMTModel, MarianTokenizer
import torch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================================
# اختيار النموذج الأفضل للإنجليزية-العربية
# ===============================================

MODEL_NAME = "Helsinki-NLP/opus-mt-en-ar"
# بدائل إذا ما اشتغل:
# MODEL_NAME = "facebook/nllb-200-distilled-600M"  # أقوى لكن أبطأ
# MODEL_NAME = "Helsinki-NLP/opus-mt-tc-big-en-ar" # أكبر وأدق

logger.info(f"📥 تحميل نموذج الترجمة: {MODEL_NAME}")

try:
    tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME)
    model = MarianMTModel.from_pretrained(MODEL_NAME)
    
    # استخدام GPU إذا متوفر
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    
    logger.info(f"✅ تم تحميل النموذج بنجاح على {device}")
except Exception as e:
    logger.error(f"❌ فشل تحميل النموذج: {e}")
    raise


# ===============================================
# دالة الترجمة الأساسية
# ===============================================

def translate_single_text(text, use_two_stage=False, max_length=512):
    """
    ترجمة نص واحد من الإنجليزية إلى العربية
    
    Args:
        text (str): النص الإنجليزي
        use_two_stage (bool): استخدام ترجمة مرحلتين (تجريبي)
        max_length (int): الحد الأقصى لطول النص
    
    Returns:
        str: النص المترجم للعربية
    """
    try:
        if not text or not text.strip():
            return ""
        
        # تنظيف النص
        text = text.strip()
        
        # Tokenization
        inputs = tokenizer(
            text, 
            return_tensors="pt", 
            padding=True, 
            truncation=True, 
            max_length=max_length
        )
        
        # نقل للجهاز المناسب
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # الترجمة
        with torch.no_grad():
            translated = model.generate(
                **inputs,
                max_length=max_length,
                num_beams=5,           # للحصول على ترجمة أفضل
                early_stopping=True,
                no_repeat_ngram_size=3 # تجنب التكرار
            )
        
        # فك الترميز
        translation = tokenizer.decode(
            translated[0], 
            skip_special_tokens=True
        )
        
        # تنظيف الترجمة
        translation = translation.strip()
        
        # ترجمة مرحلتين (اختياري)
        if use_two_stage:
            translation = improve_translation(translation)
        
        return translation
    
    except Exception as e:
        logger.error(f"❌ خطأ في ترجمة النص: {e}")
        return f"[خطأ في الترجمة: {str(e)}]"


# ===============================================
# ترجمة محسّنة (مرحلتين)
# ===============================================

def improve_translation(text):
    """
    تحسين الترجمة عن طريق إعادة صياغة
    (تجريبي - قد لا يعطي نتائج أفضل دائماً)
    """
    try:
        # يمكن استخدام نموذج paraphrase هنا
        # حالياً نرجع النص كما هو
        return text
    except:
        return text


# ===============================================
# ترجمة نصوص متعددة (Batch)
# ===============================================

def translate_texts(texts, use_two_stage=False, batch_size=5):
    """
    ترجمة قائمة من النصوص مع معالجة دفعية
    
    Args:
        texts (list): قائمة النصوص الإنجليزية
        use_two_stage (bool): استخدام ترجمة محسّنة
        batch_size (int): عدد النصوص في كل دفعة
    
    Returns:
        list: قائمة النصوص المترجمة
    """
    translated_texts = []
    total = len(texts)
    
    logger.info(f"🔄 بدء ترجمة {total} نص...")
    
    for i in range(0, total, batch_size):
        batch = texts[i:i+batch_size]
        
        for j, text in enumerate(batch):
            current = i + j + 1
            logger.info(f"📝 ترجمة النص {current}/{total}")
            
            translation = translate_single_text(text, use_two_stage)
            translated_texts.append(translation)
    
    logger.info(f"✅ اكتملت الترجمة!")
    return translated_texts


# ===============================================
# ترجمة مرحلتين (للتوافق)
# ===============================================

def two_stage_translation(text):
    """
    للتوافق مع الكود القديم
    """
    return translate_single_text(text, use_two_stage=True)


# ===============================================
# اختبار النموذج
# ===============================================

if __name__ == "__main__":
    # اختبار بسيط
    test_text = "I wish I could hug you on my left shoulder"
    
    print(f"📥 النص الأصلي: {test_text}")
    print(f"🔄 جاري الترجمة...")
    
    translation = translate_single_text(test_text)
    
    print(f"📤 الترجمة: {translation}")