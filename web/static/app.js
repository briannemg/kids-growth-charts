// ── app.js ────────────────────────────────────────────────────────────────
//
// Stage 2: Frontend wired to the Flask backend.
//
// New JS concepts introduced here:
//   - fetch()              (making HTTP requests to the backend)
//   - async / await        (handling asynchronous operations cleanly)
//   - response.json()      (parsing JSON responses)
//   - populating a <select> dynamically from data

// Global state
var childrenData = {};
var lastResult = null;

// ── 1. UNIT TOGGLES ──────────────────────────────────────────────────────

function setupUnitToggle(toggleId, panelMap) {
  var toggle = document.getElementById(toggleId);
  var buttons = toggle.querySelectorAll(".unit-btn");

  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      buttons.forEach(function (b) {
        b.classList.remove("active");
      });
      btn.classList.add("active");
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

// ── 2. POPULATE CHILDREN DROPDOWN ────────────────────────────────────────
//
// Instead of hardcoding names in the HTML, we fetch them from the backend.
// This is an async function — the `await` keyword pauses it until the
// fetch completes, then continues. Everything else on the page keeps
// working while it waits.

async function loadChildren() {
  try {
    var response = await fetch("/children");
    var data = await response.json();
    var select = document.getElementById("child-select");

    data.children.forEach(function (child) {
      childrenData[child.name] = child; // store the whole object
      var option = document.createElement("option");
      option.value = child.name;
      option.textContent = child.name;
      select.appendChild(option);
    });
  } catch (err) {
    console.error("Could not load children:", err);
  }
}

loadChildren();

// ── 3. UNIT CONVERSION HELPERS ───────────────────────────────────────────

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

// ── 4. READING FORM VALUES ───────────────────────────────────────────────

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
    return isNaN(dec) ? null : decimalLbsToKg(dec);
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

// ── 5. VALIDATION ────────────────────────────────────────────────────────

function validate(child, date, heightCm, weightKg) {
  var errors = [];
  if (!child) errors.push("Please select a child.");
  if (!date) errors.push("Please enter a measurement date.");
  if (heightCm === null && weightKg === null) {
    errors.push("Please enter at least a height or weight.");
  }
  if (heightCm !== null && (heightCm < 30 || heightCm > 250)) {
    errors.push("Height looks out of range — double-check the value.");
  }
  if (weightKg !== null && (weightKg < 0.5 || weightKg > 200)) {
    errors.push("Weight looks out of range — double-check the value.");
  }
  return errors;
}

// ── 6. DISPLAYING RESULTS ────────────────────────────────────────────────

function formatHeight(cm) {
  if (!cm) return "—";
  var totalInches = cm / 2.54;
  var ft = Math.floor(totalInches / 12);
  var inches = (totalInches % 12).toFixed(1);
  return `${ft}′ ${inches}″  (${cm.toFixed(1)} cm)`;
}

function formatWeight(kg) {
  if (!kg) return "—";
  var totalOz = kg / 0.0283495;
  var lbs = Math.floor(totalOz / 16);
  var oz = (totalOz % 16).toFixed(1);
  return `${lbs} lb ${oz} oz  (${kg.toFixed(3)} kg)`;
}

function formatHc(cm) {
  if (!cm) return "—";
  return `${(cm / 2.54).toFixed(1)}″  (${cm.toFixed(1)} cm)`;
}

function ordinal(n) {
  console.log("ordinal received:", n, typeof n);
  n = Math.round(n);
  if (n < 0) return n;
  var mod100 = n % 100;
  var mod10 = n % 10;
  if (mod100 >= 11 && mod100 <= 13) return n + "th";
  if (mod10 === 1) return n + "st";
  if (mod10 === 2) return n + "nd";
  if (mod10 === 3) return n + "rd";
  return n + "th";
}

function formatPercentile(p) {
  if (p === null || p === undefined) return "—";
  return ordinal(p);
}

function resultRow(label, value, percentile) {
  var percentileHtml =
    percentile !== undefined
      ? `<span class="result-percentile">${formatPercentile(percentile)}</span>`
      : "";
  return `
    <div class="result-row">
      <span class="result-label">${label}</span>
      <span class="result-value">${value} ${percentileHtml}</span>
    </div>`;
}

function showError(messageHtml) {
  var result = document.getElementById("result");
  result.className = "result error-box";
  result.innerHTML =
    "<div class='result-title'>⚠️ Please fix the following:</div>" +
    messageHtml;
}

function showLoading() {
  var result = document.getElementById("result");
  result.className = "result";
  result.classList.remove("hidden");
  result.innerHTML = "<div class='result-title'>Calculating…</div>";
}

function showCharts(child, heightCm, weightKg, hcCm) {
  // Remove any existing charts
  var existing = document.getElementById("charts-section");
  if (existing) existing.remove();

  var section = document.createElement("div");
  section.id = "charts-section";

  // Decide which charts to show based on what was submitted
  var charts = [];
  if (heightCm) charts.push({ type: "height", label: "Height-for-Age" });
  if (weightKg) charts.push({ type: "weight", label: "Weight-for-Age" });
  if (hcCm)
    charts.push({
      type: "head_circumference",
      label: "Head Circumference-for-Age",
    });
  if (heightCm && weightKg) charts.push({ type: "bmi", label: "BMI-for-Age" });
  if (heightCm)
    charts.push({ type: "projection", label: "Projected Adult Height" });

  charts.forEach(function (chart) {
    var wrapper = document.createElement("div");
    wrapper.className = "chart-wrapper";

    var label = document.createElement("h3");
    label.className = "chart-label";
    label.textContent = chart.label;

    // The src points directly to the Flask chart endpoint
    var img = document.createElement("img");
    img.className = "chart-img";
    img.alt = chart.label;
    img.src = `/charts/${encodeURIComponent(child)}/${chart.type}`;

    var link = document.createElement("a");
    link.href = `/charts/${encodeURIComponent(child)}/${chart.type}`;
    link.target = "_blank";
    link.appendChild(img);

    wrapper.appendChild(label);
    wrapper.appendChild(link);
    section.appendChild(wrapper);
  });

  // Insert charts after the card
  var card = document.querySelector(".card");
  card.insertAdjacentElement("afterend", section);
}

function showResults(data) {
  // Store for the save button to use
  lastResult = data;

  var result = document.getElementById("result");
  result.className = "result success";

  var dob = childrenData[data.child] ? childrenData[data.child].dob : null;
  var ageDisplay = dob
    ? formatAge(dob, data.date)
    : `${data.age_months} months`;

  result.innerHTML =
    `<div class="result-title">✓ Results for ${data.child}</div>` +
    resultRow("Date", data.date) +
    resultRow("Age", ageDisplay) +
    resultRow("Height", formatHeight(data.height_cm), data.percentiles.height) +
    resultRow("Weight", formatWeight(data.weight_kg), data.percentiles.weight) +
    resultRow(
      "Head circumference",
      formatHc(data.hc_cm),
      data.percentiles.head_circumference,
    ) +
    resultRow(
      "BMI",
      data.bmi ? data.bmi.toFixed(1) : "—",
      data.percentiles.bmi,
    );

  // Show the save button
  document.getElementById("save-wrap").classList.remove("hidden");

  // Show charts below the results
  showCharts(data.child, data.height_cm, data.weight_kg, data.hc_cm);
}

// ── 8. HISTORY TABLE ─────────────────────────────────────────────────────────
//
// Loads and renders the full measurement history for a child.
// Called automatically when a child is selected in the dropdown.

function formatAge(dob, measurementDate) {
  // dob and measurementDate are strings in "YYYY-MM-DD" format
  // We split manually to avoid timezone issues with new Date()
  var dobParts = dob.split("-").map(Number);
  var dateParts = measurementDate.split("-").map(Number);

  var years = dateParts[0] - dobParts[0];
  var months = dateParts[1] - dobParts[1];
  var days = dateParts[2] - dobParts[2];

  // Borrow from months if days is negative
  if (days < 0) {
    months -= 1;
    var borrowYear = dobParts[0] + years;
    var borrowMonth = dobParts[1] + months;
    if (borrowMonth <= 0) {
      borrowMonth += 12;
      borrowYear -= 1;
    }
    // Find how many days are in the borrow month to get the reference point
    var reference = new Date(borrowYear, borrowMonth - 1, dobParts[2]);
    // If the day doesn't exist in that month, Date() rolls over automatically -
    // walk back to the last valid day instead
    if (reference.getMonth() !== borrowMonth - 1) {
      reference = new Date(borrowYear, borrowMonth, 0); // last day of borrowMonth
    }
    var mDate = new Date(dateParts[0], dateParts[1] - 1, dateParts[2]);
    days = Math.round((mDate - reference) / (1000 * 60 * 60 * 24));
  }

  // Borrow from years if months is negative
  if (months < 0) {
    years -= 1;
    months += 12;
  }

  var parts = [];
  if (years > 0) parts.push(years + (years === 1 ? " year" : " years"));
  if (months > 0) parts.push(months + (months === 1 ? " month" : " months"));
  if (days > 0) parts.push(days + (days === 1 ? " day" : " days"));

  return parts.length > 0 ? parts.join(" ") : "0 days";
}

function historyCell(primary, secondary, percentile) {
  if (primary === null || primary === undefined) return "<td>-</td>";
  var html = `<td><div class="td-primary">${primary}</div>`;
  if (secondary) html += `<div class="td-secondary">${secondary}</div>`;
  if (percentile !== null && percentile !== undefined) {
    html += `<div class="td-percentile">${formatPercentile(percentile)}</div>`;
  }
  html += "</td>";
  return html;
}

async function loadHistory(childName) {
  var section = document.getElementById("history-section");
  var subtitle = document.getElementById("history-subtitle");
  var loading = document.getElementById("history-loading");
  var tableWrap = document.getElementById("history-table-wrap");
  var tbody = document.getElementById("history-body");

  // Show the section and reset state
  section.classList.remove("hidden");
  loading.classList.remove("hidden");
  tableWrap.classList.add("hidden");
  subtitle.textContent = childName;
  tbody.innerHTML = "";

  try {
    var response = await fetch(`/history/${encodeURIComponent(childName)}`);
    var data = await response.json();

    data.measurements.forEach(function (m) {
      var ageYears = Math.floor(m.age_months / 12);
      var ageMonths = Math.round(m.age_months % 12);
      var dob = childrenData[childName] ? childrenData[childName].dob : null;
      var ageDisplay = dob ? formatAge(dob, m.date) : `${m.age_months} months`;

      var heightPrimary = m.height_cm ? formatHeight(m.height_cm) : null;
      var weightPrimary = m.weight_kg ? formatWeight(m.weight_kg) : null;
      var hcPrimary = m.hc_cm ? formatHc(m.hc_cm) : null;
      var bmiPrimary = m.bmi ? m.bmi.toFixed(1) : null;

      var row = `<tr>
        <td><div class="td-primary">${m.date}</div></td>
        <td><div class="td-primary">${ageDisplay}</div></td>
        ${historyCell(heightPrimary, null, m.percentiles.height)}
        ${historyCell(weightPrimary, null, m.percentiles.weight)}
        ${historyCell(hcPrimary, null, m.percentiles.head_circumference)}
        ${historyCell(bmiPrimary, null, m.percentiles.bmi)}
      </tr>`;

      tbody.innerHTML += row;
    });

    loading.classList.add("hidden");
    tableWrap.classList.remove("hidden");
  } catch (err) {
    loading.textContent = "Could not load history.";
    console.error(err);
  }
}

// Load history whenever a child is selected in the dropdown
document.getElementById("child-select").addEventListener("change", function () {
  if (this.value) {
    loadHistory(this.value);
  }
});

// ── 7. SUBMIT HANDLER ────────────────────────────────────────────────────
//
// async so it can use await for the fetch call.
// All display functions are defined above, so they're available here.

document
  .getElementById("submit-btn")
  .addEventListener("click", async function () {
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
      return;
    }

    showLoading();

    try {
      var response = await fetch("/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          child: child,
          date: date,
          height_cm: heightCm,
          weight_kg: weightKg,
          hc_cm: hcCm,
        }),
      });

      if (!response.ok) {
        var err = await response.json();
        showError("<div>" + (err.error || "Something went wrong.") + "</div>");
        return;
      }

      var data = await response.json();
      showResults(data);
    } catch (err) {
      showError("<div>Could not reach the server. Is Flask running?</div>");
      console.error(err);
    }
  });

// ── 9. SAVE HANDLER ──────────────────────────────────────────────────────────

document
  .getElementById("save-btn")
  .addEventListener("click", async function () {
    if (!lastResult) return;

    var btn = document.getElementById("save-btn");
    btn.textContent = "Saving…";
    btn.disabled = true;

    try {
      var response = await fetch("/measurements", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          child: lastResult.child,
          date: lastResult.date,
          height_cm: lastResult.height_cm,
          weight_kg: lastResult.weight_kg,
          hc_cm: lastResult.hc_cm,
        }),
      });

      var data = await response.json();

      if (!response.ok) {
        btn.textContent = "Save Measurement";
        btn.disabled = false;
        // Show the error in the result box
        var result = document.getElementById("result");
        result.className = "result error-box";
        result.innerHTML = `<div class="result-title">⚠️ Could not save</div><div>${data.error}</div>`;
        return;
      }

      // Success — update the button and refresh the history table
      btn.textContent = "✓ Saved";
      btn.disabled = true;
      lastResult = null;

      // Refresh the history table to show the new measurement
      loadHistory(document.getElementById("child-select").value);
    } catch (err) {
      btn.textContent = "Save Measurement";
      btn.disabled = false;
      console.error(err);
    }
  });
