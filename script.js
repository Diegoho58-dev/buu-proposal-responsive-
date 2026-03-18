const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const scoreEl = document.getElementById('score');
const livesEl = document.getElementById('lives');
const gameOverEl = document.getElementById('gameOver');
const finalScoreEl = document.querySelector('#finalScore');
const touchZone = document.getElementById('touchZone');

// RESPONSIVE CANVAS
function resizeCanvas() {
    const size = Math.min(window.innerWidth, window.innerHeight * 0.8);
    canvas.width = size;
    canvas.height = size * 0.5;
    canvas.style.width = size + 'px';
    canvas.style.height = (size * 0.5) + 'px';
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);
window.addEventListener('orientationchange', () => setTimeout(resizeCanvas, 100));

let game = {
    score: 0,
    lives: 3,
    gameSpeed: 4,
    gameRunning: true,
    obstacles: [],
    keys: {}
};

const buu = {
    x: 80,
    y: canvas.height - 120,
    width: 50,
    height: 70,
    velY: 0,
    jumping: false,
    grounded: false,
    groundY: 0
};

// TOUCH + TECLAS
touchZone.addEventListener('touchstart', jump, { passive: false });
touchZone.addEventListener('click', jump);
document.addEventListener('keydown', (e) => {
    if (e.code === 'Space') {
        e.preventDefault();
        jump();
    }
});

function jump(e) {
    e?.preventDefault();
    if (buu.grounded) {
        buu.velY = -16;
        buu.grounded = false;
        buu.jumping = true;
    }
}

function update() {
    if (!game.gameRunning) return;
    
    buu.groundY = canvas.height - 100;
    
    // FÍSICA
    buu.velY += 0.8;
    buu.y += buu.velY;
    if (buu.y >= buu.groundY) {
        buu.y = buu.groundY;
        buu.velY = 0;
        buu.grounded = true;
    }

    // OBSTÁCULOS
    if (Math.random() < 0.025) {
        game.obstacles.push({
            x: canvas.width,
            y: Math.random() > 0.6 ? buu.groundY - 50 : buu.groundY,
            width: 35,
            height: 50,
            type: Math.random() > 0.7 ? 'fuego' : 'roca'
        });
    }

    // ACTUALIZAR OBSTÁCULOS
    for (let i = game.obstacles.length - 1; i >= 0; i--) {
        const obs = game.obstacles[i];
        obs.x -= game.gameSpeed;
        
        // COLISIÓN
        if (obs.x < buu.x + buu.width && obs.x + obs.width > buu.x &&
            obs.y < buu.y + buu.height && obs.y + obs.height > buu.y) {
            game.lives--;
            livesEl.textContent = game.lives;
            game.obstacles.splice(i, 1);
            if (game.lives <= 0) endGame();
            continue;
        }
        
        // PUNTOS
        if (obs.x + obs.width < 0) {
            game.obstacles.splice(i, 1);
            game.score++;
            scoreEl.textContent = game.score;
            game.gameSpeed += 0.05;
        }
    }

    draw();
    requestAnimationFrame(update);
}

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // SUELO
    ctx.fillStyle = '#90EE90';
    ctx.fillRect(0, buu.groundY + 20, canvas.width, canvas.height - buu.groundY - 20);
    
    // NUBES
    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    for (let i = 0; i < 3; i++) {
        const x = (100 + i * 200 - (game.score * 2) % canvas.width + canvas.width) % (canvas.width + 200);
        ctx.beginPath();
        ctx.arc(x, 60 + Math.sin(i) * 15, 25, 0, Math.PI * 2);
        ctx.arc(x + 30, 60 + Math.sin(i) * 15, 35, 0, Math.PI * 2);
        ctx.fill();
    }
    
    // BUU MEJORADO
    const pink = buu.jumping ? '#ff69b4' : '#ff1493';
    ctx.fillStyle = pink;
    ctx.fillRect(buu.x, buu.y, buu.width, buu.height);
    
    // CARA BUU
    ctx.fillStyle = 'white';
    ctx.fillRect(buu.x + 8, buu.y + 8, 12, 12);
    ctx.fillRect(buu.x + 30, buu.y + 8, 12, 12);
    ctx.fillStyle = 'black';
    ctx.fillRect(buu.x + 11, buu.y + 11, 6, 6);
    ctx.fillRect(buu.x + 33, buu.y + 11, 6, 6);
    ctx.fillRect(buu.x + 18, buu.y + 40, 14, 6); // BOCA
    
    // ANTENAS
    ctx.fillStyle = pink;
    ctx.fillRect(buu.x + 12, buu.y - 3, 6, 12);
    ctx.fillRect(buu.x + 32, buu.y - 3, 6, 12);
    
    // OBSTÁCULOS
    game.obstacles.forEach(obs => {
        if (obs.type === 'fuego') {
            ctx.fillStyle = '#ff4500';
            ctx.fillRect(obs.x, obs.y, obs.width, obs.height);
            ctx.fillStyle = '#ffff00';
            ctx.fillRect(obs.x + 3, obs.y - 8, 8, 15);
        } else {
            ctx.fillStyle = '#8B4513';
            ctx.fillRect(obs.x, obs.y, obs.width, obs.height);
            ctx.fillStyle = '#A0522D';
            ctx.fillRect(obs.x + 5, obs.y + 5, obs.width - 10, 15);
        }
    });
}

function endGame() {
    game.gameRunning = false;
    finalScoreEl.textContent = game.score;
    gameOverEl.style.display = 'block';
}

function restartGame() {
    game.score = 0;
    game.lives = 3;
    game.gameSpeed = 4;
    game.obstacles = [];
    game.gameRunning = true;
    buu.y = buu.groundY;
    scoreEl.textContent = 0;
    livesEl.textContent = 3;
    gameOverEl.style.display = 'none';
    update();
}

// INICIAR
update();
