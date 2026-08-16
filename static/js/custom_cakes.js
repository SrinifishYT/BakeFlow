const form = document.getElementById('customCakeForm');

if (form) {
    const priceFields = ['size', 'flavour', 'filling', 'frosting', 'shape', 'dietary'];
    const colour = document.getElementById('colour');
    const priceOutput = document.getElementById('estimatedPrice');
    const preview = document.getElementById('cakePreview');
    const title = document.getElementById('previewTitle');
    const description = document.getElementById('previewDescription');
    const messageInput = form.querySelector('[name="cake_message"]');
    const messageOutput = document.getElementById('previewMessage');

    function selectedPrice(select) {
        const option = select.options[select.selectedIndex];
        return Number(option.dataset.price || 0);
    }

    function updatePreview() {
        let total = 0;

        priceFields.forEach(id => {
            total += selectedPrice(document.getElementById(id));
        });

        form.querySelectorAll('input[name="decorations"]:checked').forEach(box => {
            total += Number(box.dataset.price || 0);
        });

        const size = document.getElementById('size').value;
        const flavour = document.getElementById('flavour').value;
        const filling = document.getElementById('filling').value;
        const frosting = document.getElementById('frosting').value;
        const shape = document.getElementById('shape').value;

        priceOutput.textContent = `$${total.toFixed(2)}`;
        title.textContent = `${flavour} ${shape} Cake`;
        description.textContent = `${size} · ${filling} · ${frosting}`;
        preview.style.setProperty('--cake-colour', colour.value);
        messageOutput.textContent = messageInput.value.trim() || 'Your Cake';
    }

    form.addEventListener('change', updatePreview);
    form.addEventListener('input', updatePreview);
    updatePreview();
}
