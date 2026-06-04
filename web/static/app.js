// ── app.js ────────────────────────────────────────────────────────────────
//
// Stage 2: Frontend wired to the Flask backend.
//
// New JS concepts introduced here:
//   - fetch()              (making HTTP requests to the backend)
//   - async / await        (handling asynchronous operations cleanly)
//   - response.json()      (parsing JSON responses)
//   - populating a <select> dynamically from data

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

function formatPercentile(p) {
  if (p === null || p === undefined) return "—";
  return `${p}th percentile`;
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
  var result = document.getElementById("result");
  result.className = "result success";

  var ageYears = Math.floor(data.age_months / 12);
  var ageMonths = Math.round(data.age_months % 12);
  var ageDisplay =
    ageYears > 0
      ? `${ageYears}y ${ageMonths}m (${data.age_months} months)`
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

  // Show charts below the results
  showCharts(data.child, data.height_cm, data.weight_kg, data.hc_cm);
}

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
