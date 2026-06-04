// ── app.js ────────────────────────────────────────────────────────────────
//
// Stage 1: Pure JS form behavior.
// No backend yet - this just reads the form, validates it,
// and displays a summary of what was entered.
//
// JS concepts practiced here:
//   - querySelector / getElementById  (selecting elements)
//   - addEventListener                (responding to clicks)
//   - classList.add/remove            (showing/hiding elements)
//   - value / parseFloat              (reading input values)
//   - template literals               (building strings with ${ })
//   - basic validation                (checking for empty/invalid inputs)
//   - dataset                         (reading data-* attributes from HTML)

// ── 1. UNIT TOGGLES ──────────────────────────────────────────────────────
//
// Each section has a set of unit buttons and a matching set up input panels.
// When a button is clicked:
//   - Mark it active (for CSS styling)
//   - Show the matching input panel
//   - Hide all the others
//
// panelMap is an object that maps each data-unit value to an element ID.
// This replaces a long chain of if/else checks.

function setupUnitToggle(toggleId, panelMap) {
  var toggle = document.getElementById(toggleId);
  var buttons = toggle.querySelectorAll(".unit-btn");

  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      // Deactivate all buttons
      buttons.forEach(function (b) {
        b.classList.remove("active");
      });
      // Activate the clicked one
      btn.classList.add("active");

      // Hide all panels, then show the one that matches this button
      Object.values(panelMap).forEach(function (panelId) {
        document.getElementById(panelId).classList.add("hidden");
      });
      document
        .getElementById(panelMap[btn.dataset.unit])
        .classList.remove("hidden");
    });
  });

  // Initialize: hide all panels, then show the default active one
  Object.values(panelMap).forEach(function (panelId) {
    document.getElementById(panelId).classList.add("hidden");
  });
  var defaultBtn = toggle.querySelector(".unit-btn.active");
  document
    .getElementById(panelMap[defaultBtn.dataset.unit])
    .classList.remove("hidden");
}

// Wire up all three toggles.
// The panelMap keys must match the data-unit values in the HTML exactly.
setupUnitToggle("height-toggle", {
  ft_in: "height-ft-in",
  dec_in: "height-dec-in",
  cm: "height-cm-wrap",
});

setupUnitToggle("weight-toggle", {
  lbs_oz: "weight-lbs-oz",
  dec_lbs: "weight-dec-lbs-wrap",
  kg: "weight-kg-wrap",
  g: "weight-g-wrap",
});

setupUnitToggle("hc-toggle", {
  dec_in: "hc-dec-in",
  cm: "hc-cm-wrap",
});

// ── 2. UNIT CONVERSION HELPERS ───────────────────────────────────────────
//
// Your Python codes stores everything in metric (cm, kg).
// These match the conversion functions in growth_charts/units.py.

function feetInchesToCm(feet, inches) {
  return (feet * 12 + inches) * 2.54;
}

function inchesToCm(inches) {
  return inches * 2.54;
}

function lbsOzToKg(lbs, oz) {
  return (lbs * 16 + oz) * 0.0283495;
}

function decimalLbsToKg(lbs) {
  return lbs * 0.453592;
}

function gramsToKg(g) {
  return g / 1000;
}

// ── 3. READING FORM VALUES ───────────────────────────────────────────────
//
// Each function finds the currently active unit panel and reads
// the right input(s) from it, returning a value in metric.
// Returns null if the field is empty.

function getActiveUnit(toggleId) {
  var activeBtn = document.querySelector("#" + toggleId + " .unit-btn.active");
  return activeBtn ? activeBtn.dataset.unit : null;
}

function getHeightCm() {
  var unit = getActiveUnit("height-toggle");

  if (unit === "ft_in") {
    var ft = parseFloat(document.getElementById("height-ft").value) || 0;
    var inches = parseFloat(document.getElementById("height-in").value) || 0;
    if (ft === 0 && inches === 0) return null;
    return feetInchesToCm(ft, inches);
  }
  if (unit === "dec_in") {
    var dec = parseFloat(document.getElementById("height-dec").value);
    return isNaN(dec) ? null : inchesToCm(dec);
  }
  if (unit === "cm") {
    var cm = parseFloat(document.getElementById("height-cm").value);
    return isNaN(cm) ? null : cm;
  }
  return null;
}

function getWeightKg() {
  var unit = getActiveUnit("weight-toggle");

  if (unit === "lbs_oz") {
    var lbs = parseFloat(document.getElementById("weight-lbs").value) || 0;
    var oz = parseFloat(document.getElementById("weight-oz").value) || 0;
    if (lbs === 0 && oz === 0) return null;
    return lbsOzToKg(lbs, oz);
  }
  if (unit === "dec_lbs") {
    var dec = parseFloat(document.getElementById("weight-dec-lbs").value);
    return isNaN(dec) ? Null : decimalLbsToKg(dec);
  }
  if (unit === "kg") {
    var kg = parseFloat(document.getElementById("weight-kg").value);
    return isNaN(kg) ? null : kg;
  }
  if (unit === "g") {
    var g = parseFloat(document.getElementById("weight-g").value);
    return isNaN(g) ? null : gramsToKg(g);
  }
  return null;
}

function getHcCm() {
  var unit = getActiveUnit("hc-toggle");

  if (unit === "dec_in") {
    var inches = parseFloat(document.getElementById("hc-in").value);
    return isNaN(inches) ? null : inchesToCm(inches);
  }
  if (unit === "cm") {
    var cm = parseFloat(document.getElementById("hc-cm").value);
    return isNaN(cm) ? null : cm;
  }
  return null;
}

// ── 4. VALIDATION ────────────────────────────────────────────────────────
//
// Returns an array of error message strings.
// An empty array means everything is valid.

function validate(child, date, heightCm, weightKg) {
  var errors = [];

  if (!child) {
    errors.push("Please select a child.");
  }
  if (!date) {
    errors.push("Please enter a measurement date.");
  }
  if (heightCm === null && weightKg === null) {
    errors.push("Please enter at least a height or weight.");
  }
  if (heightCm !== null && (heightCm < 30 || heightCm > 250)) {
    errors.push("Height looks out of range - double-check the value.");
  }
  if (weightKg !== null && (weightKg < 0.5 || weightKg > 200)) {
    errors.push("Weight looks out of range - double-check the value.");
  }

  return errors;
}

// ── 5. DISPLAYING RESULTS ────────────────────────────────────────────────
//
// Build a friendly summary of the collected values and show it below the form.
// Both imperial and metric are shown so the user can sanity-check the conversion.

function formatHeight(cm) {
  if (cm === null) return "-";
  var totalInches = cm / 2.54;
  var ft = Math.floor(totalInches / 12);
  var inches = (totalInches % 12).toFixed(1);
  return `${ft} ft ${inches} in  (${cm.toFixed(1)} cm)`;
}

function formatWeight(kg) {
  if (kg === null) return "-";
  var totalOz = kg / 0.0283495;
  var lbs = Math.floor(totalOz / 16);
  var oz = (totalOz % 16).toFixed(1);
  return `${lbs} lb ${oz} oz  (${kg.toFixed(3)} kg)`;
}

function formatHc(cm) {
  if (cm === null) return "-";
  return `${(cm / 2.54).toFixed(1)} in  (${cm.toFixed(1)} cm)`;
}

function resultRow(label, value) {
  return `
      <div class="result-row">
        <span class="result-label">${label}</span>
        <span class="result-value">${value}</span>
      </div>`;
}

function showError(messageHtml) {
  var result = document.getElementById("result");
  result.className = "result error-box";
  result.innerHTML =
    "<div class='result-title'>⚠️ Please fix the following:</div>" +
    messageHTML;
}

function showSuccess(child, date, heightCm, weightKg, hcCm) {
  var result = document.getElementById("result");
  result.className = "result success";
  result.innerHTML =
    "<div class='result-title'>✓ Measurement ready to save</div>" +
    resultRow("Child", child) +
    resultRow("Date", date) +
    resultRow("Height", formatHeight(heightCm)) +
    resultRow("Weight", formatWeight(weightKg)) +
    resultRow("Head circumference", formatHc(hcCm));
}

// ── 6. SUBMIT HANDLER ────────────────────────────────────────────────────
//
// Ties everything together when the button is clicked.

document.getElementById("submit-btn").addEventListener("click", function () {
  var child = document.getElementById("child-select").value;
  var date = document.getElementById("measure-date").value;
  var heightCm = getHeightCm();
  var weightKg = getWeightKg();
  var hcCm = getHcCm();

  var errors = validate(child, date, heightCm, weightKg);

  var result = document.getElementById("result");
  result.classList.remove("hidden");

  if (errors.length > 0) {
    var errorList = errors
      .map(function (e) {
        return "<div>• " + e + "</div>";
      })
      .join("");
    showError(errorList);
  } else {
    showSuccess(child, date, heightCm, weightKg, hcCm);
  }
});
