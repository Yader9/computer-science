document.addEventListener("DOMContentLoaded", function() {
    const chatInput = document.getElementById("chatInput");
    const chatOutput = document.getElementById("chatOutput");
    const sendButton = document.getElementById("sendButton");
    const typingAnimation = document.getElementById("typingAnimation");
    const quickReplies = document.getElementById("quickReplies");
    let soundInitialized = false;
    let firstExchange = localStorage.getItem('firstExchange') !== 'false';
    
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
        messageDiv.textContent = message;
        chatOutput.appendChild(messageDiv);
        chatOutput.scrollTop = chatOutput.scrollHeight;
    }

    function sendInputMessage() {
        const message = chatInput.value.trim();
        if (message) {
            if (!soundInitialized) {
                enableSound();
                soundInitialized = true;
            }
            sendMessageToBot(message);
            chatInput.value = "";
        }
    }

    function sendMessageToBot(message) {
        appendMessageToChat("User", message);
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
        });
    }

    function processBotResponse(data) {
        typingAnimation.style.display = "none";
        if (firstExchange && data.quick_replies && data.quick_replies.length > 0) {
            displayQuickReplies(data.quick_replies);
            firstExchange = false;
            localStorage.setItem('firstExchange', 'false');
        }
        if (data.reply) {
            appendMessageToChat("Bot", data.reply);
        }
        playReceiveSound();
    }
    
    function pollForResponse(user_id) {
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
                } else {
                    pollForResponse(user_id);
                }
            })
            .catch(error => {
                console.error("Error while polling for response:", error);
                typingAnimation.style.display = "none";
            });
        }, 3000);
    }

    function displayQuickReplies(replies) {
        quickReplies.innerHTML = '';
        replies.forEach(reply => {
            const button = document.createElement('button');
            button.className = 'quick-reply';
            button.textContent = reply;
            button.addEventListener('click', function() {
                chatInput.value = reply;
                sendInputMessage();
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
        if (firstExchange) {
            sendMessageToBot('');
        }
    });
});
