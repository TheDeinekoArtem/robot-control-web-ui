import eventlet
eventlet.monkey_patch() # Важливо для асинхронної роботи WebSocket

from flask import Flask, jsonify
from flask_socketio import SocketIO

# Імпортуємо наші власні модулі
from robot import VirtualRobot
from pathfinding import astar

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_secret_key'
# Вказуємо async_mode='eventlet' для максимальної продуктивності
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- СТАН СЕРВЕРА ---
# Створюємо карту 20x20. Початково вся заповнена нулями (вільно).
GRID_WIDTH = 20
GRID_HEIGHT = 20
grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

# Створюємо нашого робота у стартовій точці (0, 0)
robot = VirtualRobot(start_x=0, start_y=0)

# Змінна для збереження фонового потоку симуляції
background_thread = None

def simulation_loop():
    """Фоновий цикл, який постійно працює на сервері"""
    while True:
        if robot.status == "moving":
            robot.move_step() # Робимо один крок
        
        # Відправляємо поточний стан (навіть якщо стоїть) усім підключеним браузерам
        socketio.emit('robot_state', robot.get_state())
        
        # Чекаємо 0.5 секунди перед наступним кроком (швидкість робота)
        socketio.sleep(0.5) 

@socketio.on('connect')
def handle_connect():
    global background_thread
    print("🟢 Клієнт (браузер) підключився!")
    
    # Запускаємо фоновий цикл симуляції при першому підключенні
    if background_thread is None:
        background_thread = socketio.start_background_task(simulation_loop)
        
    # Відправляємо клієнту розміри карти та саму матрицю з перешкодами
    socketio.emit('map_data', {'width': GRID_WIDTH, 'height': GRID_HEIGHT, 'grid': grid})
    socketio.emit('robot_state', robot.get_state())

@socketio.on('set_target')
def handle_set_target(data):
    """Отримуємо координати від клієнта, куди треба поїхати"""
    target_x = data.get('x')
    target_y = data.get('y')
    
    start_pos = (robot.x, robot.y)
    goal_pos = (target_x, target_y)
    print(f"📍 Розрахунок маршруту: {start_pos} -> {goal_pos}")
    
    # Викликаємо наш алгоритм A*
    path = astar(grid, start_pos, goal_pos)
    
    if path:
        print(f"✅ Маршрут знайдено! Кількість кроків: {len(path)}")
        robot.set_path(path)
        # Відправляємо маршрут на фронтенд, щоб намалювати зелену лінію
        socketio.emit('path_found', {'path': path})
    else:
        print("❌ Шляху немає (ціль недосяжна або заблокована)!")
        robot.status = "error"
        socketio.emit('path_error', {'message': 'Неможливо побудувати маршрут. Перешкода!'})

@socketio.on('toggle_obstacle')
def handle_toggle_obstacle(data):
    """Обробляємо клік користувача для встановлення/видалення стіни"""
    x = data.get('x')
    y = data.get('y')
    
    if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
        # Змінюємо 0 на 1, або 1 на 0 (перемикач)
        grid[y][x] = 1 if grid[y][x] == 0 else 0
        print(f"🧱 Перешкода змінена в координатах ({x}, {y})")
        
        # Відправляємо оновлену карту всім
        socketio.emit('map_data', {'width': GRID_WIDTH, 'height': GRID_HEIGHT, 'grid': grid})
        
        # Логіка безпеки: якщо робот їхав і хтось поставив стіну - зупиняємо його
        if robot.status == "moving":
            robot.set_path([])
            robot.status = "idle"
            print("⚠️ Робот екстрено зупинений через зміну карти.")

if __name__ == '__main__':
    print("🚀 Запуск WebSocket сервера на http://127.0.0.1:5000...")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)