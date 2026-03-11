document.addEventListener("DOMContentLoaded", function () {
    const resumeElement = document.getElementById("resume");
    const scriptElement = document.getElementById("clauses-data");

    if (!resumeElement || !scriptElement) return;

    let clauses = [];
    try {
        clauses = JSON.parse(scriptElement.textContent || "[]");
    } catch (e) {
        clauses = [];
    }

    if (!Array.isArray(clauses) || clauses.length === 0) return;

    let html = resumeElement.innerHTML;
    clauses.forEach((clause) => {
        if (!clause) return;
        const escaped = clause.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const regex = new RegExp(escaped, "g");
        html = html.replace(regex, `<mark>${clause}</mark>`);
    });

    resumeElement.innerHTML = html;
});