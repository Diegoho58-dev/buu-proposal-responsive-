const historia = [
    {
        titulo: "1 NOVIEMBRE - El día que cambió todo",
        texto: "Jenny, el MEJOR DÍA de mi vida fue el 1 de Noviembre. Te llamé temblando... pero tu voz me dio paz. Desde ese momento supe que eras MI PERSONA.",
        clase: "nov1"
    },
    {
        titulo: "7 NOVIEMBRE - Noche romántica eterna",
        texto: "El 7 de Noviembre fue mágico. Te dije que te amaba de verdad y vi en tus ojos que tú también me amas. ¡Ese día nació nuestro amor verdadero! ❤️",
        clase: "nov7"
    },
    {
        titulo: "Dios nos unió",
        texto: "\"Dos podrán ayudarse mutuamente, y tendrán éxito\" - Eclesiastés 4:9. Dios puso tu nombre en mi corazón Jenny. ¡Él nos juntó por propósito divino!",
        clase: "dios"
    },
    {
        titulo: "La Perla del Gran Precio",
        texto: "\"El amor es bondad... todo lo sufre, todo lo cree, todo lo espera, todo lo soporta\" - 1 Corintios 13:4-7. Así es nuestro amor Jenny.",
        clase: "dios"
    },
    {
        titulo: "Nuestro primer obstáculo",
        texto: "Cuando las cosas se pusieron difíciles, tú no te fuiste. Me tomaste de la mano y oramos juntos. ¡ERES MI FUERZA Jenny!",
        clase: "nov1"
    },
    {
        titulo: "El templo nos espera",
        texto: "\"Lo que Dios ha unido, no lo separe el hombre\" - Mateo 19:6. Jenny, Dios nos está preparando para el templo. ¡Nuestra eternidad juntos!",
        clase: "dios"
    },
    {
        titulo: "Salgamos adelante JUNTOS",
        texto: "Popayán será nuestro hogar. Tú, yo, nuestros hijos, la iglesia, las misiones. ¡Construiremos un legado para Dios juntos! ¿Lista mi amor?",
        clase: "futuro"
    },
    {
        titulo: "Tu sonrisa es mi motor",
        texto: "Cada vez que te veo sonreír, recuerdo por qué lucho. Jenny, TÚ ERES MI RAZÓN para levantarme cada mañana y conquistar el mundo.",
        clase: "nov7"
    },
    {
        titulo: "Promesas de Dios",
        texto: "\"No te dejaré, ni te desampararé\" - Hebreos 13:5. Dios nos lo prometió Jenny. Él nos sostendrá en cada prueba que enfrentemos.",
        clase: "dios"
    },
    {
        titulo: "Nuestra misión juntos",
        texto: "Serviremos en la iglesia, visitaremos familias, llevaremos el evangelio. Jenny, seremos un equipo misional INSEPARABLE para Dios.",
        clase: "futuro"
    },
    {
        titulo: "El futuro que Dios pintó",
        texto: "\"Porque yo sé los planes que tengo para vosotros... planes de bienestar y no de calamidad\" - Jeremías 29:11. ¡Dios ya lo vio Jenny!",
        clase: "futuro"
    },
    {
        titulo: "HOY te lo pido",
        texto: "Jenny, después de esta historia... ¿aceptas salir adelante CONMIGO? ¿Construir la familia eterna que Dios diseñó para nosotros? 💍",
        clase: "nov1"
    }
];

let capituloActual = 0;
const buuImg = document.getElementById('buuImg');
const escenario = document.getElementById('escenario');
const escenarioTitulo = document.getElementById('escenarioTitulo');
const historiaText = document.getElementById('historiaText');
const capituloNum = document.getElementById('capituloNum');
const finalEpico = document.getElementById('finalEpico');
const narracionBox = document.getElementById('narracionBox');

function siguienteEscenario() {
    if (capituloActual >= historia.length - 1) {
        // FINAL ÉPICO
        narracionBox.style.display = 'none';
        setTimeout(() => {
            finalEpico.style.display = 'block';
            crearConfetiMatrimonio();
        }, 800);
        return;
    }
    
    capituloActual++;
    mostrarCapitulo();
}

function mostrarCapitulo() {
    const actual = historia[capituloActual];
    
    // ESCENARIO
    escenario.className = `escenario ${actual.clase}`;
    escenarioTitulo.textContent = actual.titulo;
    historiaText.innerHTML = actual.texto;
    capituloNum.textContent = capituloActual + 1;
    
    // ANIMACIÓN BUU
    buuImg.style.animation = 'none';
    setTimeout(() => {
        buuImg.style.animation = 'flotarBuu 3s ease-in-out infinite';
    }, 100);
    
    // TRANSICIÓN SUAVE
    narracionBox.style.opacity = '0';
    setTimeout(() => {
        narracionBox.style.opacity = '1';
    }, 300);
}

function reiniciar() {
    capituloActual = 0;
    finalEpico.style.display = 'none';
    narracionBox.style.display = 'block';
    mostrarCapitulo();
}

function crearConfetiMatrimonio() {
    for(let i = 0; i < 80; i++) {
        setTimeout(() => {
            const confeti = document.createElement('div');
            confeti.innerHTML = ['💍','💖','✨','👰','🤵'][Math.floor(Math.random()*5)];
            confeti.style.cssText = `
                position: fixed; left: ${Math.random()*100}vw; top: ${Math.random()*-50-20}vh;
                font-size: ${Math.random()*30+20}px; pointer-events: none; z-index: 1000;
                animation: caerMatrimonio 4s linear forwards;
            `;
            document.body.appendChild(confeti);
            setTimeout(() => confeti.remove(), 4000);
        }, i * 40);
    }
}

// INICIO AUTOMÁTICO
setTimeout(() => {
    mostrarCapitulo();
}, 1000);

// ANIMACIÓN CSS DINÁMICA
const style = document.createElement('style');
style.textContent = `
    @keyframes caerMatrimonio {
        0% { transform: translateY(0) rotate(0deg); opacity: 1; }
        100% { transform: translateY(120vh) rotate(720deg); opacity: 0; }
    }
`;
document.head.appendChild(style);

// TOUCH MOBILE
document.addEventListener('touchstart', e => e.preventDefault(), { passive: false });
