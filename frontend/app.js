const { createApp, ref, onMounted } = Vue;

createApp({
    setup() {
        // --- РЕАКТИВНІ ЗМІННІ ---
        // Ці змінні автоматично оновлюють HTML, коли змінюються
        const isConnected = ref(false);
        const robot = ref({ x: 0, y: 0, status: 'idle', battery: 100 });
        
        // Змінні для карти
        const gridWidth = ref(20);
        const gridHeight = ref(20);
        const mapGrid = ref([]);
        const currentPath = ref([]);

        let canvas, ctx, socket;

        // --- ФУНКЦІЯ МАЛЮВАННЯ НА CANVAS ---
        const draw = () => {
            if (!ctx) return;
            
            const width = canvas.width;
            const height = canvas.height;
            const cellW = width / gridWidth.value;
            const cellH = height / gridHeight.value;

            // Очищаємо екран перед новим кадром
            ctx.clearRect(0, 0, width, height);

            // 1. Малюємо сітку та перешкоди
            for (let y = 0; y < gridHeight.value; y++) {
                for (let x = 0; x < gridWidth.value; x++) {
                    // Малюємо контур клітинки
                    ctx.strokeStyle = '#45475a';
                    ctx.lineWidth = 1;
                    ctx.strokeRect(x * cellW, y * cellH, cellW, cellH);
                    
                    // Якщо це стіна (1), зафарбовуємо її
                    if (mapGrid.value[y] && mapGrid.value[y][x] === 1) {
                        ctx.fillStyle = '#cdd6f4'; // Світлий колір стіни
                        ctx.fillRect(x * cellW, y * cellH, cellW, cellH);
                    }
                }
            }

            // 2. Малюємо знайдений маршрут (зелена лінія)
            if (currentPath.value.length > 0) {
                ctx.strokeStyle = '#a6e3a1'; 
                ctx.lineWidth = 4;
                ctx.beginPath();
                currentPath.value.forEach((point, index) => {
                    // Рахуємо центр клітинки
                    const cx = point[0] * cellW + cellW / 2;
                    const cy = point[1] * cellH + cellH / 2;
                    if (index === 0) ctx.moveTo(cx, cy);
                    else ctx.lineTo(cx, cy);
                });
                ctx.stroke();
            }

            // 3. Малюємо робота (синій круг)
            const rx = robot.value.x * cellW + cellW / 2;
            const ry = robot.value.y * cellH + cellH / 2;
            
            ctx.fillStyle = '#89b4fa';
            ctx.beginPath();
            ctx.arc(rx, ry, cellW / 2.5, 0, Math.PI * 2);
            ctx.fill();
        };

        // --- ОБРОБНИКИ КЛІКІВ МИШІ ---
        const handleLeftClick = (event) => {
            if (!isConnected.value) return;
            const rect = canvas.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            
            // Вираховуємо індекс клітинки, по якій клікнули
            const cellX = Math.floor(x / (canvas.width / gridWidth.value));
            const cellY = Math.floor(y / (canvas.height / gridHeight.value));
            
            console.log(`🎯 Ціль: (${cellX}, ${cellY})`);
            socket.emit('set_target', { x: cellX, y: cellY });
        };

        const handleRightClick = (event) => {
            if (!isConnected.value) return;
            const rect = canvas.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            
            const cellX = Math.floor(x / (canvas.width / gridWidth.value));
            const cellY = Math.floor(y / (canvas.height / gridHeight.value));
            
            console.log(`🧱 Перешкода: (${cellX}, ${cellY})`);
            socket.emit('toggle_obstacle', { x: cellX, y: cellY });
        };

        const emergencyStop = () => {
            if (!isConnected.value) return;
            // Відправляємо робота в його ж поточну точку, щоб він зупинився
            socket.emit('set_target', { x: robot.value.x, y: robot.value.y });
        };

        const recharge = () => {
            if (!isConnected.value) return;
            socket.emit('recharge');
        };

        // --- ІНІЦІАЛІЗАЦІЯ ПРИ ЗАВАНТАЖЕННІ СТОРІНКИ ---
        onMounted(() => {
            canvas = document.getElementById('gridCanvas');
            ctx = canvas.getContext('2d');
            draw(); // Малюємо порожню сітку до підключення

            // Підключаємося до нашого Python сервера
            socket = io('http://127.0.0.1:5000');

            socket.on('connect', () => {
                isConnected.value = true;
                console.log("З'єднано з сервером!");
            });

            socket.on('disconnect', () => {
                isConnected.value = false;
            });

            // Коли сервер надсилає нову карту (після встановлення стіни)
            socket.on('map_data', (data) => {
                gridWidth.value = data.width;
                gridHeight.value = data.height;
                mapGrid.value = data.grid;
                draw();
            });

            // Коли сервер надсилає поточний стан робота (кожні 0.5с)
            socket.on('robot_state', (data) => {
                robot.value = data;
                if (data.status === 'idle') {
                    currentPath.value = []; // Очищаємо зелену лінію, якщо приїхали
                }
                draw();
            });

            // Коли сервер розрахував новий маршрут
            socket.on('path_found', (data) => {
                currentPath.value = data.path;
                draw();
            });
            
            // Якщо сервер каже, що маршрут неможливий
            socket.on('path_error', (data) => {
                alert(data.message); // Виводимо спливаюче вікно з помилкою
            });
        });

        return {
            isConnected,
            robot,
            handleLeftClick,
            handleRightClick,
            emergencyStop
            recharge
        };
    }
}).mount('#app');