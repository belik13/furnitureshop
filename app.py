import os
import requests
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Переменные окружения
BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    logger.error("❌ TELEGRAM_TOKEN или CHAT_ID не установлены!")
else:
    logger.info("✅ Telegram настроен")

def send_to_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
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
        return True, response.json()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False, str(e)

@app.route('/')
def home():
    """Главная страница"""
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'telegram_configured': bool(BOT_TOKEN and CHAT_ID)
    })

@app.route('/send-project', methods=['POST'])
def send_project():
    try:
        data = request.get_json()
        if not data:
            data = request.form.to_dict()
        
        name = data.get('name', '').strip()
        contact = data.get('contact', '').strip()
        
        if not name or not contact:
            return jsonify({
                'success': False,
                'error': 'Заполните имя и контакты'
            }), 400
        
        # Формируем сообщение
        current_time = datetime.now().strftime('%d.%m.%Y, %H:%M:%S')
        message = f"""
🏢 *НОВАЯ ЗАЯВКА*

👤 *Имя:* {name}
📱 *Контакты:* {contact}
🏗 *Объект:* {data.get('objtype', 'Не указан')}
🔗 *Ссылка:* {data.get('link', 'Не указана')}
💬 *Комментарий:* {data.get('comment', 'Не указан')}
📅 *Дата:* {current_time}
        """
        
        success, _ = send_to_telegram(message)
        
        if success:
            return jsonify({'success': True, 'message': 'Отправлено'}), 200
        else:
            return jsonify({'success': False, 'error': 'Ошибка'}), 500
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)