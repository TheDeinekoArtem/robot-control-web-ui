/**
 * IoE Agent Control Dashboard - Frontend Logic
 * Framework: Vue 3 (Composition API)
 * Communication: Socket.io
 */

const { createApp, ref, onMounted } = Vue;

createApp({
    setup() {
        // --- REACTIVE STATE VARIABLES ---
        const isConnected = ref(false);
        const robot = ref({ x: 0, y: 0, status: 'idle', battery: 100, history: [] });
        
        // Environment State
        const gridWidth = ref(20);
        const gridHeight = ref(20);
        const mapGrid = ref([]);
        const mazeDensity = ref(20);
        
        // Navigation & Telemetry State
        const currentPath = ref([]);
        const totalDistance = ref(0);
        const pathLength = ref(0);
        const simSpeed = ref(3);
        
        // UI State
        const logs = ref([]); 
        const showModal = ref(false);

        // Internal Variables
        let canvas, ctx, socket;

        /**
         * Core Rendering Engine
         * Optimized for 60fps (Removed heavy gradients from the main grid loop)
         */
        const draw = () => {
            if (!ctx) return;
            
            const width = canvas.width;
            const height = canvas.height;
            const cellW = width / gridWidth.value;
            const cellH = height / gridHeight.value;

            // Pre-calculate robot center
            const rx = robot.value.x * cellW + cellW / 2;
            const ry = robot.value.y * cellH + cellH / 2;

            // Clear frame
            ctx.clearRect(0, 0, width, height);

            // LAYER 1: Grid & Obstacles
            ctx.strokeStyle = '#45475a';
            ctx.lineWidth = 1;
            
            for (let y = 0; y < gridHeight.value; y++) {
                for (let x = 0; x < gridWidth.value; x++) {
                    const xPos = x * cellW;
                    const yPos = y * cellH;
                    
                    ctx.strokeRect(xPos, yPos, cellW, cellH);
                    
                    if (mapGrid.value[y] && mapGrid.value[y][x] === 1) {
                        // Using static color for high performance rendering
                        ctx.fillStyle = '#cdd6f4'; 
                        ctx.fillRect(xPos + 1, yPos + 1, cellW - 2, cellH - 2);
                    }
                }
            }

            // LAYER 2: Charging Station (Base)
            ctx.save();
            ctx.shadowBlur = 15;
            ctx.shadowColor = '#f9e2af';
            
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

            // LAYER 3: Movement Trail (History)
            if (robot.value.history && robot.value.history.length > 0) {
                ctx.save();
                ctx.beginPath();
                ctx.strokeStyle = 'rgba(137, 180, 250, 0.06)'; 
                ctx.lineWidth = cellW / 2.5; 
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';

                ctx.moveTo(robot.value.history[0][0] * cellW + cellW / 2, robot.value.history[0][1] * cellH + cellH / 2);
                robot.value.history.forEach(p => ctx.lineTo(p[0] * cellW + cellW / 2, p[1] * cellH + cellH / 2));
                ctx.lineTo(rx, ry);
                ctx.stroke();
                ctx.restore();
            }

            // LAYER 4: Navigation Path & Destination Target
            if (currentPath.value.length > 0) {
                ctx.save();
                ctx.strokeStyle = '#a6e3a1'; 
                ctx.lineWidth = 4;
                ctx.shadowBlur = 12;
                ctx.shadowColor = '#a6e3a1';
                ctx.beginPath();
                ctx.moveTo(rx, ry); 

                currentPath.value.forEach(p => ctx.lineTo(p[0] * cellW + cellW / 2, p[1] * cellH + cellH / 2));
                ctx.stroke();
                ctx.restore();

                const target = currentPath.value[currentPath.value.length - 1];
                ctx.beginPath();
                ctx.arc(target[0] * cellW + cellW / 2, target[1] * cellH + cellH / 2, cellW / 3, 0, Math.PI * 2);
                ctx.strokeStyle = '#f38ba8';
                ctx.lineWidth = 3;
                ctx.stroke();
                ctx.fillStyle = 'rgba(243, 139, 168, 0.2)';
                ctx.fill();
            }

            // LAYER 5: Autonomous Agent (Robot Body)
            ctx.save();
            ctx.translate(rx, ry);
            
            if (currentPath.value.length > 0) {
                const next = currentPath.value[0];
                ctx.rotate(Math.atan2(next[1] - robot.value.y, next[0] - robot.value.x));
            } else if (robot.value.history?.length > 0) {
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

        // --- INTERACTION HANDLERS ---

        const handleLeftClick = (event) => {
            if (!isConnected.value) return;
            const rect = canvas.getBoundingClientRect();
            const x = Math.floor((event.clientX - rect.left) / (canvas.width / gridWidth.value));
            const y = Math.floor((event.clientY - rect.top) / (canvas.height / gridHeight.value));
            socket.emit('set_target', { x, y });
        };

        const handleRightClick = (event) => {
            if (!isConnected.value) return;
            const rect = canvas.getBoundingClientRect();
            const x = Math.floor((event.clientX - rect.left) / (canvas.width / gridWidth.value));
            const y = Math.floor((event.clientY - rect.top) / (canvas.height / gridHeight.value));
            
            // Immediate visual feedback: clear local path line
            currentPath.value = [];
            socket.emit('toggle_obstacle', { x, y });
        };

        // --- COMMAND EMITTERS ---

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

        /**
         * Mission Log Exporter
         * Formats mission history and triggers text file download
         */
        const exportLogs = () => {
            const reportDate = new Date().toLocaleDateString();
            const reportHeader = `IOE AGENT MISSION REPORT\nDate: ${reportDate}\n` +
                                `--------------------------\n`;
            
            const content = logs.value.map(l => `[${l.time}] ${l.message}`).join('\n');
            const blob = new Blob([reportHeader + content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            
            const timestamp = new Date().getHours() + '-' + new Date().getMinutes();
            a.href = url;
            a.download = `robot_mission_log_${timestamp}.txt`;
            a.click();
            URL.revokeObjectURL(url);
        };

        // --- LIFECYCLE HOOKS & SOCKET SETUP ---

        onMounted(() => {
            canvas = document.getElementById('gridCanvas');
            ctx = canvas.getContext('2d');
            draw(); 

            // Initialize WebSocket connection
            socket = io('http://127.0.0.1:5000');

            socket.on('connect', () => {
                isConnected.value = true;
                socket.emit('get_initial_state'); 
            });

            // Full state synchronization
            socket.on('initial_data', (data) => {
                gridWidth.value = data.width;
                gridHeight.value = data.height;
                mapGrid.value = data.grid;
                robot.value = data.robot; 
                simSpeed.value = data.speed || 3;
                totalDistance.value = data.robot.total_distance || 0;
                currentPath.value = data.currentPath || [];
                pathLength.value = currentPath.value.length;
                draw();
            });

            // Map and configuration updates
            socket.on('map_data', (data) => {
                mapGrid.value = data.grid;
                if (data.speed) simSpeed.value = data.speed; 
                draw();
            });

            // Real-time telemetry updates
            socket.on('robot_state', (data) => {
                robot.value = data;
                totalDistance.value = data.total_distance;
                currentPath.value = data.path || []; 
                pathLength.value = currentPath.value.length;
                draw();
            });

            // Pathfinding updates
            socket.on('path_found', (data) => {
                currentPath.value = data.path;
                pathLength.value = data.path.length;
                draw();
            });

            socket.on('path_error', (data) => alert(data.message));

            // System logging with semantic categorization
            socket.on('server_log', (data) => {
                let type = 'info';
                const msg = data.message;
                
                if (msg.includes('❌') || msg.includes('немає') || msg.includes('Зупинка')) {
                    type = 'error';
                } else if (msg.includes('✅') || msg.includes('🔋')) {
                    type = 'success';
                } else if (msg.includes('⚠️') || msg.includes('Перерахунок')) {
                    type = 'warning';
                }

                logs.value.unshift({ ...data, type }); 
                if (logs.value.length > 100) logs.value.pop();
            });

            socket.on('disconnect', () => isConnected.value = false);
        });

        return {
            isConnected, robot, handleLeftClick, handleRightClick, emergencyStop,
            recharge, mazeDensity, clearMap, generateMaze, logs, showModal,
            simSpeed, changeSpeed, totalDistance, pathLength, exportLogs
        };
    }
}).mount('#app');