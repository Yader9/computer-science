document.addEventListener("DOMContentLoaded", function() {
    const chatInput = document.getElementById("chatInput");
    const chatOutput = document.getElementById("chatOutput");
    const sendButton = document.getElementById("sendButton");
    const typingAnimation = document.getElementById("typingAnimation");
    const quickReplies = document.getElementById("quickReplies");
    let soundInitialized = false;
    let firstExchange = true;
    
    let observer = new MutationObserver(mutations => {
        mutations.forEach(mutation => {
            if (mutation.attributeName === "style") {
                console.log("quickReplies style changed to:", quickReplies.style.display);
            }
        });
    });
    
    observer.observe(quickReplies, {
        attributes: true // configure it to listen to attribute changes
    });
    

    chatInput.addEventListener("keydown", function (event) {
        if (event.keyCode === 13 && !event.shiftKey) {
            event.preventDefault();
            sendInputMessage();
        }
    });

    sendButton.addEventListener("click", sendInputMessage);

    function sendInputMessage() {
        console.log("Sending input message...");

        setTimeout(() => {
            console.log("Force hiding quick replies after delay...");
            quickReplies.style.display = 'none';
        }, 500);  // Adjust timing as needed for testing
        
        // Esconder las Quick Replies inmediatamente al enviar un mensaje
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
    
        setTimeout(() => {
            fetch("/chatbot", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: message })
            })
            .then(response => response.json())
            .then(data => {
                typingAnimation.style.display = "none";
                const reply = data.reply;
                appendMessageToChat("Bot", reply);

                // Added an if condition for quick_replies, independent of the firstExchange flag
                if(data.quick_replies) {
                    console.log("Displaying quick replies...");
                    displayQuickReplies(data.quick_replies);
                }

                if (firstExchange) {
                    firstExchange = false;
                }

                const receiveSound = document.getElementById("sendSound");
                receiveSound.volume = 0.5;
                receiveSound.play();
            })
            .catch(error => {
                console.error("Error:", error);
                typingAnimation.style.display = "none";
            });
        }, 1000);
    }


    function appendMessageToChat(sender, message) {
        const messageDiv = document.createElement("div");
        messageDiv.className = sender.toLowerCase();
        messageDiv.textContent = `${sender}: ${message}`;
        chatOutput.appendChild(messageDiv);
        chatOutput.scrollTop = chatOutput.scrollHeight;
    }

    function displayQuickReplies(replies) {
        console.log("Displaying quick replies...");
        while (quickReplies.firstChild) {
            quickReplies.removeChild(quickReplies.firstChild);
        }

        replies.forEach(reply => {
            const btn = document.createElement('div');
            btn.className = 'quick-reply';
            btn.innerText = reply;
            btn.onclick = function() {
                chatInput.value = reply;
                sendInputMessage();
            };
            quickReplies.appendChild(btn);
        });

        quickReplies.style.display = 'block';
    }

    function enableSound() {
        console.log("Enabling sound...");
        const receiveSound = document.getElementById("sendSound");
        receiveSound.play();
        receiveSound.pause();
    }

    document.getElementById("startChatButton").addEventListener("click", function() {
        const introScreen = document.getElementById('introScreen');
        if (introScreen) {
            introScreen.style.display = 'none';
        }
        document.querySelector(".chat-container").style.display = "block";
    });    
    
});

