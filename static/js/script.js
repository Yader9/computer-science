document.addEventListener("DOMContentLoaded", function() {
    const chatInput = document.getElementById("chatInput");
    const chatOutput = document.getElementById("chatOutput");
    const sendButton = document.getElementById("sendButton");
    const typingAnimation = document.getElementById("typingAnimation");
    const quickReplies = document.getElementById("quickReplies");
    // If the flag isn't set, it means it's the user's first visit/interaction.
    if (localStorage.getItem('firstExchangeComplete') === null) {
        localStorage.setItem('firstExchangeComplete', 'false');
    }

    let firstExchangeComplete = localStorage.getItem('firstExchangeComplete') === 'true';
    
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
            appendMessageToChat("User", message);
            if (!firstExchangeComplete) {
                // Mark the first exchange as complete to prevent future welcome messages
                localStorage.setItem('firstExchangeComplete', 'true');
                firstExchangeComplete = true;
            }
            sendMessageToBot(message);
            chatInput.value = "";
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
        });
    }

    function processBotResponse(data) {
        console.log('Processing bot response:', data);

        typingAnimation.style.display = "none";

        // Always append the bot's reply to the chat.
        if (data.reply) {
            appendMessageToChat("Bot", data.reply);
        }

        // Check if it's the first exchange and quick replies have not been displayed yet.
        if (data.quick_replies && !firstExchangeComplete) {
            displayQuickReplies(data.quick_replies);
            // Since we've now displayed the quick replies, set the flag to true.
            localStorage.setItem('firstExchangeComplete', 'true');
            firstExchangeComplete = true;
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
        // Do not send any message here, just show the chat interface.
    })
})