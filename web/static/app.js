// ── app.js ────────────────────────────────────────────────────────────────
//
// Growth Charts — frontend logic
//
// JS concepts used:
//   - fetch() / async / await     (HTTP requests to Flask backend)
//   - DOM manipulation            (querySelector, createElement, classList)
//   - Event listeners             (click, change)
//   - Template literals           (${} strings)
//   - Modules pattern             (functions grouped by responsibility)

// ── GLOBAL STATE ─────────────────────────────────────────────────────────────

var childrenData = {}; // keyed by name, populated from /children
var lastResult = null; // most recent /calculate response
var formState = "idle"; // "idle" | "calculated"
// States:
//   idle       — form is empty or reset, button says "Calculate"
//   calculated — /calculate succeeded, button says "Save Measurement"

// ── 1. UNIT TOGGLES ──────────────────────────────────────────────────────────

function setupUnitToggle(toggleId, panelMap) {
  var toggle = document.getElementById(toggleId);
  var buttons = toggle.querySelectorAll(".unit-btn");

  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      buttons.forEach(function (b) {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      Object.values(panelMap).forEach(function (id) {
        document.getElementById(id).classList.add("hidden");
      });
      document
        .getElementById(panelMap[btn.dataset.unit])
        .classList.remove("hidden");
    });
  });

  // Initialize: hide all, show the active one
  Object.values(panelMap).forEach(function (id) {
    document.getElementById(id).classList.add("hidden");
  });
  var defaultBtn = toggle.querySelector(".unit-btn.active");
  document
    .getElementById(panelMap[defaultBtn.dataset.unit])
    .classList.remove("hidden");
}

// Main form toggles
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

// Modal toggles
setupUnitToggle("modal-height-toggle", {
  ft_in: "modal-height-ft-in",
  dec_in: "modal-height-dec-in",
  cm: "modal-height-cm-wrap",
});
setupUnitToggle("modal-weight-toggle", {
  lbs_oz: "modal-weight-lbs-oz",
  dec_lbs: "modal-weight-dec-lbs-wrap",
  kg: "modal-weight-kg-wrap",
  g: "modal-weight-g-wrap",
});
setupUnitToggle("modal-hc-toggle", {
  dec_in: "modal-hc-dec-in",
  cm: "modal-hc-cm-wrap",
});

// ── 2. LOAD CHILDREN ─────────────────────────────────────────────────────────

async function loadChildren() {
  try {
    var response = await fetch("/children");
    var data = await response.json();
    var select = document.getElementById("child-select");

    data.children.forEach(function (child) {
      childrenData[child.name] = child;
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

// ── 3. UNIT CONVERSION HELPERS ───────────────────────────────────────────────

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
function round1(n) {
  return Math.round(n * 10) / 10;
}

// ── 4. READING FORM VALUES ───────────────────────────────────────────────────

function getActiveUnit(toggleId) {
  var btn = document.querySelector("#" + toggleId + " .unit-btn.active");
  return btn ? btn.dataset.unit : null;
}

function readHeightCm(prefix) {
  // prefix is "" for main form, "modal-" for modal
  var unit = getActiveUnit(prefix + "height-toggle");
  if (unit === "ft_in") {
    var ft =
      parseFloat(document.getElementById(prefix + "height-ft").value) || 0;
    var ins =
      parseFloat(document.getElementById(prefix + "height-in").value) || 0;
    return ft === 0 && ins === 0 ? null : feetInchesToCm(ft, ins);
  }
  if (unit === "dec_in") {
    var d = parseFloat(document.getElementById(prefix + "height-dec").value);
    return isNaN(d) ? null : inchesToCm(d);
  }
  if (unit === "cm") {
    var cm = parseFloat(document.getElementById(prefix + "height-cm").value);
    return isNaN(cm) ? null : cm;
  }
  return null;
}

function readWeightKg(prefix) {
  var unit = getActiveUnit(prefix + "weight-toggle");
  if (unit === "lbs_oz") {
    var lbs =
      parseFloat(document.getElementById(prefix + "weight-lbs").value) || 0;
    var oz =
      parseFloat(document.getElementById(prefix + "weight-oz").value) || 0;
    return lbs === 0 && oz === 0 ? null : lbsOzToKg(lbs, oz);
  }
  if (unit === "dec_lbs") {
    var d = parseFloat(
      document.getElementById(prefix + "weight-dec-lbs").value,
    );
    return isNaN(d) ? null : decimalLbsToKg(d);
  }
  if (unit === "kg") {
    var kg = parseFloat(document.getElementById(prefix + "weight-kg").value);
    return isNaN(kg) ? null : kg;
  }
  if (unit === "g") {
    var g = parseFloat(document.getElementById(prefix + "weight-g").value);
    return isNaN(g) ? null : gramsToKg(g);
  }
  return null;
}

function readHcCm(prefix) {
  var unit = getActiveUnit(prefix + "hc-toggle");
  if (unit === "dec_in") {
    var ins = parseFloat(document.getElementById(prefix + "hc-in").value);
    return isNaN(ins) ? null : inchesToCm(ins);
  }
  if (unit === "cm") {
    var cm = parseFloat(document.getElementById(prefix + "hc-cm").value);
    return isNaN(cm) ? null : cm;
  }
  return null;
}

// Convenience wrappers for main form
function getHeightCm() {
  return readHeightCm("");
}
function getWeightKg() {
  return readWeightKg("");
}
function getHcCm() {
  return readHcCm("");
}

// ── 5. VALIDATION ────────────────────────────────────────────────────────────

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

// ── 6. FORMATTING HELPERS ────────────────────────────────────────────────────

// Full format — used in the results box (imperial + metric)
function formatHeight(cm) {
  if (!cm) return "—";
  var totalInches = cm / 2.54;
  var ft = Math.floor(totalInches / 12);
  var ins = (totalInches % 12).toFixed(1);
  return `${ft} ft ${ins} in  (${cm.toFixed(1)} cm)`;
}

function formatWeight(kg) {
  if (!kg) return "—";
  var totalOz = kg / 0.0283495;
  var lbs = Math.floor(totalOz / 16);
  var oz = (totalOz % 16).toFixed(1);
  return `${lbs} lb ${oz} oz  (${kg.toFixed(1)} kg)`;
}

function formatHc(cm) {
  if (!cm) return "—";
  return `${(cm / 2.54).toFixed(1)} in  (${cm.toFixed(1)} cm)`;
}

// Short format — used in the history table (imperial only, no metric)
function formatHeightShort(cm) {
  if (!cm) return null;
  var totalInches = cm / 2.54;
  var ft = Math.floor(totalInches / 12);
  var ins = (totalInches % 12).toFixed(1);
  return `${ft} ft ${ins} in`;
}

function formatWeightShort(kg) {
  if (!kg) return null;
  var totalOz = kg / 0.0283495;
  var lbs = Math.floor(totalOz / 16);
  var oz = (totalOz % 16).toFixed(1);
  return `${lbs} lb ${oz} oz`;
}

function formatHcShort(cm) {
  if (!cm) return null;
  return `${(cm / 2.54).toFixed(1)} in`;
}

function ordinal(n) {
  n = Math.round(n);
  if (n < 0) return String(n);
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

function formatAge(dob, measurementDate) {
  var dobParts = dob.split("-").map(Number);
  var dateParts = measurementDate.split("-").map(Number);

  var years = dateParts[0] - dobParts[0];
  var months = dateParts[1] - dobParts[1];
  var days = dateParts[2] - dobParts[2];

  if (days < 0) {
    months -= 1;
    var borrowYear = dobParts[0] + years;
    var borrowMonth = dobParts[1] + months;
    if (borrowMonth <= 0) {
      borrowMonth += 12;
      borrowYear -= 1;
    }
    var reference = new Date(borrowYear, borrowMonth - 1, dobParts[2]);
    if (reference.getMonth() !== borrowMonth - 1) {
      reference = new Date(borrowYear, borrowMonth, 0);
    }
    var mDate = new Date(dateParts[0], dateParts[1] - 1, dateParts[2]);
    days = Math.round((mDate - reference) / (1000 * 60 * 60 * 24));
  }
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

// ── 7. RESULT DISPLAY ────────────────────────────────────────────────────────

function resultRow(label, value, percentile) {
  var pctHtml =
    percentile !== undefined
      ? `<span class="result-percentile">${formatPercentile(percentile)}</span>`
      : "";
  return `
    <div class="result-row">
      <span class="result-label">${label}</span>
      <span class="result-value">${value} ${pctHtml}</span>
    </div>`;
}

function showError(messageHtml) {
  var result = document.getElementById("result");
  result.className = "result error-box";
  result.classList.remove("hidden");
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

function showResults(data) {
  lastResult = data;
  setFormState("calculated");

  var result = document.getElementById("result");
  result.className = "result success";
  result.classList.remove("hidden");

  var dob = childrenData[data.child] ? childrenData[data.child].dob : null;
  var ageDisplay = dob
    ? formatAge(dob, data.date)
    : `${data.age_months} months`;

  result.innerHTML =
    `<div class="result-title">Results for ${data.child}</div>` +
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

  // Pass the date so the chart can preview the unsaved measurement
  showCharts(data.child, data.height_cm, data.weight_kg, data.hc_cm, data.date);
}

function showCharts(child, heightCm, weightKg, hcCm, date) {
  var existing = document.getElementById("charts-section");
  if (existing) existing.remove();

  var section = document.createElement("div");
  section.id = "charts-section";

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

  // Build query string with measurement values for preview injection
  // and a cache-busting timestamp so the browser always fetches fresh images
  var params = new URLSearchParams();
  if (date) params.set("date", date);
  if (heightCm) params.set("height_cm", heightCm);
  if (weightKg) params.set("weight_kg", weightKg);
  if (hcCm) params.set("hc_cm", hcCm);
  params.set("t", Date.now());
  var queryString = params.toString();

  charts.forEach(function (chart) {
    var wrapper = document.createElement("div");
    wrapper.className = "chart-wrapper";

    var label = document.createElement("h3");
    label.className = "chart-label";
    label.textContent = chart.label;

    var url = `/charts/${encodeURIComponent(child)}/${chart.type}?${queryString}`;

    var img = document.createElement("img");
    img.className = "chart-img";
    img.alt = chart.label;
    img.src = url;

    var link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.appendChild(img);

    wrapper.appendChild(label);
    wrapper.appendChild(link);
    section.appendChild(wrapper);
  });

  document.querySelector(".card").insertAdjacentElement("afterend", section);
}

// ── 8. FORM STATE MACHINE ────────────────────────────────────────────────────
//
// The single submit button changes label and behavior based on formState:
//   idle        → label "Calculate",        click runs /calculate
//   calculated  → label "Save Measurement", click runs /measurements POST

function setFormState(state) {
  formState = state;
  var btn = document.getElementById("submit-btn");
  if (state === "idle") {
    btn.textContent = "Calculate";
    btn.disabled = false;
  } else if (state === "calculated") {
    btn.textContent = "Save Measurement";
    btn.disabled = false;
  } else if (state === "saving") {
    btn.textContent = "Saving…";
    btn.disabled = true;
  } else if (state === "saved") {
    btn.textContent = "✓ Saved";
    btn.disabled = true;
  }
}

// Reset the main form back to a clean idle state
function resetForm() {
  document.getElementById("measure-date").value = "";
  document.getElementById("height-ft").value = "";
  document.getElementById("height-in").value = "";
  document.getElementById("height-dec").value = "";
  document.getElementById("height-cm").value = "";
  document.getElementById("weight-lbs").value = "";
  document.getElementById("weight-oz").value = "";
  document.getElementById("weight-dec-lbs").value = "";
  document.getElementById("weight-kg").value = "";
  document.getElementById("weight-g").value = "";
  document.getElementById("hc-in").value = "";
  document.getElementById("hc-cm").value = "";
  document.getElementById("result").classList.add("hidden");
  var existing = document.getElementById("charts-section");
  if (existing) existing.remove();
  lastResult = null;
  setFormState("idle");
}

// Reset form state when child selection changes
document.getElementById("child-select").addEventListener("change", function () {
  resetForm();
  if (this.value) loadHistory(this.value);
});

// ── 9. SUBMIT HANDLER ────────────────────────────────────────────────────────

document
  .getElementById("submit-btn")
  .addEventListener("click", async function () {
    var child = document.getElementById("child-select").value;
    var date = document.getElementById("measure-date").value;
    var heightCm = getHeightCm();
    var weightKg = getWeightKg();
    var hcCm = getHcCm();

    // ── "Save Measurement" state: persist the last calculated result ──────────
    if (formState === "calculated" && lastResult) {
      setFormState("saving");
      try {
        var saveResp = await fetch("/measurements", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            child: lastResult.child,
            date: lastResult.date,
            height_cm: lastResult.height_cm
              ? round1(lastResult.height_cm)
              : null,
            weight_kg: lastResult.weight_kg
              ? round1(lastResult.weight_kg)
              : null,
            hc_cm: lastResult.hc_cm ? round1(lastResult.hc_cm) : null,
          }),
        });
        var saveData = await saveResp.json();
        if (!saveResp.ok) {
          setFormState("calculated");
          showError("<div>" + (saveData.error || "Could not save.") + "</div>");
          return;
        }
        setFormState("saved");
        loadHistory(lastResult.child);
      } catch (err) {
        setFormState("calculated");
        showError("<div>Could not reach the server.</div>");
        console.error(err);
      }
      return;
    }

    // ── "Calculate" state: run /calculate ────────────────────────────────────
    var errors = validate(child, date, heightCm, weightKg);
    if (errors.length > 0) {
      showError(
        errors
          .map(function (e) {
            return "<div>• " + e + "</div>";
          })
          .join(""),
      );
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
          height_cm: heightCm ? round1(heightCm) : null,
          weight_kg: weightKg ? round1(weightKg) : null,
          hc_cm: hcCm ? round1(hcCm) : null,
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

// ── 10. HISTORY TABLE ────────────────────────────────────────────────────────

function historyCell(primary, secondary, percentile) {
  if (primary === null || primary === undefined) return "<td>—</td>";
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

  section.classList.remove("hidden");
  loading.classList.remove("hidden");
  tableWrap.classList.add("hidden");
  subtitle.textContent = childName;
  tbody.innerHTML = "";

  try {
    var response = await fetch(`/history/${encodeURIComponent(childName)}`);
    var data = await response.json();
    var dob = childrenData[childName] ? childrenData[childName].dob : null;

    data.measurements.forEach(function (m) {
      var ageDisplay = dob ? formatAge(dob, m.date) : `${m.age_months} months`;
      // Use short (imperial only) format in the table to keep columns narrow
      var heightPrimary = formatHeightShort(m.height_cm);
      var weightPrimary = formatWeightShort(m.weight_kg);
      var hcPrimary = formatHcShort(m.hc_cm);
      var bmiPrimary = m.bmi ? m.bmi.toFixed(1) : null;

      tbody.innerHTML += `<tr>
        <td><div class="td-primary">${m.date}</div></td>
        <td><div class="td-primary">${ageDisplay}</div></td>
        ${historyCell(heightPrimary, null, m.percentiles.height)}
        ${historyCell(weightPrimary, null, m.percentiles.weight)}
        ${historyCell(hcPrimary, null, m.percentiles.head_circumference)}
        ${historyCell(bmiPrimary, null, m.percentiles.bmi)}
        <td>
          <button class="btn-edit" data-date="${m.date}" data-child="${childName}">Edit</button>
          <button class="btn-delete" data-date="${m.date}" data-child="${childName}">Delete</button>
        </td>
      </tr>`;
    });

    loading.classList.add("hidden");
    tableWrap.classList.remove("hidden");

    document.querySelectorAll(".btn-edit").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openEditModal(btn.dataset.child, btn.dataset.date);
      });
    });
    document.querySelectorAll(".btn-delete").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openDeleteModal(btn.dataset.child, btn.dataset.date);
      });
    });
  } catch (err) {
    loading.textContent = "Could not load history.";
    console.error(err);
  }
}

// ── 11. EDIT MODAL ───────────────────────────────────────────────────────────

function openModal() {
  document.getElementById("modal-overlay").classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeModal() {
  document.getElementById("modal-overlay").classList.add("hidden");
  document.getElementById("modal-error").classList.add("hidden");
  document.body.style.overflow = "";
  var saveBtn = document.getElementById("modal-save");
  saveBtn.textContent = "Update Measurement";
  saveBtn.disabled = false;
}

// Close on overlay click or close/cancel buttons
document
  .getElementById("modal-overlay")
  .addEventListener("click", function (e) {
    if (e.target === this) closeModal();
  });
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("modal-cancel").addEventListener("click", closeModal);

// Store which child/date is being edited
var modalChild = null;
var modalDate = null;

function openEditModal(childName, date) {
  fetch(`/history/${encodeURIComponent(childName)}`)
    .then(function (r) {
      return r.json();
    })
    .then(function (data) {
      var m = data.measurements.find(function (m) {
        return m.date === date;
      });
      if (!m) return;

      modalChild = childName;
      modalDate = date;

      // Fill in meta info
      var dob = childrenData[childName] ? childrenData[childName].dob : null;
      document.getElementById("modal-child-name").textContent = childName;
      document.getElementById("modal-date").textContent = date;
      document.getElementById("modal-age").textContent = dob
        ? formatAge(dob, date)
        : "";

      // Clear all modal inputs first
      [
        "modal-height-ft",
        "modal-height-in",
        "modal-height-dec",
        "modal-height-cm",
        "modal-weight-lbs",
        "modal-weight-oz",
        "modal-weight-dec-lbs",
        "modal-weight-kg",
        "modal-weight-g",
        "modal-hc-in",
        "modal-hc-cm",
      ].forEach(function (id) {
        document.getElementById(id).value = "";
      });

      // Pre-fill height in cm
      if (m.height_cm) {
        document
          .querySelector("#modal-height-toggle .unit-btn[data-unit='cm']")
          .click();
        document.getElementById("modal-height-cm").value = m.height_cm;
      } else {
        document
          .querySelector("#modal-height-toggle .unit-btn[data-unit='ft_in']")
          .click();
      }

      // Pre-fill weight in kg
      if (m.weight_kg) {
        document
          .querySelector("#modal-weight-toggle .unit-btn[data-unit='kg']")
          .click();
        document.getElementById("modal-weight-kg").value = m.weight_kg;
      } else {
        document
          .querySelector("#modal-weight-toggle .unit-btn[data-unit='lbs_oz']")
          .click();
      }

      // Pre-fill HC in cm
      if (m.hc_cm) {
        document
          .querySelector("#modal-hc-toggle .unit-btn[data-unit='cm']")
          .click();
        document.getElementById("modal-hc-cm").value = m.hc_cm;
      } else {
        document
          .querySelector("#modal-hc-toggle .unit-btn[data-unit='dec_in']")
          .click();
      }

      openModal();
    });
}

document
  .getElementById("modal-save")
  .addEventListener("click", async function () {
    var heightCm = readHeightCm("modal-");
    var weightKg = readWeightKg("modal-");
    var hcCm = readHcCm("modal-");
    var modalError = document.getElementById("modal-error");

    modalError.classList.add("hidden");

    if (heightCm === null && weightKg === null) {
      modalError.className = "result error-box";
      modalError.classList.remove("hidden");
      modalError.innerHTML =
        "<div>Please enter at least a height or weight.</div>";
      return;
    }

    var saveBtn = document.getElementById("modal-save");
    saveBtn.textContent = "Saving…";
    saveBtn.disabled = true;

    try {
      var response = await fetch(
        `/measurements/${encodeURIComponent(modalChild)}/${modalDate}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            height_cm: heightCm ? round1(heightCm) : null,
            weight_kg: weightKg ? round1(weightKg) : null,
            hc_cm: hcCm ? round1(hcCm) : null,
          }),
        },
      );

      var data = await response.json();

      if (!response.ok) {
        saveBtn.textContent = "Update Measurement";
        saveBtn.disabled = false;
        modalError.className = "result error-box";
        modalError.classList.remove("hidden");
        modalError.innerHTML =
          "<div>" + (data.error || "Could not save.") + "</div>";
        return;
      }

      // Success — brief confirmation then close and refresh
      saveBtn.textContent = "✓ Updated";
      setTimeout(function () {
        closeModal();
        loadHistory(modalChild);
      }, 600);
    } catch (err) {
      saveBtn.textContent = "Update Measurement";
      saveBtn.disabled = false;
      console.error(err);
    }
  });

// ── 12. DELETE MODAL ─────────────────────────────────────────────────────────

var deleteChild = null;
var deleteDate = null;

function openDeleteModal(childName, date) {
  deleteChild = childName;
  deleteDate = date;

  var dob = childrenData[childName] ? childrenData[childName].dob : null;
  document.getElementById("delete-modal-child-name").textContent = childName;
  document.getElementById("delete-modal-date").textContent = date;
  document.getElementById("delete-modal-age").textContent = dob
    ? formatAge(dob, date)
    : "";

  // Reset button state
  var confirmBtn = document.getElementById("delete-modal-confirm");
  confirmBtn.textContent = "Delete Measurement";
  confirmBtn.disabled = false;

  document.getElementById("delete-modal-overlay").classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeDeleteModal() {
  document.getElementById("delete-modal-overlay").classList.add("hidden");
  document.body.style.overflow = "";
}

document
  .getElementById("delete-modal-overlay")
  .addEventListener("click", function (e) {
    if (e.target === this) closeDeleteModal();
  });
document
  .getElementById("delete-modal-close")
  .addEventListener("click", closeDeleteModal);
document
  .getElementById("delete-modal-cancel")
  .addEventListener("click", closeDeleteModal);

document
  .getElementById("delete-modal-confirm")
  .addEventListener("click", async function () {
    var confirmBtn = document.getElementById("delete-modal-confirm");
    confirmBtn.textContent = "Deleting…";
    confirmBtn.disabled = true;

    try {
      var response = await fetch(
        `/measurements/${encodeURIComponent(deleteChild)}/${deleteDate}`,
        { method: "DELETE" },
      );

      var data = await response.json();

      if (!response.ok) {
        confirmBtn.textContent = "Delete Measurement";
        confirmBtn.disabled = false;
        console.error(data.error);
        return;
      }

      // Success — close and refresh
      confirmBtn.textContent = "✓ Deleted";
      setTimeout(function () {
        closeDeleteModal();
        loadHistory(deleteChild);
      }, 600);
    } catch (err) {
      confirmBtn.textContent = "Delete Measurement";
      confirmBtn.disabled = false;
      console.error(err);
    }
  });
