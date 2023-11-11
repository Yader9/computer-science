"""
This module provides an endpoint for a Chatbot service to answer PCB-related questions.
"""

# Import necessary libraries
import logging
import os
from flask import Flask, render_template
from flask_socketio import SocketIO
import openai

# Initialize Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Global variable
openai.api_key = os.environ.get('OPENAI_API_KEY')

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

def call_openai_api(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": message}
            ],
            max_tokens=150,
            temperature=0.5
        )
        return response.choices[0].get('message', {}).get('content').strip()
    except Exception as e:
        logging.error("Error processing request: %s", str(e))
        return f"Error: {str(e)}"

@app.route('/')
def index():
    """Renders the chatbot interface."""
    return render_template('chatbot_interface.html')

@socketio.on('send_message')
def handle_message(data):
    message = data['message']
    language = detect_language(message)
    quick_replies = get_quick_replies(language)
    reply = call_openai_api(message)
    socketio.emit('receive_reply', {'reply': reply, 'quick_replies': quick_replies})

if __name__ == '__main__':
    socketio.run(app)

