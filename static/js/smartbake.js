const form = document.getElementById('smartBakeForm');
const input = document.getElementById('smartBakeInput');
const messages = document.getElementById('chatMessages');
const sendButton = document.getElementById('sendButton');

function addMessage(text, type, name) {
    const wrapper = document.createElement('div');
    wrapper.className = `message ${type}-message`;

    const label = document.createElement('div');
    label.className = 'message-name';
    label.textContent = name;

    const paragraph = document.createElement('p');
    paragraph.textContent = text;

    wrapper.appendChild(label);
    wrapper.appendChild(paragraph);
    messages.appendChild(wrapper);
    messages.scrollTop = messages.scrollHeight;
    return wrapper;
}

if (form) {
    document.querySelectorAll('.prompt-chip').forEach(button => {
        button.addEventListener('click', () => {
            input.value = button.textContent.trim();
            input.focus();
        });
    });

    form.addEventListener('submit', async event => {
        event.preventDefault();
        const text = input.value.trim();
        if (!text) return;

        addMessage(text, 'user', 'You');
        input.value = '';
        sendButton.disabled = true;

        const typing = addMessage('Thinking about the best cake for you…', 'assistant', 'SmartBake');
        typing.classList.add('typing');

        try {
            const response = await fetch('/api/smartbake', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: text})
            });

            const data = await response.json();
            typing.remove();

            if (!response.ok) {
                addMessage(data.error || 'SmartBake could not respond right now.', 'assistant', 'SmartBake');
            } else {
                addMessage(data.reply, 'assistant', 'SmartBake');
            }
        } catch (error) {
            typing.remove();
            addMessage('SmartBake could not connect. Check your internet connection and try again.', 'assistant', 'SmartBake');
        } finally {
            sendButton.disabled = false;
            input.focus();
        }
    });

    messages.scrollTop = messages.scrollHeight;
}
