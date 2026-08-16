const deliveryFields = document.getElementById('deliveryFields');
const deliveryCost = document.getElementById('deliveryCost');
const totalOutput = document.getElementById('checkoutTotal');
const deliveryRadios = document.querySelectorAll('input[name="delivery_method"]');

function updateDelivery() {
    const selected = document.querySelector('input[name="delivery_method"]:checked');
    if (!selected || !totalOutput) return;

    const subtotal = Number(totalOutput.dataset.subtotal || 0);
    const fee = Number(totalOutput.dataset.fee || 0);
    const isDelivery = selected.value === 'Delivery';

    deliveryFields.classList.toggle('active', isDelivery);
    deliveryCost.textContent = isDelivery ? `$${fee.toFixed(2)}` : 'Free';
    totalOutput.textContent = `$${(subtotal + (isDelivery ? fee : 0)).toFixed(2)}`;

    deliveryFields.querySelectorAll('input, select').forEach(field => {
        field.required = isDelivery;
    });
}

deliveryRadios.forEach(radio => radio.addEventListener('change', updateDelivery));
updateDelivery();
