class VirtualRobot:
    def __init__(self, start_x=0, start_y=0):
        # Поточні координати на сітці
        self.x = start_x
        self.y = start_y

        # Телеметрія
        self.battery = 100.0
        self.status = (
            "idle"  # 'idle' (стоїть), 'moving' (їде), 'error' (помилка/розряджений)
        )

        # Маршрут
        self.path = []
        self.history = []

    def set_path(self, new_path):
        """Отримує новий маршрут і змінює статус на 'moving'"""
        self.path = new_path
        if self.path:
            self.status = "moving"
        else:
            self.status = "idle"

    def calculate_reserve(self, target_x, target_y):
        """
        Розраховує мінімально необхідний заряд для повернення на базу (0,0).
        Враховує діагональні (0.7) та прямі (0.5) кроки.
        """
        diag_steps = min(target_x, target_y)
        straight_steps = abs(target_x - target_y)

        # Точний розрахунок ідеального шляху додому + 2.0% буферної енергії на обхід можливих перешкод
        return (diag_steps * 0.7) + (straight_steps * 0.5) + 2.0

    def move_step(self):
        """Робить один крок по маршруту з розумним контролем енергії"""
        if self.status == "moving" and self.path:
            next_point = self.path[0]
            is_diagonal = (
                abs(next_point[0] - self.x) == 1 and abs(next_point[1] - self.y) == 1
            )
            step_cost = 0.7 if is_diagonal else 0.5

            # Визначаємо, чи їде робот зараз на базу
            is_going_home = len(self.path) > 0 and self.path[-1] == (0, 0)

            # Розраховуємо резерв для НАСТУПНОЇ точки
            reserve_needed = self.calculate_reserve(next_point[0], next_point[1])

            # ЗАХИСТ 1: Розумний резерв (діє, тільки якщо ми їдемо у справах, а не на підзарядку)
            if not is_going_home and (self.battery - step_cost < reserve_needed):
                print(
                    f"⚠️ Батарея ({self.battery:.1f}%) наближається до резерву ({reserve_needed:.1f}%). Зупинка!"
                )
                self.status = "error"
                self.path = []  # Скасовуємо місію, щоб не вмерти в дорозі
                return

            # ЗАХИСТ 2: Фізичний нуль (щоб батарея ніколи не була від'ємною, навіть по дорозі додому)
            if self.battery - step_cost < 0:
                self.battery = 0.0
                self.status = "error"
                self.path = []
                return

            # Якщо всі перевірки пройдені — робимо крок
            if (self.x, self.y) not in self.history:
                self.history.append((self.x, self.y))

            self.x, self.y = next_point
            self.path.pop(0)
            self.battery -= step_cost

            if not self.path:
                self.status = "idle"

            # Якщо приїхали на базу (0, 0) - заряджаємось і стираємо хвіст
            if self.x == 0 and self.y == 0:
                self.battery = 100.0
                self.history = []

    def get_state(self):
        """Повертає поточний стан робота"""
        return {
            "x": self.x,
            "y": self.y,
            "battery": round(self.battery, 1),
            "status": self.status,
            "history": self.history,
        }
