/*
 * The Obsidian — booking form interactivity.
 * Handles date constraints, package selected-states and the live total.
 * All behaviour lives here externally; no inline JS in the templates.
 */
document.addEventListener('DOMContentLoaded', function () {

  // Keep check-out at least one day after check-in on any date pair
  const checkIn  = document.querySelector('input[name="check_in"]');
  const checkOut = document.querySelector('input[name="check_out"]');
  if (checkIn && checkOut) {
    // When check-in changes, push check-out forward if it is now invalid
    checkIn.addEventListener('change', function () {
      checkOut.min = checkIn.value;
      if (checkOut.value <= checkIn.value) {
        const next = new Date(checkIn.value);
        next.setDate(next.getDate() + 1);
        checkOut.value = next.toISOString().split('T')[0];
      }
    });
  }

  // Package selection — toggle the selected class and update the live total
  const grid = document.getElementById('packageGrid');
  const liveTotal = document.getElementById('liveTotal');

  if (grid) {
    // Recalculate the running total from every checked package
    function recalculate() {
      let total = 0;
      // Loop over each package card and add the checked ones
      grid.querySelectorAll('.pkg-select').forEach(function (card) {
        const input = card.querySelector('input[type="checkbox"]');
        const price = parseFloat(card.dataset.price) || 0;
        if (input.checked) {
          card.classList.add('selected');
          total += price;
        } else {
          card.classList.remove('selected');
        }
      });
      // Update the live total display if present
      if (liveTotal) {
        liveTotal.textContent = '£' + total.toLocaleString();
      }
    }

    // Recalculate whenever a package checkbox changes
    grid.addEventListener('change', recalculate);

    // Run once on load so pre-checked packages show correctly
    recalculate();
  }
});

/*
 * EDIT PAGE — live total preview.
 * On the edit-booking page this recalculates the new totals as the guest
 * changes the room type, dates or packages, and shows whether a top-up is
 * due or the balance will be reduced. This is a preview only; the
 * authoritative figure is recalculated on the server when the form is saved.
 */
document.addEventListener('DOMContentLoaded', function () {

  // Only run on the edit page, identified by the edit form element
  const form = document.getElementById('editForm');
  if (!form) return;

  // Read the fixed values the calculation needs from the form's data attributes
  const amountPaid = parseFloat(form.dataset.amountPaid) || 0;
  const depositPct = parseFloat(form.dataset.depositPct) || 25;

  // Grab the inputs that affect the total
  const typeSelect = document.getElementById('roomTypeSelect');
  const checkIn    = document.getElementById('editCheckIn');
  const checkOut   = document.getElementById('editCheckOut');
  const pkgGrid    = document.getElementById('packageGrid');

  // Grab the live display elements to update
  const elNights   = document.getElementById('liveNights');
  const elRoom     = document.getElementById('liveRoom');
  const elPackages = document.getElementById('livePackages');
  const elTotal    = document.getElementById('liveTotal');
  const elOutLabel = document.getElementById('liveOutcomeLabel');
  const elOutcome  = document.getElementById('liveOutcome');
  const elNote     = document.getElementById('liveNote');

  // Format a number as a pound amount with two decimals
  function gbp(n) {
    return '£' + n.toFixed(2);
  }

  // Work out how many nights lie between the two chosen dates
  function nightsBetween() {
    // Guard against empty or invalid dates
    if (!checkIn.value || !checkOut.value) return 0;
    const inD  = new Date(checkIn.value);
    const outD = new Date(checkOut.value);
    const diff = (outD - inD) / (1000 * 60 * 60 * 24);
    // Never return a negative number of nights
    return diff > 0 ? Math.round(diff) : 0;
  }

  // Recalculate everything and update the live summary
  function recalc() {
    // Room cost = nightly price of the chosen type times the nights
    const nights = nightsBetween();
    const selectedOption = typeSelect.options[typeSelect.selectedIndex];
    const pricePerNight = parseFloat(selectedOption.dataset.price) || 0;
    const roomTotal = pricePerNight * nights;

    // Packages cost = sum of every checked package's price
    let pkgTotal = 0;
    pkgGrid.querySelectorAll('.pkg-select').forEach(function (card) {
      const input = card.querySelector('input[type="checkbox"]');
      if (input.checked) pkgTotal += parseFloat(card.dataset.price) || 0;
    });

    // Grand total is the two combined
    const grandTotal = roomTotal + pkgTotal;

    // Update the room, packages and total rows
    elNights.textContent = nights ? '(' + nights + ' night' + (nights === 1 ? '' : 's') + ')' : '';
    elRoom.textContent     = gbp(roomTotal);
    elPackages.textContent = gbp(pkgTotal);
    elTotal.textContent    = gbp(grandTotal);

    // Decide the outcome relative to what has already been paid.
    // The required deposit is a percentage of the new grand total.
    const requiredDeposit = grandTotal * depositPct / 100;

    if (requiredDeposit > amountPaid) {
      // More deposit is owed — a top-up will be charged on saving
      const topUp = requiredDeposit - amountPaid;
      elOutLabel.textContent = 'Top-up due on saving';
      elOutcome.textContent  = gbp(topUp);
      elOutcome.className     = 'value owed';
      elNote.textContent = 'Your new total is higher, so a top-up of '
        + gbp(topUp) + ' will be taken when you save.';
    } else {
      // Enough is already paid — show the remaining balance owed at the hotel,
      // which the surplus has reduced (no cash refund is issued).
      const balance = grandTotal - amountPaid;
      elOutLabel.textContent = 'Balance owed at hotel';
      elOutcome.textContent  = gbp(balance > 0 ? balance : 0);
      elOutcome.className     = 'value owed';
      // If they have overpaid against the new lower total, say so plainly
      if (amountPaid > grandTotal) {
        elNote.textContent = 'Your new total is lower. You have paid '
          + gbp(amountPaid - grandTotal) + ' more than the new total, '
          + 'which clears your balance — no refund is issued.';
      } else {
        elNote.textContent = 'Your deposit already covers the required amount. '
          + 'The remaining balance is payable at the hotel.';
      }
    }
  }

  // Grab the live availability note element and the booking id to exclude
  const availNote = document.getElementById('availabilityNote');
  const excludeId = availNote ? availNote.dataset.exclude : null;
  const saveBtn   = form.querySelector('button[type="submit"]');

  // Ask the server how many rooms of the chosen type are free for the
  // chosen dates, and show the answer live before the guest saves.
  function checkAvailability() {
    // Need a note element, a type and both dates to ask
    if (!availNote) return;
    const type = typeSelect.value;
    const ci = checkIn.value;
    const co = checkOut.value;
    if (!type || !ci || !co) return;

    // Build the query and call the JSON availability endpoint
    const url = '/bookings/availability/?room_type=' + encodeURIComponent(type)
      + '&check_in=' + ci + '&check_out=' + co
      + (excludeId ? '&exclude=' + excludeId : '');

    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        // Show a clear message based on how many are free
        if (data.status === 'available') {
          availNote.textContent = '◆ ' + data.available + ' of ' + data.total + ' available for these dates';
          availNote.style.color = '#4caf50';
          if (saveBtn) saveBtn.disabled = false;
        } else if (data.status === 'last-one') {
          availNote.textContent = '◆ Only 1 left for these dates';
          availNote.style.color = 'var(--gold)';
          if (saveBtn) saveBtn.disabled = false;
        } else if (data.status === 'full') {
          availNote.textContent = '◆ No rooms of this type are free for these dates — choose another type or dates';
          availNote.style.color = '#ef5350';
          // Block saving into a fully booked type
          if (saveBtn) saveBtn.disabled = true;
        } else {
          availNote.textContent = '';
        }
      })
      .catch(function () {
        // On any network error, clear the note rather than mislead
        availNote.textContent = '';
      });
  }

  // Recalculate whenever any relevant field changes
  typeSelect.addEventListener('change', function () { recalc(); checkAvailability(); });
  checkIn.addEventListener('change', function () { recalc(); checkAvailability(); });
  checkOut.addEventListener('change', function () { recalc(); checkAvailability(); });
  pkgGrid.addEventListener('change', recalc);

  // Run once on load so the summary and availability are correct upfront
  recalc();
  checkAvailability();
});
