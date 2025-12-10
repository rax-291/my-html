"""
Flask API - الآنسة فصيحة
يستقبل الملفات والنصوص ويترجمها ويرجعها
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import logging
from datetime import datetime

# استيراد المعالجات والمترجم
from file_handlers.txt_handler import extract_text_from_txt, create_txt
from file_handlers.pdf_handler import extract_text_from_pdf, create_pdf
from file_handlers.docx_handler import extract_text_from_docx, create_docx
from file_handlers.epub_handler import extract_text_from_epub, create_epub
from translator import translate_texts, translate_single_text

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إنشاء التطبيق
app = Flask(__name__)
CORS(app)  # للسماح بالـ Frontend يتصل

# إنشاء المجلدات المطلوبة
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# الملفات المدعومة
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'epub'}


def allowed_file(filename):
    """
    التحقق من نوع الملف
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename):
    """
    استخراج امتداد الملف
    """
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def cleanup_old_files():
    """
    حذف الملفات القديمة (أكثر من ساعة)
    """
    try:
        import time
        current_time = time.time()
        
        for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    # إذا الملف أقدم من ساعة
                    if current_time - os.path.getmtime(filepath) > 3600:
                        os.remove(filepath)
                        logger.info(f"🗑️  حذف ملف قديم: {filename}")
    except Exception as e:
        logger.warning(f"⚠️  تعذر حذف الملفات القديمة: {e}")


# ========================================
# Route 1: الصفحة الرئيسية (اختبار)
# ========================================

@app.route('/', methods=['GET'])
def home():
    """
    صفحة رئيسية للاختبار
    """
    return jsonify({
        'status': 'ok',
        'message': 'مرحباً بك في API الآنسة فصيحة',
        'version': '1.0',
        'endpoints': {
            '/api/health': 'التحقق من حالة الخادم',
            '/api/translate-text': 'ترجمة نص مباشر',
            '/api/translate-file': 'ترجمة ملف'
        }
    })


# ========================================
# Route 2: فحص الصحة
# ========================================

@app.route('/api/health', methods=['GET'])
def health():
    """
    التحقق من أن الخادم يعمل
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


# ========================================
# Route 3: ترجمة نص مباشر
# ========================================

@app.route('/api/translate-text', methods=['POST'])
def translate_text_endpoint():
    """
    ترجمة نص إنجليزي إلى عربي
    
    Body (JSON):
    {
        "text": "النص الإنجليزي",
        "use_two_stage": true  (اختياري - افتراضي true)
    }
    
    Response:
    {
        "translation": "النص العربي",
        "success": true
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'الرجاء إرسال نص في حقل "text"'
            }), 400
        
        text = data['text']
        use_two_stage = data.get('use_two_stage', True)
        
        if not text.strip():
            return jsonify({
                'success': False,
                'error': 'النص فارغ'
            }), 400
        
        logger.info(f"📝 ترجمة نص: {text[:50]}...")
        
        # الترجمة
        translation = translate_single_text(text, use_two_stage=use_two_stage)
        
        return jsonify({
            'success': True,
            'translation': translation
        })
    
    except Exception as e:
        logger.error(f"❌ خطأ في ترجمة النص: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========================================
# Route 4: ترجمة ملف
# ========================================

@app.route('/api/translate-file', methods=['POST'])
def translate_file_endpoint():
    """
    ترجمة ملف كامل
    
    Form Data:
    - file: الملف (PDF/DOCX/TXT/EPUB)
    - use_two_stage: true/false (اختياري)
    
    Response:
    الملف المترجم للتحميل مباشرة
    """
    try:
        # حذف الملفات القديمة
        cleanup_old_files()
        
        # التحقق من وجود ملف
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'لم يتم إرسال ملف'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'لم يتم اختيار ملف'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'نوع الملف غير مدعوم. المدعوم: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # الحصول على إعدادات الترجمة
        use_two_stage = request.form.get('use_two_stage', 'true').lower() == 'true'
        
        # حفظ الملف المرفوع
        original_filename = file.filename
        file_ext = get_file_extension(original_filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        upload_filename = f"upload_{timestamp}.{file_ext}"
        upload_path = os.path.join(UPLOAD_FOLDER, upload_filename)
        file.save(upload_path)
        
        logger.info(f"📁 تم رفع الملف: {original_filename}")
        logger.info(f"📊 نوع الملف: {file_ext.upper()}")
        
        # ========================================
        # استخراج النص حسب نوع الملف
        # ========================================
        
        logger.info("📖 استخراج النص...")
        
        if file_ext == 'txt':
            texts = extract_text_from_txt(upload_path)
        elif file_ext == 'pdf':
            texts = extract_text_from_pdf(upload_path)
        elif file_ext in ['docx', 'doc']:
            texts = extract_text_from_docx(upload_path)
        elif file_ext == 'epub':
            texts = extract_text_from_epub(upload_path)
        else:
            raise Exception(f"نوع الملف غير مدعوم: {file_ext}")
        
        logger.info(f"✅ تم استخراج {len(texts)} جزء من النص")
        
        # ========================================
        # الترجمة
        # ========================================
        
        logger.info("🔄 جاري الترجمة...")
        
        translated_texts = translate_texts(
            texts,
            use_two_stage=use_two_stage,
            batch_size=5
        )
        
        logger.info("✅ اكتملت الترجمة!")
        
        # ========================================
        # إعادة بناء الملف
        # ========================================
        
        logger.info("📝 إنشاء الملف المترجم...")
        
        output_filename = f"translated_{timestamp}.{file_ext}"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        if file_ext == 'txt':
            create_txt(translated_texts, output_path)
        elif file_ext == 'pdf':
            create_pdf(translated_texts, output_path)
        elif file_ext in ['docx', 'doc']:
            create_docx(translated_texts, output_path)
        elif file_ext == 'epub':
            # استخراج العنوان من اسم الملف
            title = original_filename.replace(f'.{file_ext}', '')
            create_epub(translated_texts, output_path, title=f"{title} (مترجم)")
        
        logger.info(f"✅ تم إنشاء الملف: {output_filename}")
        
        # حذف الملف المرفوع
        try:
            os.remove(upload_path)
        except:
            pass
        
        # إرجاع الملف المترجم
        download_name = original_filename.replace(f'.{file_ext}', f'_translated.{file_ext}')
        
        return send_file(
            output_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/octet-stream'
        )
    
    except Exception as e:
        logger.error(f"❌ خطأ في ترجمة الملف: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========================================
# تشغيل الخادم
# ========================================

if __name__ == '__main__':
    logger.info("="*70)
    logger.info("🚀 تشغيل خادم الآنسة فصيحة")
    logger.info("="*70)
    logger.info("📍 العنوان: http://localhost:5000")
    logger.info("🌐 API جاهز لاستقبال الطلبات")
    logger.info("="*70)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )

    