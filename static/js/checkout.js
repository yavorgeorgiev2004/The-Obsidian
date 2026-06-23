/*
 * The Obsidian — Stripe checkout handler.
 * Used by both the deposit and the top-up payment pages. Reads its
 * configuration from data attributes so the same external file serves
 * both flows with no inline JS.
 */
document.addEventListener('DOMContentLoaded', function () {

  // Read the Stripe configuration from the payment element's data attributes
  const paymentEl = document.getElementById('payment-element');
  if (!paymentEl) return;

  const clientSecret = paymentEl.dataset.clientSecret;
  const publicKey    = paymentEl.dataset.publicKey;
  const successUrl   = paymentEl.dataset.successUrl;

  // Initialise Stripe and create the card input
  
  const stripe   = Stripe(publicKey, { locale: 'en-GB' });
  const elements = stripe.elements();
  const card     = elements.create('card', {
    style: {
      base: {
        color: '#F5F5F5',
        fontFamily: 'Montserrat, sans-serif',
        fontSize: '14px',
        '::placeholder': { color: 'rgba(232,232,232,0.4)' },
      },
    },
  });
  card.mount('#card-element');

  // Show inline card errors as the guest types
  card.on('change', function (event) {
    document.getElementById('card-errors').textContent = event.error ? event.error.message : '';
  });

  // Confirm the payment when the pay button is clicked
  const payButton = document.getElementById('pay-button');
  payButton.addEventListener('click', function () {
    // Disable the button while the payment is processing
    payButton.disabled = true;
    payButton.textContent = 'Processing...';

    // Confirm the card payment with Stripe using the client secret
    stripe.confirmCardPayment(clientSecret, {
      payment_method: { card: card },
    }).then(function (result) {
      if (result.error) {
        // Show the error and re-enable the button to try again
        document.getElementById('card-errors').textContent = result.error.message;
        payButton.disabled = false;
        payButton.textContent = 'Try Again ◆';
      } else if (result.paymentIntent && result.paymentIntent.status === 'succeeded') {
        // On success, go to the deposit or top-up success page
        window.location.href = successUrl;
      }
    });
  });
});
