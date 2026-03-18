const historia = [
    {
        titulo: "1 NOVIEMBRE - El mejor día",
        texto: "Jenny, el MEJOR DÍA de mi vida fue el 1 de Noviembre. Te llamé temblando... pero tu voz me dio paz. ¡SUPE que eras MI PERSONA!"
    },
    {
        titulo: "7 NOVIEMBRE - Noche mágica",
        texto: "El 7 de Noviembre te dije que te amaba de verdad. Vi en tus ojos que tú también me amas. ¡NACIÓ NUESTRO AMOR ETERNO! ❤️"
    },
    {
        titulo: "Dios nos unió",
        texto: "\"Dos podrán ayudarse mutuamente, y tendrán éxito\" - Eclesiastés 4:9. ¡DIOS puso tu nombre en mi corazón Jenny!"
    },
    {
        titulo: "Amor verdadero",
        texto: "\"El amor todo lo sufre, todo lo cree, todo lo espera\" - 1 Corintios 13:4-7. Así es nuestro amor Jenny."
    },
    {
        titulo: "Nuestro primer reto",
        texto: "Cuando todo se puso difícil, TÚ no te fuiste. Me tomaste de la mano y oramos. ¡ERES MI FUERZA!"
    },
    {
        titulo: "El templo nos espera",
        texto: "\"Lo que Dios ha unido, no lo separe el hombre\" - Mateo 19:6. Dios nos prepara para el templo Jenny."
    },
    {
        titulo: "Popayán nuestro hogar",
        texto: "Tú, yo, nuestros hijos, la iglesia. Construiremos un LEGADO para Dios en Popayán. ¡Nuestra familia eterna!"
    },
    {
        titulo: "Tu sonrisa",
        texto: "Cada vez que sonríes, recuerdo por qué lucho. Jenny, TÚ ERES MI RAZÓN para conquistar el mundo."
    },
    {
        titulo: "Promesa de Dios",
        texto: "\"No te dejaré, ni te desampararé\" - Hebreos 13:5. Dios nos lo prometió. ¡Él nos sostendrá siempre!"
    },
    {
        titulo: "Nuestra misión",
        texto: "Serviremos en la iglesia juntos. Visitaremos familias. ¡Seremos un equipo misional para Dios Jenny!"
    },
    {
        titulo: "Planes de Dios",
        texto: "\"Yo sé los planes que tengo para vosotros\" - Jeremías 29:11. ¡Dios ya vio nuestro futuro Jenny!"
    },
    {
        titulo: "HOY te pido",
        texto: "Jenny, ¿aceptas salir adelante CONMIGO? ¿Construir la familia eterna que Dios diseñó para nosotros? 💍"
    }
];

let actual = 0;

function siguienteHistoria() {
    if (actual >= historia.length - 1) {
        // FINAL
        document.getElementById('final').style.display = 'block';
        document.querySelector('.narracion').style.display = 'none';
        document.querySelector('.progreso').style.display = 'none';
        confeti();
        return;
    }
    
    actual++;
    mostrarHistoria();
}

function mostrarHistoria() {
    const cap = historia[actual];
    document.getElementById('escenario').className = 'escenario ' + (cap.clase || 'nov1');
    document.getElementById('escenarioTitulo').textContent = cap.titulo;
    document.getElementById('textoHistoria').textContent = cap.texto;
    document.getElementById('progreso').textContent = `Capítulo ${actual + 1}/12`;
}

function reiniciar() {
    actual = 0;
    document.getElementById('final').style.display = 'none';
    document.querySelector('.narracion').style.display = 'block';
    document.querySelector('.progreso').style.display = 'block';
    mostrarHistoria();
}

function confeti() {
    for(let i = 0; i < 50; i++) {
        setTimeout(() => {
            let c = document.createElement('div');
            c.innerHTML = '💖';
            c.style.cssText = `
                position: fixed; top: -10%; left: ${Math.random()*100}%;
                font-size: ${20 + Math.random()*20}px; pointer-events: none;
                animation: caida 3s linear forwards; z-index: 1000;
            `;
            document.body.appendChild(c);
            setTimeout(() => c.remove(), 3000);
        }, i * 50);
    }
}

mostrarHistoria();
