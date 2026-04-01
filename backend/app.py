import eventlet

eventlet.monkey_patch()  # Важливо для асинхронної роботи WebSocket

from flask import Flask, jsonify
from flask_socketio import SocketIO

# Імпортуємо наші власні модулі
from robot import VirtualRobot
from pathfinding import astar

app = Flask(__name__)
app.config["SECRET_KEY"] = "my_secret_key"
# Вказуємо async_mode='eventlet' для максимальної продуктивності
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

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
            # Передаємо карту та алгоритм роботу для точного розрахунку резерву
            robot.move_step(grid, astar)

        socketio.emit("robot_state", robot.get_state())
        socketio.sleep(0.5)


@socketio.on("connect")
def handle_connect():
    global background_thread
    print("🟢 Клієнт (браузер) підключився!")

    # Запускаємо фоновий цикл симуляції при першому підключенні
    if background_thread is None:
        background_thread = socketio.start_background_task(simulation_loop)

    # Відправляємо клієнту розміри карти та саму матрицю з перешкодами
    socketio.emit(
        "map_data", {"width": GRID_WIDTH, "height": GRID_HEIGHT, "grid": grid}
    )
    socketio.emit("robot_state", robot.get_state())


@socketio.on("set_target")
def handle_set_target(data):
    """Отримуємо координати від клієнта, куди треба поїхати"""
    target_x = data.get("x")
    target_y = data.get("y")

    start_pos = (robot.x, robot.y)
    goal_pos = (target_x, target_y)
    print(f"📍 Розрахунок маршруту: {start_pos} -> {goal_pos}")

    # Викликаємо наш алгоритм A*
    path = astar(grid, start_pos, goal_pos)

    if path:
        print(f"✅ Маршрут знайдено! Кількість кроків: {len(path)}")
        robot.set_path(path)
        # Відправляємо маршрут на фронтенд, щоб намалювати зелену лінію
        socketio.emit("path_found", {"path": path})
    else:
        print("❌ Шляху немає (ціль недосяжна або заблокована)!")
        robot.status = "error"
        socketio.emit(
            "path_error", {"message": "Неможливо побудувати маршрут. Перешкода!"}
        )


@socketio.on("toggle_obstacle")
def handle_toggle_obstacle(data):
    """Обробляємо клік користувача для встановлення/видалення стіни"""
    x = data.get("x")
    y = data.get("y")

    # ЗАХИСТ: Не дозволяємо ставити стіну прямо на робота!
    if x == robot.x and y == robot.y:
        print("⚠️ Спроба поставити стіну на робота! Ігноруємо.")
        socketio.emit(
            "path_error", {"message": "Неможливо поставити перешкоду на робота!"}
        )
        return

    if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
        grid[y][x] = 1 if grid[y][x] == 0 else 0
        print(f"🧱 Перешкода змінена в ({x}, {y})")

        # Відправляємо оновлену карту всім
        socketio.emit(
            "map_data", {"width": GRID_WIDTH, "height": GRID_HEIGHT, "grid": grid}
        )

        # РОЗУМНИЙ ПЕРЕРАХУНОК МАРШРУТУ
        if robot.status == "moving" and robot.path:
            target = robot.path[-1]  # Кінцева ціль (остання точка масиву)
            start_pos = (robot.x, robot.y)  # Де робот зараз

            print(f"🔄 Перерахунок маршруту до {target}...")
            new_path = astar(grid, start_pos, target)

            if new_path:
                print("✅ Знайдено новий шлях в обхід!")
                robot.set_path(new_path)
                socketio.emit("path_found", {"path": new_path})
            else:
                print("❌ Шлях повністю заблоковано стінами.")
                robot.set_path([])
                robot.status = "error"
                socketio.emit("path_found", {"path": []})  # Прибираємо зелену лінію
                socketio.emit(
                    "path_error",
                    {"message": "Шлях заблоковано! Робот не може дістатися цілі."},
                )


@socketio.on("recharge")
def handle_recharge():
    """Відправляє робота на базу (0, 0) для підзарядки"""
    print("🔋 Команда: Повернення на базу!")

    start_pos = (robot.x, robot.y)
    goal_pos = (0, 0)  # Координати нашої бази

    if start_pos == goal_pos:
        # Якщо вже на базі
        robot.battery = 100.0
        robot.status = "idle"
        socketio.emit("robot_state", robot.get_state())
        return

    # Будуємо маршрут на базу
    path = astar(grid, start_pos, goal_pos)
    if path:
        robot.set_path(path)
        socketio.emit("path_found", {"path": path})
    else:
        socketio.emit(
            "path_error", {"message": "База недоступна! Шлях заблоковано стінами."}
        )


if __name__ == "__main__":
    print("🚀 Запуск WebSocket сервера на http://127.0.0.1:5000...")
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
