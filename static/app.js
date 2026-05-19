document.addEventListener("DOMContentLoaded", () => {

    const form = document.getElementById("chatForm");
    const container = document.getElementById("messagesContainer");
    const textarea = document.getElementById("content");

    // ✅ Auto resize textarea
    document.querySelectorAll("textarea").forEach((t) => {
        t.addEventListener("input", () => {
            t.style.height = "auto";
            t.style.height = t.scrollHeight + "px";
        });
    });

    // ✅ Cargar mensajes
    async function loadMessages() {
        if (!container) return;

        const res = await fetch("/api/messages");
        const messages = await res.json();

        container.innerHTML = "";

        messages.forEach((msg) => {
            const div = document.createElement("article");

            div.className = "message-card " +
                (msg.sender_id === CURRENT_USER_ID ? "from-diego" : "from-jenny");

            div.innerHTML = `
                <div class="message-meta">
                    <strong>${msg.sender}</strong>
                    <span>${msg.created_at}</span>
                </div>
                <p>${msg.content}</p>
            `;

            container.appendChild(div);
        });

        container.scrollTop = container.scrollHeight;
    }

    // ✅ Enviar mensaje sin recargar
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            const content = textarea.value.trim();
            if (!content) return;

            await fetch("/api/send", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ content })
            });

            textarea.value = "";
            loadMessages();
        });
    }

    // ✅ actualizar cada 2 segundos
    setInterval(loadMessages, 2000);

    // ✅ cargar al inicio
    loadMessages();
});
