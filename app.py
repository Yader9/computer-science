"""
This module provides an endpoint for a Chatbot service to answer PCB-related questions.
"""

# Import necessary libraries
import logging
import os
from datetime import datetime, timedelta
from threading import Thread
from queue import Queue, Empty
from flask import Flask, request, jsonify, session, render_template
import openai
from flask_session import Session

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = True
Session(app)

# Global variables
user_context = {}
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Cola para manejar solicitudes asincrónicas
request_queue = Queue()

def detect_language(message):
    """Detect the language of a given message."""
    spanish_keywords = ['hola', 'buenas', 'ayuda', 'día', 'gracias', 'por favor']
    return 'spanish' if any(word in message.lower() for word in spanish_keywords) else 'english'

def get_quick_replies(language):
    """Generate quick replies based on the user's language preference."""
    if language == 'spanish':
        return ['¿Qué es un PCB?', 'Cuéntame sobre electrónica', '¿Cómo se hacen los PCBs?']
    else:
        return ['What is a PCB?', 'Tell me about electronics', 'How are PCBs made?']

def process_request(data, response_queue):
    """Procesa la solicitud en un hilo separado."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": data['message']}
            ],
            max_tokens=150,
            temperature=0.5
        )
        reply = response.choices[0].get('message', {}).get('content').strip()
    except Exception as e:
        reply = f"Error: {str(e)}"
        logging.error("Error processing request: %s", str(e))

    response_queue.put(reply)


@app.route('/')
def index():
    """Renders the chatbot interface."""
    return render_template('chatbot_interface.html')

@app.route('/chatbot', methods=['POST'])
def chatbot():
    """Endpoint to communicate with the chatbot and get a response."""
    data = request.get_json()
    message = data['message']

    # Check session for user_id
    if 'user_id' not in session:
        session['user_id'] = os.urandom(24).hex()
    user_id = session['user_id']

    # Check if the user has a context. If not, create one.
    if user_id not in user_context:
        language = detect_language(message)
        user_context[user_id] = {
            "language_preference": language,
            "previous_questions": [],
            "received_welcome": False,
            "creation_time": datetime.now()
        }

    context = user_context[user_id]

    # Check if the message is a page reload signal
    if datetime.now() - context['creation_time'] > timedelta(hours=1):
        del user_context[user_id]

    # Send the welcome message if it hasn't been sent yet.
    if not context['received_welcome']:
        language = context["language_preference"]
        welcome_message = (
            '¡Bienvenido al Chatbot de PCB! ¿En qué puedo ayudarte hoy?'
            if language == 'spanish'
            else 'Welcome to the PCB Chatbot! How can I assist you today?'
        )
        context['received_welcome'] = True
        quick_replies = get_quick_replies(language)
        return jsonify({'reply': welcome_message, 'quick_replies': quick_replies})

    response_queue = Queue()
    Thread(target=process_request, args=(data, response_queue)).start()

    try:
        reply = response_queue.get(timeout=35)  # Espera un máximo de 35 segundos
    except Empty:
        return jsonify({'reply': "La respuesta está tardando más de lo esperado, por favor intenta de nuevo más tarde."}), 504

    quick_replies = get_quick_replies(context["language_preference"])    
    return jsonify({'reply': reply, 'quick_replies': quick_replies})

if os.environ.get('HEROKU_ENV'):
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
