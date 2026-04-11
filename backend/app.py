import eventlet
import random
from flask import Flask, jsonify
from flask_socketio import SocketIO
from datetime import datetime

# Import custom modules for robot logic and pathfinding
from robot import VirtualRobot
from pathfinding import astar

# Initialize eventlet for asynchronous WebSocket performance
eventlet.monkey_patch()

app = Flask(__name__)
app.config["SECRET_KEY"] = "my_secret_key"

# Initialize SocketIO with eventlet mode and CORS enabled for frontend communication
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


def send_log(message):
    """
    Broadcasts a timestamped log message to the frontend and prints it to the console.
    """
    time_str = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{time_str}] {message}"
    print(formatted_msg)
    socketio.emit("server_log", {"time": time_str, "message": message})


# --- SERVER STATE CONFIGURATION ---
# 20x20 Grid initialization (0 = free space, 1 = obstacle)
GRID_WIDTH = 20
GRID_HEIGHT = 20
grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

# Simulation timing and speed control
simulation_delay = 0.5
current_speed_level = 3

# Robot instance initialized at starting point (0, 0)
robot = VirtualRobot(start_x=0, start_y=0)

# Global variable to manage the simulation background thread
background_thread = None


def simulation_loop():
    """
    Continuous background loop that handles robot movement steps and state broadcasting.
    """
    while True:
        if robot.status == "moving":
            # Pass grid and A* algorithm to the robot for real-time energy reserve calculation
            robot.move_step(grid, astar)

        # Always broadcast the current robot state to all connected clients
        socketio.emit("robot_state", robot.get_state())
        socketio.sleep(simulation_delay)


@socketio.on("connect")
def handle_connect():
    """
    Handles new client connections. Starts the simulation thread if not already running.
    """
    global background_thread
    send_log("🟢 Клієнт (браузер) підключився!")

    if background_thread is None:
        background_thread = socketio.start_background_task(simulation_loop)

    # Send initial map configuration and speed settings to the new client
    socketio.emit(
        "map_data",
        {
            "width": GRID_WIDTH,
            "height": GRID_HEIGHT,
            "grid": grid,
            "speed": current_speed_level,
        },
    )
    socketio.emit("robot_state", robot.get_state())


@socketio.on("get_initial_state")
def handle_get_initial_state():
    """
    Provides the full current system state. Essential for UI recovery after page refresh (F5).
    """
    socketio.emit(
        "initial_data",
        {
            "width": GRID_WIDTH,
            "height": GRID_HEIGHT,
            "grid": grid,
            "robot": robot.get_state(),
            "currentPath": robot.path,
            "speed": current_speed_level,
        },
    )


@socketio.on("set_target")
def handle_set_target(data):
    """
    Processes navigation requests to specific coordinates.
    Calculates the shortest path using the A* algorithm.
    """
    target_x = data.get("x")
    target_y = data.get("y")
    start_pos = (robot.x, robot.y)
    goal_pos = (target_x, target_y)

    send_log(f"📍 Розрахунок маршруту: {start_pos} -> {goal_pos}")

    # Stop condition: if the target is the robot's current position
    if start_pos == goal_pos:
        send_log("🛑 Зупинка (ціль збігається з поточними координатами).")
        robot.set_path([])
        robot.status = "idle"
        socketio.emit("path_found", {"path": []})
        socketio.emit("robot_state", robot.get_state())
        return

    # Run pathfinding algorithm
    path = astar(grid, start_pos, goal_pos)

    if path:
        send_log(f"✅ Маршрут знайдено! Кількість кроків: {len(path)}")
        robot.set_path(path)
        socketio.emit("path_found", {"path": path})
    else:
        send_log("❌ Шляху немає (ціль недосяжна або заблокована)!")
        robot.status = "error"
        socketio.emit(
            "path_error", {"message": "Неможливо побудувати маршрут. Перешкода!"}
        )


@socketio.on("toggle_obstacle")
def handle_toggle_obstacle(data):
    """
    Allows users to manually add or remove obstacles.
    Triggers automatic rerouting if the robot is currently moving.
    """
    x, y = data.get("x"), data.get("y")

    # Safety check: prevent placing an obstacle directly on the robot
    if x == robot.x and y == robot.y:
        send_log("⚠️ Спроба поставити стіну на робота! Ігноруємо.")
        socketio.emit(
            "path_error", {"message": "Неможливо поставити перешкоду на робота!"}
        )
        return

    if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
        # Toggle grid cell state
        grid[y][x] = 1 if grid[y][x] == 0 else 0
        send_log(f"🧱 Перешкода змінена в ({x}, {y})")

        # Broadcast updated map to all clients
        socketio.emit(
            "map_data", {"width": GRID_WIDTH, "height": GRID_HEIGHT, "grid": grid}
        )

        # Dynamic Rerouting: Recalculate path if the robot's current route is affected
        if robot.status == "moving" and robot.path:
            target = robot.path[-1]
            start_pos = (robot.x, robot.y)

            send_log(f"🔄 Перерахунок маршруту до {target}...")
            new_path = astar(grid, start_pos, target)

            if new_path:
                send_log("✅ Знайдено новий шлях в обхід!")
                robot.set_path(new_path)
                socketio.emit("path_found", {"path": new_path})
            else:
                send_log("❌ Шлях повністю заблоковано стінами.")
                robot.set_path([])
                robot.status = "error"
                socketio.emit("path_found", {"path": []})
                socketio.emit(
                    "path_error",
                    {"message": "Шлях заблоковано! Робот не може дістатися цілі."},
                )


@socketio.on("recharge")
def handle_recharge():
    """
    Commands the robot to return to the charging station at (0, 0).
    """
    send_log("🔋 Команда: Повернення на базу!")
    start_pos = (robot.x, robot.y)
    goal_pos = (0, 0)

    if start_pos == goal_pos:
        robot.battery = 100.0
        robot.status = "idle"
        socketio.emit("robot_state", robot.get_state())
        return

    path = astar(grid, start_pos, goal_pos)
    if path:
        robot.set_path(path)
        socketio.emit("path_found", {"path": path})
    else:
        socketio.emit(
            "path_error", {"message": "База недоступна! Шлях заблоковано стінами."}
        )


@socketio.on("clear_map")
def handle_clear_map():
    """
    Resets the entire grid to an empty state and updates active routes.
    """
    global grid
    send_log("🧹 Очищення карти...")
    grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    socketio.emit(
        "map_data",
        {
            "width": GRID_WIDTH,
            "height": GRID_HEIGHT,
            "grid": grid,
            "speed": current_speed_level,
        },
    )

    # Recalculate straight-line path if robot was moving
    if robot.status == "moving" and robot.path:
        target = robot.path[-1]
        new_path = astar(grid, (robot.x, robot.y), target)
        if new_path:
            robot.set_path(new_path)
            socketio.emit("path_found", {"path": new_path})


@socketio.on("generate_maze")
def handle_generate_maze(data):
    """
    Procedurally generates random obstacles with a given density.
    Ensures that the base, the robot, and the current target remain accessible.
    """
    global grid
    density = data.get("density", 0.2)
    send_log(f"🎲 Генерація лабіринту (щільність {int(density*100)}%)...")

    target = robot.path[-1] if robot.path else None

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            # Protective check: skip base, robot position, and current target
            if (
                (x == 0 and y == 0)
                or (x == robot.x and y == robot.y)
                or (target and x == target[0] and y == target[1])
            ):
                grid[y][x] = 0
            else:
                grid[y][x] = 1 if random.random() < density else 0

    socketio.emit(
        "map_data",
        {
            "width": GRID_WIDTH,
            "height": GRID_HEIGHT,
            "grid": grid,
            "speed": current_speed_level,
        },
    )

    # Update path finding through the new maze
    if robot.status == "moving" and target:
        new_path = astar(grid, (robot.x, robot.y), target)
        if new_path:
            robot.set_path(new_path)
            socketio.emit("path_found", {"path": new_path})
        else:
            robot.set_path([])
            robot.status = "error"
            socketio.emit("path_found", {"path": []})
            send_log("❌ Згенерований лабіринт заблокував шлях!")


@socketio.on("set_speed")
def handle_set_speed(data):
    """
    Adjusts the simulation speed level (1 to 5) by modifying the loop delay.
    """
    global simulation_delay, current_speed_level
    speed_level = int(data.get("speed", 3))
    current_speed_level = speed_level

    # Speed to delay mapping: 1 = slowest (1s), 5 = turbo (0.1s)
    delays = {1: 1.0, 2: 0.75, 3: 0.5, 4: 0.25, 5: 0.1}
    simulation_delay = delays.get(speed_level, 0.5)

    send_log(f"⚡ Швидкість симуляції змінено на рівень {speed_level}/5")


if __name__ == "__main__":
    print("🚀 WebSocket Server starting on http://127.0.0.1:5000...")
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
