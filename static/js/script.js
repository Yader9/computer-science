document.addEventListener("DOMContentLoaded", function() {
    const chatInput = document.getElementById("chatInput");
    const chatOutput = document.getElementById("chatOutput");
    const sendButton = document.getElementById("sendButton");
    const typingAnimation = document.getElementById("typingAnimation");
    const quickReplies = document.getElementById("quickReplies");
    let soundInitialized = false;
    let firstExchange = true;
    let lastQuickReplies = [];

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

    function sendInputMessage() {
        console.log("Sending input message...");
        quickReplies.style.display = 'none';
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
        console.log("Sending message to bot...");
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
                // Poll for response using the user_id returned by the server
                pollForResponse(data.user_id);
            } else {
                // Handle immediate response here if necessary
                typingAnimation.style.display = "none";
                appendMessageToChat("Bot", data.reply);
                if (data.quick_replies) {
                    displayQuickReplies(data.quick_replies);
                }
                playReceiveSound();
            }
        })
        .catch(error => {
            console.error("Error:", error);
            typingAnimation.style.display = "none";
        });
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
                    // Continue polling if the status is still 'pending'
                    pollForResponse(user_id);
                }
            })
            .catch(error => {
                console.error("Error while polling for response:", error);
                typingAnimation.style.display = "none";
            });
        }, 3000); // Poll every 3 seconds
    }

    function appendMessageToChat(sender, message) {
        const messageDiv = document.createElement("div");
        messageDiv.className = sender === "User" ? "user-message" : "bot-message";
        messageDiv.textContent = message;
        chatOutput.appendChild(messageDiv);
        chatOutput.scrollTop = chatOutput.scrollHeight;
    }

    function displayQuickReplies(replies) {
        // Convert both arrays to strings and compare
        if (JSON.stringify(replies) !== JSON.stringify(lastQuickReplies)) {
            // Clear the current quick replies
            while (quickReplies.firstChild) {
                quickReplies.removeChild(quickReplies.firstChild);
            }
    
            // Display new quick replies and update the stored ones
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

            quickReplies.style.display = 'block';
            lastQuickReplies = replies.slice(); // Store a copy of the current replies
        }
    }

    function enableSound() {
        // This function ensures that the sound is enabled by the browser
        const receiveSound = document.getElementById("sendSound");
        receiveSound.play();
        receiveSound.pause();
    }

    function playReceiveSound() {
        // Play a sound when the message from the bot is received
        const receiveSound = document.getElementById("sendSound");
        if (receiveSound) {
            receiveSound.volume = 0.5;
            receiveSound.play();
        }
    }

    document.getElementById("startChatButton").addEventListener("click", function() {
        const introScreen = document.getElementById('introScreen');
        if (introScreen) {
            introScreen.style.display = 'none';
        }
        document.querySelector(".chat-container").style.display = "block";
    });
});
