import os
import requests
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Разрешаем запросы с вашего сайта

# ===== НАСТРОЙКИ TELEGRAM (берём из переменных окружения) =====
BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# Проверяем, что переменные установлены
if not BOT_TOKEN or not CHAT_ID:
    print("⚠️ ВНИМАНИЕ: TELEGRAM_TOKEN или CHAT_ID не установлены!")
    print("⚠️ Добавьте их в Environment Variables на Render")
# ===============================================================

def send_to_telegram(message):
    """Отправка сообщения в Telegram"""
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
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")
        return False, str(e)

@app.route('/')
def home():
    """Главная страница для проверки работоспособности"""
    return jsonify({
        'status': 'ok',
        'message': 'KANTON Bot is running!',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    """Проверка здоровья сервиса"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'telegram_configured': bool(BOT_TOKEN and CHAT_ID)
    })

@app.route('/send-project', methods=['POST'])
def send_project():
    """Обработчик заявок с сайта"""
    try:
        # Получаем данные из запроса
        data = request.get_json()
        
        # Если данные пришли как form-data, а не JSON
        if not data:
            data = request.form.to_dict()
        
        # Извлекаем поля
        name = data.get('name', '').strip()
        contact = data.get('contact', '').strip()
        objtype = data.get('objtype', 'Не указан')
        link = data.get('link', '').strip()
        comment = data.get('comment', '').strip()
        
        # Валидация
        if not name or not contact:
            return jsonify({
                'success': False,
                'error': 'Пожалуйста, заполните имя и контактные данные'
            }), 400
        
        # Формируем красивое сообщение
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
        
        # Отправляем в Telegram
        success, result = send_to_telegram(message)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Заявка успешно отправлена в Telegram'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Ошибка отправки в Telegram. Попробуйте позже.'
            }), 500
            
    except Exception as e:
        print(f"❌ Ошибка обработки запроса: {e}")
        return jsonify({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }), 500

if __name__ == '__main__':
    # Для локальной разработки
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)