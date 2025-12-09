// Placeholder file for CRM scripts.

// Example: tab switching behavior for profile pages
document.addEventListener("DOMContentLoaded", function () {
    const tabButtons = document.querySelectorAll("[data-tab-target]");
    const tabContents = document.querySelectorAll(".tab-content-section");

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = document.querySelector(btn.dataset.tabTarget);

            tabContents.forEach(c => c.classList.add("d-none"));
            tabButtons.forEach(b => b.classList.remove("active"));

            target.classList.remove("d-none");
            btn.classList.add("active");
        });
    });
});
