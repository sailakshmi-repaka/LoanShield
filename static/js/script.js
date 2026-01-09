function showSection(sectionId) {
    const sections = document.querySelectorAll(".page-section");
    sections.forEach(section => section.classList.remove("active"));

    const target = document.getElementById(sectionId);
    if (target) {
        target.classList.add("active");
    }

    document.body.style.overflow = sectionId === "home" ? "hidden" : "auto";
}

/* ---------- SCAN FORM AJAX ---------- */
document.addEventListener("DOMContentLoaded", function () {

    // Scan app handler
    const scanForm = document.getElementById("scanForm");

    if (scanForm) {
        scanForm.addEventListener("submit", function (e) {
            e.preventDefault();

            const formData = new FormData(scanForm);
            const resultBox = document.getElementById("scanResultBox");

            resultBox.innerHTML = "🔍 Scanning application...";

            fetch("/predict", {
                method: "POST",
                body: formData
            })
            .then(res => res.text())
            .then(html => {
                resultBox.innerHTML = html;
            })
            .catch(() => {
                resultBox.innerHTML = "❌ Error fetching result.";
            });
        });
    }

    /* ---------- REPORT FORM ---------- */
    const reportForm = document.getElementById("reportForm");

    if (reportForm) {
        reportForm.addEventListener("submit", function (e) {
            e.preventDefault();

            const formData = new FormData(reportForm);
            const message = document.getElementById("reportMessage");

            fetch("/report", {
                method: "POST",
                body: formData
            })
            .then(res => res.text())
            .then(data => {
                message.innerText = data;
                message.style.color = "lightgreen";
                reportForm.reset();
            })
            .catch(() => {
                message.innerText = "Error submitting report.";
                message.style.color = "red";
            });
        });
    }

});
window.onload = function () {
    const section = localStorage.getItem("openSection");
    if (section) {
        showSection(section);
        localStorage.removeItem("openSection");
    }
};

