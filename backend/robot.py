class VirtualRobot:
    def __init__(self, start_x=0, start_y=0):
        self.x = start_x
        self.y = start_y
        self.battery = 100.0
        self.status = "idle"
        self.path = []
        self.history = []

    def set_path(self, new_path):
        self.path = new_path
        if self.path:
            self.status = "moving"
        else:
            self.status = "idle"

    def move_step(self, grid=None, astar_func=None):
        """Робить один крок по маршруту з 100% точним контролем енергії"""
        if self.status == "moving" and self.path:
            next_point = self.path[0]
            is_diagonal = (
                abs(next_point[0] - self.x) == 1 and abs(next_point[1] - self.y) == 1
            )
            step_cost = 0.7 if is_diagonal else 0.5

            is_going_home = len(self.path) > 0 and self.path[-1] == (0, 0)

            # ЖОРСТКИЙ ЗАХИСТ: Батарея ніколи не буде мінусовою
            if self.battery - step_cost <= 0:
                self.battery = 0.0
                self.status = "error"
                self.path = []
                return

            # РОЗУМНИЙ РЕЗЕРВ: Симуляція шляху додому
            if not is_going_home and grid and astar_func:
                # Будуємо віртуальний шлях від НАСТУПНОЇ точки до бази (0,0)
                home_path = astar_func(grid, next_point, (0, 0))

                if home_path is None or len(home_path) == 0:
                    # Якщо робот бачить, що наступний крок заблокує йому шлях додому
                    self.status = "error"
                    self.path = []
                    return
                else:
                    # Рахуємо точну вартість віртуального шляху додому
                    cost_home = 0
                    curr = next_point
                    for p in home_path:
                        is_diag = abs(p[0] - curr[0]) == 1 and abs(p[1] - curr[1]) == 1
                        cost_home += 0.7 if is_diag else 0.5
                        curr = p

                    # Якщо після кроку заряду не вистачить на шлях додому + 1% буфер
                    if self.battery - step_cost < cost_home + 1.0:
                        print(
                            f"⚠️ РЕЗЕРВ! Потрібно: {cost_home:.1f}%, Залишок: {self.battery - step_cost:.1f}%"
                        )
                        self.status = "error"
                        self.path = []
                        return

            # Якщо всі перевірки пройдені — фізично робимо крок
            # Записуємо крок завжди, якщо це нова точка відносно ОСТАННЬОГО кроку
            if not self.history or self.history[-1] != (self.x, self.y):
                self.history.append((self.x, self.y))

            self.x, self.y = next_point
            self.path.pop(0)
            self.battery -= step_cost

            if not self.path:
                self.status = "idle"

            # Якщо приїхали на базу (0, 0) - заряджаємось (хвіст НЕ очищаємо!)
            if self.x == 0 and self.y == 0:
                self.battery = 100.0

    def get_state(self):
        return {
            "x": self.x,
            "y": self.y,
            "battery": round(self.battery, 1),
            "status": self.status,
            "history": self.history,
        }
