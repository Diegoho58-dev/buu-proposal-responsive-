function scrollToSection(id) {
  const element = document.getElementById(id);

  if (element) {
    element.scrollIntoView({
      behavior: "smooth"
    });
  }
}

function showAlert() {
  alert("Gracias por leer esto 💔");
}
