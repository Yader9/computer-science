from flask import Flask, request, jsonify, render_template
import openai
import os

app = Flask(__name__)
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/')
def index():
    """Renders the chatbot interface."""
    return render_template('chatbot_interface.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    message = data['message']
    language = detect_language(message)
    quick_replies = get_quick_replies(language)
    reply = call_openai_api(message)
    return jsonify({'reply': reply, 'quick_replies': quick_replies})

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
        app.logger.error("Error processing request: %s", str(e))
        return f"Error: {str(e)}"

if __name__ == '__main__':
    app.run()
