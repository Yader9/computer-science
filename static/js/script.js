document.addEventListener("DOMContentLoaded", function() {
    const chatInput = document.getElementById("chatInput");
    const chatOutput = document.getElementById("chatOutput");
    const sendButton = document.getElementById("sendButton");
    const typingAnimation = document.getElementById("typingAnimation");
    const quickReplies = document.getElementById("quickReplies");
    let soundInitialized = false;

    // Inicializar la conexión WebSocket
    const socket = io();

    chatInput.addEventListener("keydown", function(event) {
        if (event.keyCode === 13 && !event.shiftKey) {
            event.preventDefault();
            sendInputMessage();
        }
    });

    sendButton.addEventListener("click", sendInputMessage);

    function sendInputMessage() {
        const message = chatInput.value.trim();
        if (message) {
            sendMessageToBot(message);
            chatInput.value = "";
        }
    }

    function sendMessageToBot(message) {
        appendMessageToChat("User", message);
        typingAnimation.style.display = "block";
        socket.emit('send_message', { message: message });
    }

    socket.on('receive_reply', function(data) {
        typingAnimation.style.display = "none";
        const reply = data.reply;
        appendMessageToChat("Bot", reply);
        displayQuickReplies(data.quick_replies);
        playReceiveSound();
    });

    function appendMessageToChat(sender, message) {
        const messageDiv = document.createElement("div");
        messageDiv.className = sender.toLowerCase();
        messageDiv.textContent = `${sender}: ${message}`;
        chatOutput.appendChild(messageDiv);
        chatOutput.scrollTop = chatOutput.scrollHeight;
    }

    function displayQuickReplies(replies) {
        quickReplies.innerHTML = ''; // Clear the current quick replies
        replies.forEach(reply => {
            const btn = document.createElement('div');
            btn.className = 'quick-reply';
            btn.innerText = reply;
            btn.onclick = function() {
                chatInput.value = reply;
                sendInputMessage();
                quickReplies.style.display = 'none';
            };
            quickReplies.appendChild(btn);
        });
        quickReplies.style.display = replies.length > 0 ? 'block' : 'none';
    }

    function playReceiveSound() {
        if (!soundInitialized) {
            const receiveSound = document.getElementById("sendSound");
            receiveSound.play();
            receiveSound.pause();
            soundInitialized = true;
        }
        const receiveSound = document.getElementById("sendSound");
        receiveSound.volume = 0.5;
        receiveSound.play();
    }

    document.getElementById("startChatButton").addEventListener("click", function() {
        const introScreen = document.getElementById('introScreen');
        if (introScreen) {
            introScreen.style.display = 'none';
        }
        document.querySelector(".chat-container").style.display = "block";
    });
});
