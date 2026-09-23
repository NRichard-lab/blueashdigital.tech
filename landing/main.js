const toggle = document.querySelector(".nav-toggle");
const panel = document.querySelector(".header-panel");

function closeMenu() {
  toggle.setAttribute("aria-expanded", "false");
  panel.classList.remove("is-open");
}

toggle.addEventListener("click", () => {
  const open = toggle.getAttribute("aria-expanded") === "true";
  toggle.setAttribute("aria-expanded", String(!open));
  panel.classList.toggle("is-open", !open);
});

panel.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", closeMenu);
});

document.querySelectorAll("[data-open]").forEach((button) => {
  button.addEventListener("click", () => {
    const dialog = document.getElementById(button.dataset.open);
    if (!dialog) return;
    if (typeof dialog.showModal === "function" && !dialog.open) {
      dialog.showModal();
    }
    closeMenu();
  });
});

document.querySelectorAll("[data-close]").forEach((button) => {
  button.addEventListener("click", () => {
    const dialog = button.closest("dialog");
    if (dialog && dialog.open) dialog.close();
  });
});

document.querySelectorAll("dialog").forEach((dialog) => {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
});

document.querySelectorAll("form[data-preview]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const status = form.querySelector(".form-status");
    const kind = form.dataset.preview;
    if (kind === "sign-in") {
      status.textContent =
        "This preview does not sign you in. The live portal stays separate from this page.";
    } else {
      status.textContent = "Noted on this page only. Nothing was sent.";
    }
  });
});

