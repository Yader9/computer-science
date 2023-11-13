"""
This module provides an endpoint for a Chatbot service to answer PCB-related questions.
"""

import logging
import os
import concurrent.futures
from datetime import datetime
from flask import Flask, request, jsonify, session, render_template
import openai
from openai.error import OpenAIError
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
user_requests = {}

# Function to detect the language of the message
def detect_language(message):
    """
    Detect the language of a given message.
    """
    spanish_keywords = ['hola', 'buenas', 'ayuda', 'día', 'gracias', 'por favor']
    return 'spanish' if any(word in message.lower() for word in spanish_keywords) else 'english'

# Function to get quick replies based on the user's language preference
def get_quick_replies(language):
    if language == 'spanish':
        return ['¿Qué es un PCB?', 'Cuéntame sobre electrónica', '¿Cómo se hacen los PCBs?']
    else:
        return ['What is a PCB?', 'Tell me about electronics', 'How are PCBs made?']

# Function to check if rate limit has been exceeded
def rate_limit_exceeded(user_id):
    user_requests[user_id] = user_requests.get(user_id, 0) + 1
    if user_requests[user_id] > 50:  # Limit per user
        return True
    return False

# Function to get or create user context
def get_or_create_context(user_id, message):
    if user_id not in user_context:
        language = detect_language(message)
        user_context[user_id] = {
            "language_preference": language,
            "previous_questions": [],
            "received_welcome": False,
            "creation_time": datetime.now()
        }
    return user_context[user_id]

# Function to send the welcome message
def send_welcome_message(context):
    language = context["language_preference"]
    welcome_message = '¡Bienvenido al Chatbot de PCB! ¿En qué puedo ayudarte hoy?' if language == 'spanish' else 'Welcome to the PCB Chatbot! How can I assist you today?'
    context['received_welcome'] = True
    quick_replies = get_quick_replies(language)
    return welcome_message, quick_replies

# Function to handle the conversation with the chatbot
def handle_chatbot_conversation(message, context):
    """
    Handle the conversation with the chatbot and return the reply and quick replies.
    """
    reply, quick_replies = "", []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(call_openai_api, message)
        try:
            choice_content = future.result(timeout=10)  # 10-second timeout
            reply = choice_content.strip() if choice_content else "Sorry, I couldn't understand that."
        except concurrent.futures.TimeoutError:
            logging.error("OpenAI API call timed out for user %s", context['user_id'])
            reply = "The request timed out"
    return reply, quick_replies

# Function to call the OpenAI API asynchronously
def call_openai_api(message):
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

        return response.choices[0].message['content']
    except OpenAIError as e:
        logging.error("OpenAI API error: %s", e)
    return ""

@app.route('/')
def index():
    return render_template('chatbot_interface.html')

@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_id = session.get('user_id', os.urandom(24).hex())
    session['user_id'] = user_id

    if rate_limit_exceeded(user_id):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    try:
        data = request.get_json()
        message = data['message']
        context = get_or_create_context(user_id, message)

        if context['received_welcome']:
            reply, quick_replies = handle_chatbot_conversation(message, context)
        else:
            reply, quick_replies = send_welcome_message(context)

        return jsonify({'reply': reply, 'quick_replies': quick_replies})

    except ValueError as ve:
        # Handle specific ValueError that you expect may happen
        logging.error("ValueError handling /chatbot request: %s", ve)
        return jsonify({'error': 'Invalid input received'}), 400
    except Exception as e:
        # This is a catch-all for unexpected exceptions
        logging.error("Unexpected error handling /chatbot request: %s", e)
        return jsonify({'error': 'An error occurred while processing your request'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
