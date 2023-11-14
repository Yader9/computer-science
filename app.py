"""
This module provides an endpoint for a Chatbot service to answer PCB-related questions.
"""

import logging
import os
import threading
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
openai_responses = {}
openai.api_key = os.environ.get('OPENAI_API_KEY')
user_requests = {}

# Function to detect the language of the message


def detect_language(message):
    """
    Detect the language of a given message.
    """
    spanish_keywords = ['hola', 'buenas',
                        'ayuda', 'día', 'gracias', 'por favor']
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

# Function to get or create user context and update it with the new message


def get_or_create_context(user_id, message):
    if 'user_context' not in session or user_id not in session['user_context']:
        session['user_context'] = session.get('user_context', {})
        session['user_context'][user_id] = {
            "language_preference": detect_language(message),
            "previous_questions": [message],
            "received_welcome": False,
            "creation_time": datetime.now().isoformat()
        }
    else:
        # Directly modify the session's user_context without assigning it to a local variable
        session['user_context'][user_id]['previous_questions'].append(message)
        session['user_context'][user_id]['previous_questions'] = session['user_context'][user_id]['previous_questions'][-5:]

    session.modified = True
    return session['user_context'][user_id]


def send_welcome_message(user_id):
    context = session['user_context'][user_id]
    if not context['received_welcome']:
        # Prepare the welcome message and quick replies
        language = context["language_preference"]
        welcome_message = ('¡Bienvenido al Chatbot de PCB! ¿En qué puedo ayudarte hoy?'
                           if language == 'spanish' else
                           'Welcome to the PCB Chatbot! How can I assist you today?')
        quick_replies = get_quick_replies(language)

        # Update the context with the received_welcome flag
        context['received_welcome'] = True
        session['user_context'][user_id] = context
        session.modified = True  # Mark session as modified to save changes

        return welcome_message, quick_replies
    else:
        # Quick replies have already been sent; return without them
        return None, []

# New function to prepare the context messages


def prepare_context_messages(user_id):
    # Check if user_id exists in the user_context dictionary
    if user_id in user_context:
        context_messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ] + [
            {"role": "user", "content": msg}
            for msg in user_context[user_id]['previous_questions'][-5:]
        ]
        return context_messages
    else:
        # Handle the case where user_id is not found, perhaps by initializing it or logging an error
        logging.error(f'user_id {user_id} not found in user_context')
        return []


# Modified function to handle the chatbot conversation by starting a new thread


def handle_chatbot_conversation(user_id, message):
    # Update the user context with the new message
    get_or_create_context(user_id, message)
    context_messages = prepare_context_messages(user_id)

    # Initiate the OpenAI API call in a separate thread
    thread = threading.Thread(target=call_openai_api,
                              args=(user_id, context_messages))
    thread.start()
    return {"status": "pending", "user_id": user_id}

# Modified function to call the OpenAI API with the provided context messages


def call_openai_api(user_id, context_messages):
    try:
        # Call OpenAI API with the context messages
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=context_messages,
            max_tokens=150,
            temperature=0.2
        )
        # Store the response in the global dictionary
        openai_responses[user_id] = {
            "status": "completed",
            "response": response.choices[0].message['content']
        }
    except OpenAIError as e:
        openai_responses[user_id] = {
            "status": "error",
            "error_message": str(e)
        }

# Endpoint for checking the status of the OpenAI API response


@app.route('/check_response', methods=['GET'])
def check_response():
    user_id = request.args.get('user_id')
    if user_id in openai_responses:
        # If the response is ready, pop it from the dictionary and return it
        return jsonify(openai_responses.pop(user_id))
    return jsonify({"status": "pending"})


@app.route('/')
def index():
    return render_template('chatbot_interface.html')


@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_id = session.get('user_id')
    if not user_id:
        user_id = os.urandom(24).hex()
        session['user_id'] = user_id

    if rate_limit_exceeded(user_id):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    data = request.get_json()
    message = data['message']

    get_or_create_context(user_id, message)

    welcome_message, quick_replies = send_welcome_message(user_id)
    if welcome_message:
        return jsonify({'reply': welcome_message, 'quick_replies': quick_replies})

    # Continue with the normal chatbot conversation
    result = handle_chatbot_conversation(user_id, message)
    return jsonify(result)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
