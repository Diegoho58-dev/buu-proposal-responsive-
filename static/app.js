document.addEventListener("DOMContentLoaded", () => {
  const textareas = document.querySelectorAll("textarea");

  textareas.forEach((textarea) => {
    textarea.addEventListener("input", () => {
      textarea.style.height = "auto";
      textarea.style.height = `${textarea.scrollHeight}px`;
    });
  });

  const toggleButton = document.querySelector("[data-toggle-password]");
  const passwordInput = document.querySelector("#password");

  if (toggleButton && passwordInput) {
    toggleButton.addEventListener("click", () => {
      const visible = passwordInput.type === "text";

      passwordInput.type = visible ? "password" : "text";
      toggleButton.textContent = visible ? "👁" : "🙈";
      toggleButton.setAttribute(
        "aria-label",
        visible ? "Mostrar contraseña" : "Ocultar contraseña"
      );
      toggleButton.setAttribute(
        "aria-pressed",
        visible ? "false" : "true"
      );
    });
  }
});
