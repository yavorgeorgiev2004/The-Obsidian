/*
 * Relocation decision page behaviour.
 * Shows the new-date inputs only when the guest selects the reschedule
 * option, and keeps them hidden otherwise. External file; the template
 * carries no inline script.
 */
document.addEventListener('DOMContentLoaded', function () {

  // The reschedule date fields and the set of choice radios
  const dateFields = document.getElementById('rescheduleDates');
  const radios = document.querySelectorAll('input[name="choice"]');
  if (!dateFields || radios.length === 0) return;

  // Show the date inputs only when the reschedule option is selected
  function updateDateVisibility() {
    let rescheduleSelected = false;
    // Find which radio is currently checked
    radios.forEach(function (r) {
      if (r.checked && r.value === 'reschedule') rescheduleSelected = true;
    });
    dateFields.style.display = rescheduleSelected ? 'flex' : 'none';
  }

  // React to any change in the chosen option
  radios.forEach(function (r) {
    r.addEventListener('change', updateDateVisibility);
  });

  // Set the correct initial state on load
  updateDateVisibility();
});
