const { createApp, ref, onMounted } = Vue;

createApp({
    setup() {
        // --- РЕАКТИВНІ ЗМІННІ ---
        const isConnected = ref(false);
        const robot = ref({ x: 0, y: 0, status: 'idle', battery: 100, history: [] });
        
        const gridWidth = ref(20);
        const gridHeight = ref(20);
        const mapGrid = ref([]);
        const currentPath = ref([]);
        const mazeDensity = ref(20);
        const logs = ref([]); 

        // Змінна для керування спливаючим вікном (модалкою)
        const showModal = ref(false);
        const simSpeed = ref(3);

        let canvas, ctx, socket;

        // --- ФУНКЦІЯ МАЛЮВАННЯ НА CANVAS ---
        const draw = () => {
            if (!ctx) return;
            
            const width = canvas.width;
            const height = canvas.height;
            const cellW = width / gridWidth.value;
            const cellH = height / gridHeight.value;

            ctx.clearRect(0, 0, width, height);

            for (let y = 0; y < gridHeight.value; y++) {
                for (let x = 0; x < gridWidth.value; x++) {
                    ctx.strokeStyle = '#45475a';
                    ctx.lineWidth = 1;
                    ctx.strokeRect(x * cellW, y * cellH, cellW, cellH);
                    
                    if (mapGrid.value[y] && mapGrid.value[y][x] === 1) {
                        ctx.fillStyle = '#cdd6f4'; 
                        ctx.fillRect(x * cellW, y * cellH, cellW, cellH);
                    }
                }
            }

            // --- ВІЗУАЛІЗАЦІЯ ЛІНІЇ МАРШРУТУ ---
            if (currentPath.value.length > 0) {
                const rx = robot.value.x * cellW + cellW / 2;
                const ry = robot.value.y * cellH + cellH / 2;

                ctx.strokeStyle = '#a6e3a1'; 
                ctx.lineWidth = 4;
                ctx.beginPath();
                
                // Починаємо малювати ВІД РОБОТА
                ctx.moveTo(rx, ry); 

                currentPath.value.forEach((point) => {
                    const cx = point[0] * cellW + cellW / 2;
                    const cy = point[1] * cellH + cellH / 2;
                    ctx.lineTo(cx, cy);
                });
                ctx.stroke();
            }

            // ПОВЕРНУЛИ ТВОЮ ПРОЗОРІСТЬ 0.050
            if (robot.value.history && robot.value.history.length > 0) {
                ctx.beginPath();
                ctx.strokeStyle = 'rgba(137, 180, 250, 0.050)'; 
                ctx.lineWidth = cellW / 3; 
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';

                const startX = robot.value.history[0][0] * cellW + cellW / 2;
                const startY = robot.value.history[0][1] * cellH + cellH / 2;
                ctx.moveTo(startX, startY);

                for (let i = 1; i < robot.value.history.length; i++) {
                    const px = robot.value.history[i][0] * cellW + cellW / 2;
                    const py = robot.value.history[i][1] * cellH + cellH / 2;
                    ctx.lineTo(px, py);
                }

                const currentX = robot.value.x * cellW + cellW / 2;
                const currentY = robot.value.y * cellH + cellH / 2;
                ctx.lineTo(currentX, currentY);

                ctx.stroke();
            }

            const rx = robot.value.x * cellW + cellW / 2;
            const ry = robot.value.y * cellH + cellH / 2;
            
            ctx.fillStyle = '#89b4fa';
            ctx.beginPath();
            ctx.arc(rx, ry, cellW / 2.5, 0, Math.PI * 2);
            ctx.fill();
        };

        // --- ОБРОБНИКИ КЛІКІВ ---
        const handleLeftClick = (event) => {
            if (!isConnected.value) return;
            const rect = canvas.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            
            const cellX = Math.floor(x / (canvas.width / gridWidth.value));
            const cellY = Math.floor(y / (canvas.height / gridHeight.value));
            
            socket.emit('set_target', { x: cellX, y: cellY });
        };

        const handleRightClick = (event) => {
            if (!isConnected.value) return;
            const rect = canvas.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            
            const cellX = Math.floor(x / (canvas.width / gridWidth.value));
            const cellY = Math.floor(y / (canvas.height / gridHeight.value));
            
            socket.emit('toggle_obstacle', { x: cellX, y: cellY });
        };

        const emergencyStop = () => {
            if (!isConnected.value) return;
            socket.emit('set_target', { x: robot.value.x, y: robot.value.y });
        };

        const recharge = () => {
            if (!isConnected.value) return;
            socket.emit('recharge');
        };

        const clearMap = () => {
            if (!isConnected.value) return;
            socket.emit('clear_map');
        };

        const generateMaze = () => {
            if (!isConnected.value) return;
            socket.emit('generate_maze', { density: mazeDensity.value / 100 });
        };

        const changeSpeed = () => {
            if (!isConnected.value) return;
            socket.emit('set_speed', { speed: simSpeed.value });
        };

        // --- ІНІЦІАЛІЗАЦІЯ ---
        onMounted(() => {
            canvas = document.getElementById('gridCanvas');
            ctx = canvas.getContext('2d');
            draw(); 

            socket = io('http://127.0.0.1:5000');

            socket.on('connect', () => {
                isConnected.value = true;
            });

            socket.on('disconnect', () => {
                isConnected.value = false;
            });

            socket.on('map_data', (data) => {
                gridWidth.value = data.width;
                gridHeight.value = data.height;
                mapGrid.value = data.grid;
                draw();
            });

            socket.on('robot_state', (data) => {
                // ЛОГІКА КРОКУ №1: Синхронізація лінії з рухом
                if (data.x !== robot.value.x || data.y !== robot.value.y) {
                    if (currentPath.value.length > 0) {
                        const nextPoint = currentPath.value[0];
                        // Якщо робот наступив на першу точку з масиву шляху — видаляємо її
                        if (data.x === nextPoint[0] && data.y === nextPoint[1]) {
                            currentPath.value.shift(); 
                        }
                    }
                }
                
                robot.value = data; // Оновлюємо позицію робота
                draw(); // Перемальовуємо канвас
            });

            socket.on('path_found', (data) => {
                currentPath.value = data.path;
                draw();
            });
            
            socket.on('path_error', (data) => {
                alert(data.message); 
            });

            socket.on('server_log', (data) => {
                logs.value.unshift(data); 
                if (logs.value.length > 50) {
                    logs.value.pop();
                }
            });
        });

        return {
            isConnected,
            robot,
            handleLeftClick,
            handleRightClick,
            emergencyStop,
            recharge,
            mazeDensity,
            clearMap,
            generateMaze,
            logs,
            showModal,
            simSpeed,
            changeSpeed
        };
    }
}).mount('#app');