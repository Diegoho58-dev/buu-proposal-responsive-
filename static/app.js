document.addEventListener('DOMContentLoaded', () => {
  const textareas = document.querySelectorAll('textarea');

  textareas.forEach((textarea) => {
    textarea.addEventListener('input', () => {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    });
  });
});
