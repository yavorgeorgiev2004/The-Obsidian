/*
 * Maintenance form behaviour.
 * Pre-fills the expected-ready date from the selected category's default
 * number of days, and updates it when the category changes. Staff can
 * still override the date by hand. External file; no inline script.
 */
document.addEventListener('DOMContentLoaded', function () {

  // The form, the category select and the date input
  const form = document.getElementById('maintenanceForm');
  if (!form) return;
  const categorySelect = document.getElementById('categorySelect');
  const expectedReady = document.getElementById('expectedReady');
  if (!categorySelect || !expectedReady) return;

  // Read today's date, supplied by the form as a data attribute
  const today = new Date(form.dataset.today);

  // Set the expected-ready field to today plus the category's default days
  function applyDefault() {
    // Read the default day count from the selected option
    const option = categorySelect.options[categorySelect.selectedIndex];
    const days = parseInt(option.dataset.days, 10) || 1;

    // Add those days to today and format as YYYY-MM-DD for the date input
    const target = new Date(today);
    target.setDate(target.getDate() + days);
    const iso = target.toISOString().slice(0, 10);
    expectedReady.value = iso;
  }

  // Update the date whenever the category changes
  categorySelect.addEventListener('change', applyDefault);

  // Set the initial default on load
  applyDefault();
});
