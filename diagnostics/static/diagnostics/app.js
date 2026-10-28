// Functionality for the report browser

// Dropdowns auto submit so their filter is applied immediately
document.querySelectorAll("[data-autosubmit]").forEach((select) => {
  select.addEventListener("change", () => select.form.requestSubmit());
});

// Buttions that can auto-copy to clipboard
document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const source = document.querySelector(button.dataset.copy);
    await navigator.clipboard.writeText(source.textContent.trim());
    const label = button.textContent;
    button.textContent = "Copied!";
    setTimeout(() => (button.textContent = label), 1500);
  });
});

// / hotkey to jump to search box
document.addEventListener("keydown", (event) => {
  const search = document.querySelector("[data-search]");
  const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName);
  if (event.key === "/" && search && !typing) {
    event.preventDefault();
    search.focus();
    search.select();
  }
});

// Hide failed thumbnail previews
document.querySelectorAll("img[data-thumbnail]").forEach((image) => {
  const failed = image.complete && image.naturalWidth === 0;
  if (failed) image.remove();
  else image.addEventListener("error", () => image.remove());
});
