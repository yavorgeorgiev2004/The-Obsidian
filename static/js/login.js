/*
 * The Obsidian — login page interactivity.
 * Lets the three demo-account buttons fill the sign-in form when clicked,
 * so the page can be tested quickly. All behaviour is external here;
 * the template carries no inline JavaScript.
 */
document.addEventListener('DOMContentLoaded', function () {

  // Find the email and password inputs rendered by the allauth form.
  // allauth names them "login" and "password".
  const emailInput    = document.querySelector('input[name="login"]');
  const passwordInput = document.querySelector('input[name="password"]');

  // Wire every demo button to fill the form from its data attributes.
  document.querySelectorAll('.demo-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      // Read the demo credentials stored on the button itself
      const email = btn.dataset.email;
      const password = btn.dataset.password;

      // Drop them into the matching form fields if those fields exist
      if (emailInput)    emailInput.value = email;
      if (passwordInput) passwordInput.value = password;
    });
  });
});
