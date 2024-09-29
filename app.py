"""
Este módulo proporciona un endpoint para un servicio de Chatbot que ayuda a personas que desean iniciar en el gimnasio, proporcionando rutinas y planes de ejercicios personalizados.
"""

import logging
import os
import threading
from datetime import datetime
from threading import Lock
from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
import openai
from openai.error import OpenAIError
from flask_session import Session

# Configuración de logging
logging.basicConfig(level=logging.DEBUG)

# Inicialización de la aplicación Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = True
Session(app)
CORS(app)  # Habilitar CORS

# Variables globales
user_context = {}
openai_responses = {}
openai_responses_lock = Lock()  # Lock para seguridad en hilos
openai.api_key = os.environ.get('OPENAI_API_KEY')
user_requests = {}

# Función para detectar el idioma del mensaje
def detect_language(message):
    """
    Detectar el idioma de un mensaje dado.
    """
    spanish_keywords = ['hola', 'buenas', 'ayuda', 'día', 'gracias', 'por favor']
    return 'spanish' if any(word in message.lower() for word in spanish_keywords) else 'english'

# Función para obtener respuestas rápidas basadas en la preferencia de idioma del usuario
def get_quick_replies(language):
    if language == 'spanish':
        return ['¿Cómo puedo empezar a entrenar?', 'Necesito una rutina de ejercicios', 'Consejos para una alimentación saludable']
    else:
        return ['How can I start training?', 'I need an exercise routine', 'Tips for healthy eating']

# Función para verificar si se ha excedido el límite de solicitudes
def rate_limit_exceeded(user_id):
    user_requests[user_id] = user_requests.get(user_id, 0) + 1
    if user_requests[user_id] > 50:  # Límite por usuario
        return True
    return False

# Función para obtener o crear el contexto del usuario y actualizarlo con el nuevo mensaje
def get_or_create_context(user_id, message):
    if 'user_context' not in session or user_id not in session['user_context']:
        session['user_context'] = session.get('user_context', {})
        session['user_context'][user_id] = {
            "language_preference": detect_language(message),
            "previous_questions": [message],
            "received_welcome": False,
            "creation_time": datetime.now().isoformat(),
            # Nuevos campos para datos del usuario
            "age": None,
            "gender": None,
            "lifestyle": None,
            "eating_habits": None
        }
    else:
        session['user_context'][user_id]['previous_questions'].append(message)
        session['user_context'][user_id]['previous_questions'] = session['user_context'][user_id]['previous_questions'][-5:]

    session.modified = True
    return session['user_context'][user_id]

def send_welcome_message(user_id):
    context = session['user_context'][user_id]
    if not context['received_welcome']:
        # Preparar el mensaje de bienvenida y respuestas rápidas
        language = context["language_preference"]
        welcome_message = ('¡Bienvenido al Asistente de Gimnasio! ¿En qué puedo ayudarte hoy?'
                           if language == 'spanish' else
                           'Welcome to the Gym Assistant! How can I assist you today?')
        quick_replies = get_quick_replies(language)

        # Actualizar el contexto con el indicador de bienvenida recibida
        context['received_welcome'] = True
        session['user_context'][user_id] = context
        session.modified = True  # Marcar la sesión como modificada para guardar cambios

        return welcome_message, quick_replies
    else:
        # Las respuestas rápidas ya se han enviado; devolver sin ellas
        return None, []

# Función para preparar los mensajes de contexto
def prepare_context_messages(user_id):
    if 'user_context' not in session or user_id not in session['user_context']:
        logging.error('user_id %s no encontrado en user_context de la sesión', user_id)
        return [{"role": "system", "content": "Por favor, inicia una nueva conversación."}]

    # Preparar los mensajes de contexto
    context = session['user_context'][user_id]
    language = context["language_preference"]

    if language == 'spanish':
        system_message = """
        Eres un asistente personal de fitness que proporciona rutinas y planes de ejercicios personalizados basados en la edad, género, estilo de vida y hábitos alimenticios del usuario.
        Deberás hacer una pregunta a la vez. No continúes con la siguiente pregunta hasta que el usuario haya respondido a la anterior.
        Las preguntas que debes hacer son las siguientes:

        1. **Edad y Género:** Estos factores pueden influir en el tipo de ejercicio y la intensidad recomendada.
        2. **Nivel de Actividad Actual:** ¿Eres principiante, intermedio o avanzado en cuanto a actividad física?
        3. **Objetivos de Fitness:** ¿Qué deseas lograr? (por ejemplo, perder peso, ganar músculo, mejorar resistencia, etc.)
        4. **Hábitos Alimenticios:** ¿Sigues alguna dieta específica o tienes alguna restricción alimenticia?
        5. **Horario y Disponibilidad:** ¿Cuántos días a la semana puedes dedicar al ejercicio y cuánto tiempo tienes disponible por sesión?
        6. **Preferencias de Ejercicio:** ¿Prefieres entrenar en casa o en el gimnasio? ¿Tienes equipo de ejercicio en casa?
        7. **Consideraciones de Salud:** ¿Tienes alguna lesión o condición de salud que deba tener en cuenta?

        Por favor, realiza una pregunta a la vez en función de la respuesta del usuario.
        """
    else:
        system_message = """
        You are a personal fitness assistant providing personalized exercise routines and plans based on the user's age, gender, lifestyle, and eating habits.
        You should ask one question at a time and wait for the user's response before proceeding to the next question.
        The questions you should ask are as follows:

        1. **Age and Gender:** These factors may influence the type of exercise and recommended intensity.
        2. **Current Activity Level:** Are you a beginner, intermediate, or advanced when it comes to physical activity?
        3. **Fitness Goals:** What do you want to achieve? (e.g., lose weight, gain muscle, improve endurance, etc.)
        4. **Dietary Habits:** Do you follow any specific diet, or do you have any dietary restrictions?
        5. **Schedule and Availability:** How many days a week can you dedicate to exercise, and how much time do you have available per session?
        6. **Exercise Preferences:** Do you prefer to exercise at home or at the gym? Do you have home exercise equipment?
        7. **Health Considerations:** Do you have any injuries or health conditions that I should consider?

        Please ask one question at a time based on the user's response.
        """

    context_messages = [
        {"role": "system", "content": system_message}
    ] + [
        {"role": "user", "content": msg}
        for msg in context.get('previous_questions', [])[-5:]
    ]
    return context_messages

def handle_chatbot_conversation(user_id, message):
    if user_id not in session.get('user_context', {}):
        logging.error('user_id %s no está en user_context de la sesión', user_id)
        return {"status": "error", "error_message": "Error de sesión: contexto de usuario no encontrado"}

    # Actualizar el contexto del usuario con el nuevo mensaje
    get_or_create_context(user_id, message)
    context_messages = prepare_context_messages(user_id)

    if context_messages:
        thread = threading.Thread(
            target=call_openai_api, args=(user_id, context_messages))
        thread.start()
        return {"status": "pending", "user_id": user_id}
    else:
        return {"status": "error", "error_message": "No se puede iniciar la conversación con un contexto vacío"}

def call_openai_api(user_id, context_messages):
    if not context_messages:
        logging.error('Mensajes de contexto vacíos para user_id %s', user_id)
        with openai_responses_lock:
            openai_responses[user_id] = {
                "status": "error",
                "error_message": "Mensajes de contexto vacíos"
            }
        return

    try:
        # Llamar a la API de OpenAI con los mensajes de contexto
        response = openai.ChatCompletion.create(
            model="gpt-4o-2024-08-06",
            messages=context_messages,
            max_tokens=500,
            temperature=0.7
        )
        with openai_responses_lock:
            openai_responses[user_id] = {
                "status": "completed",
                "response": response.choices[0].message['content']
            }
    except OpenAIError as e:
        logging.error('Error de la API de OpenAI para user_id %s: %s', user_id, str(e))
        with openai_responses_lock:
            openai_responses[user_id] = {
                "status": "error",
                "error_message": str(e)
            }

# Endpoint para verificar el estado de la respuesta de la API de OpenAI
@app.route('/check_response', methods=['GET'])
def check_response():
    user_id = request.args.get('user_id')
    with openai_responses_lock:
        if user_id in openai_responses:
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
        return jsonify({'status': 'error', 'error_message': 'Límite de solicitudes excedido'}), 429

    data = request.get_json()
    message = data['message']

    get_or_create_context(user_id, message)

    welcome_message, quick_replies = send_welcome_message(user_id)
    if welcome_message:
        return jsonify({'reply': welcome_message, 'quick_replies': quick_replies})

    # Continuar con la conversación normal del chatbot
    result = handle_chatbot_conversation(user_id, message)
    return jsonify(result)
