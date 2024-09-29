document.addEventListener("DOMContentLoaded", function() {
    const chatInput = document.getElementById("chatInput");
    const chatOutput = document.getElementById("chatOutput");
    const sendButton = document.getElementById("sendButton");
    const typingAnimation = document.getElementById("typingAnimation");
    const quickReplies = document.getElementById("quickReplies");
    
    const chatForm = document.getElementById("chatForm");
    chatForm.addEventListener("submit", function(event) {
        event.preventDefault();
        sendInputMessage();
    });

    chatInput.addEventListener("keydown", function(event) {
        if (event.keyCode === 13 && !event.shiftKey) {
            event.preventDefault();
            sendInputMessage();
        }
    });

    sendButton.addEventListener("click", sendInputMessage);

    function appendMessageToChat(sender, message) {
        const messageDiv = document.createElement("div");
        messageDiv.className = sender === "User" ? "user-message" : "bot-message";
        messageDiv.innerHTML = message;
        chatOutput.appendChild(messageDiv);
        chatOutput.scrollTop = chatOutput.scrollHeight;
    }

    function sendInputMessage() {
        const message = chatInput.value.trim();
        if (message) {
            appendMessageToChat("User", message);
            sendMessageToBot(message);
            chatInput.value = "";
            chatInput.focus(); // Enfocar el campo de entrada después de enviar
            quickReplies.style.display = 'none'; // Ocultar respuestas rápidas después de enviar
        }
    }

    function sendMessageToBot(message) {
        typingAnimation.style.display = "block";
        fetch("/chatbot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'pending') {
                pollForResponse(data.user_id);
            } else {
                processBotResponse(data);
            }
        })
        .catch(error => {
            console.error("Error:", error);
            typingAnimation.style.display = "none";
            appendMessageToChat("Bot", "Lo siento, ha ocurrido un error. Por favor, intenta nuevamente."); // Mostrar mensaje de error al usuario
        });
    }

    function processBotResponse(data) {
        console.log('Processing bot response:', data);

        typingAnimation.style.display = "none";
        
        // Siempre agrega la respuesta del bot al chat.
        if (data.reply) {
            appendMessageToChat("Bot", data.reply);
        }
        
        // Manejar respuestas rápidas desde el backend
        if (data.quick_replies && data.quick_replies.length > 0) {
            displayQuickReplies(data.quick_replies);
        } else {
            quickReplies.innerHTML = ''; // Limpiar respuestas rápidas si no hay nuevas
            quickReplies.style.display = 'none';
        }
        
        playReceiveSound();
    }     
        
    function pollForResponse(user_id, attempts = 0) {
        if (attempts >= 10) { // Limitar el número de intentos de polling
            typingAnimation.style.display = "none";
            appendMessageToChat("Bot", "El servidor está tardando en responder. Por favor, intenta más tarde.");
            return;
        }
        // Ajustar el tiempo de espera según sea necesario basado en el tiempo de procesamiento del backend
        setTimeout(() => {
            fetch(`/check_response?user_id=${user_id}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed') {
                    typingAnimation.style.display = "none";
                    appendMessageToChat("Bot", data.response);
                    playReceiveSound();
                } else if (data.status === 'error') {
                    console.error("Error from OpenAI:", data.error_message);
                    typingAnimation.style.display = "none";
                    appendMessageToChat("Bot", "Lo siento, ha ocurrido un error. Por favor, intenta nuevamente."); // Mostrar mensaje de error al usuario
                } else {
                    // Si el estado sigue siendo pendiente, volver a realizar polling
                    pollForResponse(user_id, attempts + 1);
                }
            })
            .catch(error => {
                console.error("Error while polling for response:", error);
                typingAnimation.style.display = "none";
                appendMessageToChat("Bot", "Lo siento, ha ocurrido un error. Por favor, intenta nuevamente."); // Mostrar mensaje de error al usuario
            });
        }, 3000); // Intervalo de polling de 3000ms
    }
    
    function displayQuickReplies(replies) {
        quickReplies.innerHTML = '';
        replies.forEach(reply => {
            const button = document.createElement('button');
            button.className = 'quick-reply';
            button.textContent = reply;
            button.addEventListener('click', function() {
                chatInput.value = reply;
                chatInput.focus(); // Enfocar el campo de entrada
                quickReplies.style.display = 'none';
            });
            quickReplies.appendChild(button);
        });
        quickReplies.style.display = 'flex';
    }

    function enableSound() {
        const receiveSound = document.getElementById("sendSound");
        receiveSound.play();
        receiveSound.pause();
    }

    function playReceiveSound() {
        const receiveSound = document.getElementById("sendSound");
        if (receiveSound) {
            receiveSound.volume = 0.5;
            receiveSound.play();
        }
    }

    document.getElementById("startChatButton").addEventListener("click", function() {
        const introScreen = document.getElementById('introScreen');
        introScreen.style.display = 'none';
        document.querySelector(".chat-container").style.display = "block";
        chatInput.focus(); // Enfocar el campo de entrada al iniciar el chat
        // No envíes ningún mensaje aquí, solo muestra la interfaz de chat.
    });
});