"""
This module provides an endpoint for a Chatbot service to answer PCB-related questions.
"""

# Import necessary libraries

import logging
import os
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, render_template
import openai
from openai.error import OpenAIError
from flask_session import Session

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = True
Session(app)

user_context = {}
openai.api_key = os.environ.get('OPENAI_API_KEY')

REQUEST_COUNT = 0


def detect_language(message):
    """Detect the language of a given message."""
    spanish_keywords = ['hola', 'buenas',
                        'ayuda', 'día', 'gracias', 'por favor']
    return 'spanish' if any(word in message.lower() for word in spanish_keywords) else 'english'


def get_quick_replies(language):
    """Generate quick replies based on the user's language preference."""
    if language == 'spanish':
        return ['¿Qué es un PCB?', 'Cuéntame sobre electrónica', '¿Cómo se hacen los PCBs?']
    else:
        return ['What is a PCB?', 'Tell me about electronics', 'How are PCBs made?']


@app.route('/')
def index():
    """Renders the chatbot interface."""
    return render_template('chatbot_interface.html')


@app.route('/chatbot', methods=['POST'])
def chatbot():
    """Endpoint to communicate with the chatbot and get a response."""
    global REQUEST_COUNT

    if 'user_id' not in session:
        session['user_id'] = os.urandom(24).hex()
    user_id = session['user_id']

    data = request.get_json()
    message = data['message']

    if user_id not in user_context:
        language = detect_language(message)
        welcome_message = (
            '¡Bienvenido al Chatbot de PCB! ¿En qué puedo ayudarte hoy?'
            if language == 'spanish'
            else 'Welcome to the PCB Chatbot! How can I assist you today?'
        )
        user_context[user_id] = {
            "language_preference": language,
            "previous_questions": [message],
            "creation_time": datetime.now()
        }
        quick_replies = get_quick_replies(language)
        return jsonify({'reply': welcome_message, 'quick_replies': quick_replies})
    context = user_context[user_id]

    # Check if the context is older than an hour
    if datetime.now() - context['creation_time'] > timedelta(hours=1):
        del user_context[user_id]

    if "arduino" in message.lower():
        context["specific_product"] = "Arduino"
    if "diseño" in message.lower() or "design" in message.lower():
        context["last_inquired_topic"] = "PCB Design"

    context["previous_questions"].append(message)
    if len(context["previous_questions"]) > 5:
        context["previous_questions"].pop(0)

    # Control the flow for specific questions
    if message.lower() == 'hola':
        return jsonify({'reply': '¡Te saluda el Chatbot de PCB! ¿En qué puedo ayudarte?', 'quick_replies': quick_replies})

    REQUEST_COUNT += 1
    if REQUEST_COUNT > 50:  # Limit the number of API calls
        return jsonify({'reply': "Has superado el número máximo de solicitudes. Intenta más tarde"})

    for _ in range(3):  # 3 retry attempts
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": message}
                ],
                max_tokens=300,
                temperature=0.2
            )

            # Verificando la respuesta
            choice_content = response.choices[0].get(
                'message', {}).get('content')
            if choice_content:
                reply = choice_content.strip()
                break
            else:
                logging.error("Unexpected response from OpenAI API")
                return jsonify({'reply': "Sorry, I couldn't understand that."})

        except OpenAIError as e:
            logging.error("OpenAI API error: %s", str(e))
            time.sleep(2)  # Esperamos un momento antes de intentar de nuevo
            continue  # Continuar para intentar de nuevo

        except Exception as e:  # pylint: disable=broad-except
            logging.error("General error: %s", str(e))
            return jsonify({'reply': f"Unexpected error: {str(e)}"})

    # Sugerencias de respuesta rápida
    if 'has_received_quick_replies' not in context:
        context['has_received_quick_replies'] = True
        quick_replies = get_quick_replies(context["language_preference"])
    else:
        quick_replies = []

    return jsonify({'reply': reply, 'quick_replies': quick_replies})


if os.environ.get('HEROKU_ENV'):
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
