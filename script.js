const boton = document.getElementById("startBtn");
const mensaje = document.getElementById("mensaje");

boton.addEventListener("click", () => {

mensaje.style.display = "block";

boton.style.display = "none";

});

function aceptar(){

document.getElementById("finalMensaje").style.display = "block";

crearConfeti();

}

function crearConfeti(){

for(let i=0;i<40;i++){

let heart = document.createElement("span");

heart.innerHTML = "❤️";

heart.style.left = Math.random()*100 + "vw";

heart.style.fontSize = (Math.random()*20+15)+"px";

heart.style.animationDuration = (Math.random()*3+5)+"s";

document.querySelector(".hearts").appendChild(heart);

}

}
