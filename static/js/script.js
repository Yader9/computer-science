document.addEventListener("DOMContentLoaded", function() {
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const chatOutput = document.getElementById("chatOutput");
    const typingAnimation = document.getElementById("typingAnimation");
    const quickReplies = document.getElementById("quickReplies");
    let soundInitialized = false;

    chatForm.addEventListener("submit", function(event) {
        event.preventDefault();
        const message = chatInput.value.trim();
        if (message) {
            sendMessageToBot(message);
            chatInput.value = "";
        }
    });

    function sendMessageToBot(message) {
        appendMessageToChat("User", message);
        typingAnimation.style.display = "block";

        // Create a FormData object to send the message as a form field
        const formData = new FormData();
        formData.append("message", message);

        // Send the form data to Flask
        fetch('/send_message', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            handleBotReply(data);
        })
        .catch((error) => {
            console.error('Error:', error);
        });
    }

    function handleBotReply(data) {
        typingAnimation.style.display = "none";
        const reply = data.reply;
        appendMessageToChat("Bot", reply);
        displayQuickReplies(data.quick_replies);
        playReceiveSound();
    }

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
                chatForm.submit(); // Submit the form when a quick reply is clicked
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
        console.log("Comenzar button clicked");
        const introScreen = document.getElementById('introScreen');
        if (introScreen) {
            introScreen.style.display = 'none';
        }
        document.querySelector(".chat-container").style.display = "block";
    });
});

