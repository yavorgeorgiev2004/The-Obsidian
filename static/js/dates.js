/*
 * Date picker helper for the rooms availability search.
 * Keeps check-out after check-in: when the guest picks a check-in date,
 * the check-out is nudged to the following day if it is not already later,
 * and the check-out input's minimum is kept one day past check-in. This
 * stops an invalid range being submitted. External file; no inline script.
 */
document.addEventListener('DOMContentLoaded', function () {

  // The two date inputs in the rooms filter, if present on this page
  const checkIn = document.getElementById('roomCheckIn');
  const checkOut = document.getElementById('roomCheckOut');
  if (!checkIn || !checkOut) return;

  // Return a YYYY-MM-DD string for the day after the given date string
  function dayAfter(dateStr) {
    const d = new Date(dateStr);
    d.setDate(d.getDate() + 1);
    return d.toISOString().slice(0, 10);
  }

  // Keep check-out valid relative to check-in
  function syncCheckout() {
    if (!checkIn.value) return;
    // Check-out can never be on or before check-in
    const minOut = dayAfter(checkIn.value);
    checkOut.min = minOut;
    // If the current check-out is not after check-in, move it to the next day
    if (!checkOut.value || checkOut.value <= checkIn.value) {
      checkOut.value = minOut;
    }
  }

  // Run when check-in changes and once on load
  checkIn.addEventListener('change', syncCheckout);
  syncCheckout();
});
