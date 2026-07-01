import os
import requests
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# ===== НАСТРОЙКА ЛОГГИРОВАНИЯ =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== ИНИЦИАЛИЗАЦИЯ FLASK =====
app = Flask(__name__)
CORS(app)  # Разрешаем запросы с вашего сайта

# ===== ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ =====
BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    logger.error("❌ TELEGRAM_TOKEN или CHAT_ID не установлены в переменных окружения!")
    logger.error("❌ Добавьте их в Environment Variables на Render")
else:
    logger.info("✅ Telegram настроен успешно")

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def send_to_telegram(message):
    """
    Отправка сообщения в Telegram
    
    Args:
        message (str): Текст сообщения с разметкой Markdown
        
    Returns:
        tuple: (success: bool, response_data: dict or str)
    """
    if not BOT_TOKEN or not CHAT_ID:
        logger.error("Telegram не настроен")
        return False, "Telegram не настроен"
    
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("✅ Сообщение успешно отправлено в Telegram")
        return True, response.json()
    except requests.exceptions.Timeout:
        logger.error("❌ Таймаут при отправке в Telegram")
        return False, "Таймаут соединения"
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Ошибка отправки в Telegram: {e}")
        return False, str(e)

def format_telegram_message(data):
    """
    Форматирует данные в красивое сообщение для Telegram
    
    Args:
        data (dict): Данные из формы
        
    Returns:
        str: Отформатированное сообщение
    """
    name = data.get('name', '').strip()
    contact = data.get('contact', '').strip()
    objtype = data.get('objtype', 'Не указан')
    link = data.get('link', '').strip()
    comment = data.get('comment', '').strip()
    current_time = datetime.now().strftime('%d.%m.%Y, %H:%M:%S')
    
    message = f"""
🏢 *НОВАЯ ЗАЯВКА С САЙТА KANTON*

👤 *Имя:* {name}
📱 *Контакты:* {contact}
🏗 *Тип объекта:* {objtype}

🔗 *Ссылка на проект:* {link if link else 'Не указана'}

💬 *Комментарий:* {comment if comment else 'Не указан'}

📅 *Дата:* {current_time}
    """
    return message

# ===== ЭНДПОЙНТЫ API =====

@app.route('/')
def home():
    """
    Корневой эндпоинт для проверки работоспособности
    """
    return jsonify({
        'status': 'ok',
        'service': 'KANTON Telegram Bot',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
        'telegram_configured': bool(BOT_TOKEN and CHAT_ID)
    })

@app.route('/health')
def health_check():
    """
    Эндпоинт для проверки здоровья сервиса (используется Render)
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'telegram_configured': bool(BOT_TOKEN and CHAT_ID),
        'bot_token_exists': bool(BOT_TOKEN),
        'chat_id_exists': bool(CHAT_ID)
    })

@app.route('/send-project', methods=['POST'])
def send_project():
    """
    Основной обработчик заявок с сайта
    Ожидает POST-запрос с JSON-данными:
    {
        "name": "Имя",
        "contact": "Контакт",
        "objtype": "Тип объекта",
        "link": "Ссылка",
        "comment": "Комментарий"
    }
    """
    try:
        # Логируем входящий запрос
        logger.info("📥 Получен запрос на /send-project")
        
        # Получаем данные из запроса
        data = request.get_json()
        
        # Если данные пришли как form-data (старый формат)
        if not data:
            data = request.form.to_dict()
            logger.info("Данные получены как form-data")
        else:
            logger.info("Данные получены как JSON")
        
        # Извлекаем поля
        name = data.get('name', '').strip()
        contact = data.get('contact', '').strip()
        
        # Валидация обязательных полей
        if not name or not contact:
            logger.warning("⚠️ Отсутствуют обязательные поля")
            return jsonify({
                'success': False,
                'error': 'Пожалуйста, заполните имя и контактные данные'
            }), 400
        
        # Форматируем сообщение
        message = format_telegram_message(data)
        
        # Отправляем в Telegram
        success, result = send_to_telegram(message)
        
        if success:
            logger.info(f"✅ Заявка от {name} успешно отправлена")
            return jsonify({
                'success': True,
                'message': 'Заявка успешно отправлена'
            }), 200
        else:
            logger.error(f"❌ Ошибка отправки в Telegram: {result}")
            return jsonify({
                'success': False,
                'error': 'Ошибка отправки. Пожалуйста, попробуйте позже.'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Обработчик 404 ошибок"""
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'Доступные эндпоинты: /, /health, /send-project'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработчик 500 ошибок"""
    logger.error(f"❌ Внутренняя ошибка сервера: {error}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'Произошла ошибка на сервере'
    }), 500

# ===== ТОЧКА ВХОДА ДЛЯ PRODUCTION =====
if __name__ == '__main__':
    # Этот блок не используется на Render (там используется Gunicorn),
    # но оставлен для локального тестирования
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)