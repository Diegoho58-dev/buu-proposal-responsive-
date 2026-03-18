const preguntas = [
    "¿Jenny realmente quiere a Diego?",
    "¿Te hace feliz estar con Diego?",
    "¿Piensas en Diego cuando no está?",
    "¿Diego te hace sentir especial?",
    "¿Confías plenamente en Diego?",
    "¿Te imaginas un futuro con Diego?",
    "¿Diego es tu prioridad #1?",
    "¿Te sientes segura con Diego?",
    "¿Diego te entiende perfectamente?",
    "¿Quieres hacer feliz a Diego siempre?",
    "¿Diego es tu persona ideal?",
    "¿Amarás a Diego por siempre?",
    "¿Diego te hace reír incluso en días malos?",
    "¿Te emociona ver mensajes de Diego?",
    "¿Sientes mariposas cuando Diego te abraza?",
    "¿Diego es tu mejor amigo también?",
    "¿Quieres viajar el mundo con Diego?",
    "¿Diego te inspira a ser mejor?",
    "¿Te gusta cocinar para Diego?",
    "¿Diego te hace sentir la mujer más bella?",
    "¿Quieres tener hijos con Diego algún día?",
    "¿Diego es tu refugio en la tormenta?",
    "¿Te encanta el olor de Diego?",
    "¿Diego te hace sentir protegida siempre?",
    "¿Prometes amar a Diego toda la vida? 💍"
];

let preguntaActual = 0;
const buuImg = document.getElementById('buuImg');
const dialogoBox = document.getElementById('dialogoBox');
const preguntaText = document.getElementById('preguntaText');
const preguntaNum = document.getElementById('preguntaNum');
const progresoFill = document.getElementById('progresoFill');
const finalSi = document.getElementById('finalSi');
const finalNo = document.getElementById('finalNo');

// AGREGAR CORAZONES ANIMADOS AL FONDO
function crearCorazonesFondo() {
    const heartsBg = document.querySelector('.hearts-bg');
    for(let i = 1; i <= 4; i++) {
        const heart = document.createElement('span');
        heart.textContent = '💖';
        heart.className = `heart-${i}`;
        heartsBg.appendChild(heart);
    }
}

// INICIAR JUEGO
function iniciarJuego() {
    preguntaActual = 0;
    buuImg.style.left = '15%';
    buuImg.classList.remove('hablando', 'cerca-jenny');
    dialogoBox.style.display = 'block';
    finalSi.style.display = 'none';
    finalNo.style.display = 'none';
    progresoFill.style.width = '0%';
    preguntaNum.textContent = '1';
    siguientePregunta();
}

function siguientePregunta() {
    if (preguntaActual >= preguntas.length) {
        // ¡COMPLETÓ LAS 25 PREGUNTAS!
        progresoFill.style.width = '100%';
        buuImg.classList.add('cerca-jenny');
        buuImg.src = 'img/buu.png'; // Refresca imagen
        setTimeout(() => {
            dialogoBox.style.display = 'none';
            finalSi.style.display = 'block';
            // CONFETI ÉPICO
            crearConfetiEpico();
        }, 2000);
        return;
    }
    
    preguntaText.textContent = preguntas[preguntaActual];
    preguntaNum.textContent = preguntaActual + 1;
    
    // BARRA DE PROGRESO
    const porcentaje = ((preguntaActual) / preguntas.length) * 100;
    progresoFill.style.width = porcentaje + '%';
    
    // BUU HABLA Y CAMINA
    buuImg.classList.add('hablando');
    const nuevaPos = 15 + (preguntaActual * 2.2);
    buuImg.style.left = Math.min(nuevaPos, 52) + '%';
}

function responder(respuesta) {
    buuImg.classList.remove('hablando');
    
    if (respuesta === 'no') {
        // JENNY DIJO NO - BUU SE PONE TRISTE
        buuImg.style.filter = 'grayscale(1) saturate(0.5)';
        setTimeout(() => {
            dialogoBox.style.display = 'none';
            finalNo.style.display = 'block';
        }, 1200);
        return;
    }
    
    // ¡SÍ! EFECTO POSITIVO
    buuImg.style.transform = 'scale(1.1)';
    setTimeout(() => {
        buuImg.style.transform = 'scale(1)';
        preguntaActual++;
        siguientePregunta();
    }, 800);
}

function reiniciar() {
    location.reload(); // Reinicio completo
}

function crearConfetiEpico() {
    for(let i = 0; i < 60; i++) {
        setTimeout(() => {
            const confeti = document.createElement('div');
            confeti.innerHTML = ['💖','💕','✨','💍','🎉'][Math.floor(Math.random()*5)];
            confeti.style.position = 'fixed';
            confeti.style.left = Math.random() * 100 + 'vw';
            confeti.style.top = Math.random() * 100 + 'vh';
            confeti.style.fontSize = (Math.random() * 25 + 20) + 'px';
            confeti.style.pointerEvents = 'none';
            confeti.style.zIndex = '1000';
            confeti.style.animation = 'confetiFall 3s linear forwards';
            document.body.appendChild(confeti);
            
            setTimeout(() => confeti.remove(), 3000);
        }, i * 50);
    }
}

// TOUCH OPTIMIZADO MÓVIL
document.addEventListener('touchstart', (e) => e.preventDefault(), { passive: false });
document.addEventListener('selectstart', (e) => e.preventDefault());

// INICIO AUTOMÁTICO ÉPICO
setTimeout(() => {
    crearCorazonesFondo();
    iniciarJuego();
}, 800);

// AGREGAR ANIMACIÓN CONFETI AL CSS (se crea dinámicamente)
const style = document.createElement('style');
style.textContent = `
    @keyframes confetiFall {
        0% { transform: translateY(0) rotate(0deg); opacity: 1; }
        100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
    }
`;
document.head.appendChild(style);
