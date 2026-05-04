document.addEventListener('DOMContentLoaded', () => {
  const textareas = document.querySelectorAll('textarea');

  textareas.forEach((textarea) => {
    const resizeTextarea = () => {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    };

    resizeTextarea();
    textarea.addEventListener('input', resizeTextarea);
  });

  const messagesContainer = document.getElementById('waMessages');
  if (messagesContainer) {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }
});
