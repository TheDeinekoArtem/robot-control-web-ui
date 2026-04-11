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

        const totalDistance = ref(0);
        const pathLength = ref(0);

        let canvas, ctx, socket;

        // --- ФУНКЦІЯ МАЛЮВАННЯ НА CANVAS (Крок 5: Сучасний візуал) ---
       // --- ФУНКЦІЯ МАЛЮВАННЯ НА CANVAS (Фінальний візуал + Fixed Logic) ---
        const draw = () => {
            if (!ctx) return;
            
            const width = canvas.width;
            const height = canvas.height;
            const cellW = width / gridWidth.value;
            const cellH = height / gridHeight.value;

            // 0. Розраховуємо координати робота ВІДРАЗУ, щоб всі блоки їх бачили
            const rx = robot.value.x * cellW + cellW / 2;
            const ry = robot.value.y * cellH + cellH / 2;

            ctx.clearRect(0, 0, width, height);

            // 1. СІТКА ТА СТІНИ
            for (let y = 0; y < gridHeight.value; y++) {
                for (let x = 0; x < gridWidth.value; x++) {
                    ctx.strokeStyle = '#45475a';
                    ctx.lineWidth = 1;
                    ctx.strokeRect(x * cellW, y * cellH, cellW, cellH);
                    
                    if (mapGrid.value[y] && mapGrid.value[y][x] === 1) {
                        let wallGrd = ctx.createLinearGradient(x * cellW, y * cellH, (x + 1) * cellW, (y + 1) * cellH);
                        wallGrd.addColorStop(0, '#cdd6f4');
                        wallGrd.addColorStop(1, '#a6adc8');
                        ctx.fillStyle = wallGrd; 
                        ctx.fillRect(x * cellW + 1, y * cellH + 1, cellW - 2, cellH - 2);
                    }
                }
            }

            // 2. СУЧАСНА БАЗА (Зарядна станція 0,0)
            ctx.save();
            ctx.shadowBlur = 15;
            ctx.shadowColor = '#f9e2af';
            
            // Градієнт для ефекту скляної панелі
            let baseGrd = ctx.createLinearGradient(4, 4, cellW - 4, cellH - 4);
            baseGrd.addColorStop(0, '#f9e2af');
            baseGrd.addColorStop(0.5, '#fdf1d6');
            baseGrd.addColorStop(1, '#fab387');

            ctx.fillStyle = baseGrd;
            if (ctx.roundRect) {
                ctx.beginPath();
                ctx.roundRect(4, 4, cellW - 8, cellH - 8, 8);
                ctx.fill();
            } else {
                ctx.fillRect(4, 4, cellW - 8, cellH - 8);
            }

            ctx.strokeStyle = 'rgba(17, 17, 27, 0.4)';
            ctx.lineWidth = 1.5;
            ctx.stroke();

            ctx.shadowBlur = 0;
            ctx.fillStyle = '#11111b';
            ctx.font = `bold ${cellH / 1.7}px "Segoe UI Symbol", Arial`;
            ctx.textAlign = 'center';
            ctx.fillText('⚡', cellW / 2 + 1, cellH / 1.35 + 1); 
            ctx.restore();

            // 3. СЛІД (Trail)
            if (robot.value.history && robot.value.history.length > 0) {
                ctx.beginPath();
                ctx.strokeStyle = 'rgba(137, 180, 250, 0.06)'; 
                ctx.lineWidth = cellW / 2.5; 
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';

                ctx.moveTo(robot.value.history[0][0] * cellW + cellW / 2, robot.value.history[0][1] * cellH + cellH / 2);
                for (let i = 1; i < robot.value.history.length; i++) {
                    ctx.lineTo(robot.value.history[i][0] * cellW + cellW / 2, robot.value.history[i][1] * cellH + cellH / 2);
                }
                ctx.lineTo(rx, ry);
                ctx.stroke();
            }

            // 4. МАРШРУТ ТА ЦІЛЬ
            if (currentPath.value.length > 0) {
                ctx.strokeStyle = '#a6e3a1'; 
                ctx.lineWidth = 4;
                ctx.shadowBlur = 12;
                ctx.shadowColor = '#a6e3a1';
                ctx.beginPath();
                ctx.moveTo(rx, ry); 

                currentPath.value.forEach((point) => {
                    ctx.lineTo(point[0] * cellW + cellW / 2, point[1] * cellH + cellH / 2);
                });
                ctx.stroke();
                ctx.shadowBlur = 0;

                const target = currentPath.value[currentPath.value.length - 1];
                ctx.beginPath();
                ctx.arc(target[0] * cellW + cellW / 2, target[1] * cellH + cellH / 2, cellW / 3, 0, Math.PI * 2);
                ctx.strokeStyle = '#f38ba8';
                ctx.lineWidth = 3;
                ctx.stroke();
                ctx.fillStyle = 'rgba(243, 139, 168, 0.2)';
                ctx.fill();
            }

            // 5. РОБОТ (Agent)
            ctx.save();
            ctx.translate(rx, ry);
            
            if (currentPath.value.length > 0) {
                const next = currentPath.value[0];
                ctx.rotate(Math.atan2(next[1] - robot.value.y, next[0] - robot.value.x));
            } else if (robot.value.history && robot.value.history.length > 0) {
                const last = robot.value.history[robot.value.history.length - 1];
                if (last[0] !== robot.value.x || last[1] !== robot.value.y) {
                    ctx.rotate(Math.atan2(robot.value.y - last[1], robot.value.x - last[0]));
                }
            }

            let robotGrd = ctx.createRadialGradient(0, 0, 2, 0, 0, cellW / 2.5);
            robotGrd.addColorStop(0, '#b4befe');
            robotGrd.addColorStop(1, '#89b4fa');
            
            ctx.fillStyle = robotGrd;
            ctx.shadowBlur = 15;
            ctx.shadowColor = '#89b4fa';
            ctx.beginPath();
            ctx.arc(0, 0, cellW / 2.5, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;

            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.moveTo(cellW / 6, 0);
            ctx.lineTo(-cellW / 10, -cellW / 10);
            ctx.lineTo(-cellW / 10, cellW / 10);
            ctx.fill();
            
            ctx.restore();
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
            // Запитуємо повний стан системи відразу після з'єднання
            socket.emit('get_initial_state'); 
             });

           // 1. Обробка початкових даних (F5 Sync)
            socket.on('initial_data', (data) => {
                gridWidth.value = data.width;
                gridHeight.value = data.height;
                mapGrid.value = data.grid;
                robot.value = data.robot; 
                
                // ВІДНОВЛЮЄМО ШВИДКІСТЬ ПРИ F5
                if (data.speed) {
                    simSpeed.value = data.speed;
                }
                
                // ВІДНОВЛЮЄМО ПРОБІГ ПРИ F5
                totalDistance.value = data.robot.total_distance || 0; 

                if (data.currentPath) {
                    currentPath.value = data.currentPath;
                    pathLength.value = data.currentPath.length;
                }
                draw();
            });

            socket.on('map_data', (data) => {
                gridWidth.value = data.width;
                gridHeight.value = data.height;
                mapGrid.value = data.grid;
                
                // Якщо сервер прислав швидкість разом із картою — оновлюємо її
                if (data.speed) {
                    simSpeed.value = data.speed; 
                }
                
                draw(); // Малюємо нові перешкоди!
            });

            // 1. Оновлюємо стан робота (СЛУХАЄМО ТІЛЬКИ СЕРВЕР)
            socket.on('robot_state', (data) => {
                robot.value = data;
                totalDistance.value = data.total_distance;
                
                // Беремо шлях напряму з бекенда. Більше ніяких умов!
                currentPath.value = data.path || []; 
                pathLength.value = currentPath.value.length;
                
                draw();
            });

            // 2. Рахуємо довжину маршруту, коли він знайдений
            socket.on('path_found', (data) => {
                currentPath.value = data.path;
                pathLength.value = data.path.length;
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
            changeSpeed,
            totalDistance, 
            pathLength
        };
    }
}).mount('#app');