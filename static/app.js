document.addEventListener("DOMContentLoaded", () => {
  const textareas = document.querySelectorAll("textarea");

  textareas.forEach((textarea) => {
    const resize = () => {
      textarea.style.height = "auto";
      textarea.style.height = textarea.scrollHeight + "px";
    };

    resize();
    textarea.addEventListener("input", resize);
  });

  const toggleButton = document.querySelector("[data-toggle-password]");
  const passwordInput = document.querySelector("#password");

  if (toggleButton && passwordInput) {
    toggleButton.addEventListener("click", () => {
      const hidden = passwordInput.type === "password";
      passwordInput.type = hidden ? "text" : "password";
      toggleButton.textContent = hidden ? "🙈" : "👁";
      toggleButton.setAttribute(
        "aria-label",
        hidden ? "Ocultar contraseña" : "Mostrar contraseña"
      );
    });
  }

  const chatMessages = document.querySelector(".chat-messages");
  if (chatMessages) {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
});
