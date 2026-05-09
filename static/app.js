document.addEventListener('DOMContentLoaded', () => {
  const textareas = document.querySelectorAll('textarea');
  const chatMessages = document.getElementById('chatMessages');
  const chatComposer = document.getElementById('chatComposer');
  const chatInput = document.getElementById('chatInput');

  const resizeTextarea = (textarea) => {
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 130)}px`;
  };

  textareas.forEach((textarea) => {
    resizeTextarea(textarea);

    textarea.addEventListener('input', () => {
      resizeTextarea(textarea);
    });
  });

  const scrollToBottom = () => {
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  };

  scrollToBottom();

  if (chatComposer) {
    chatComposer.addEventListener('submit', () => {
      setTimeout(scrollToBottom, 60);
    });
  }

  if (chatInput && window.innerWidth <= 640) {
    chatInput.addEventListener('focus', () => {
      setTimeout(scrollToBottom, 250);
    });
  }
});
