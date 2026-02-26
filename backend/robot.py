class VirtualRobot:
    def __init__(self, start_x=0, start_y=0):
        # Поточні координати на сітці
        self.x = start_x
        self.y = start_y
        
        # Телеметрія
        self.battery = 100.0
        self.status = "idle"  # Можливі статуси: 'idle' (стоїть), 'moving' (їде), 'error' (помилка)
        
        # Маршрут, по якому він зараз їде (список координат [(x1,y1), (x2,y2), ...])
        self.path = []

    def set_path(self, new_path):
        """Отримує новий маршрут і змінює статус на 'moving'"""
        self.path = new_path
        if self.path:
            self.status = "moving"
        else:
            self.status = "idle"

    def move_step(self):
        """Робить один крок по маршруту (викликатиметься сервером кожні пів секунди)"""
        if self.status == "moving" and self.path:
            if self.battery > 0:
                # Беремо наступну точку маршруту і видаляємо її зі списку
                next_point = self.path.pop(0)
                self.x, self.y = next_point
                
                # Симуляція витрати батареї (наприклад, 0.5% за кожен крок)
                self.battery -= 0.5
                
                # Якщо точок більше немає — ми приїхали
                if not self.path:
                    self.status = "idle"
            else:
                self.status = "error" # Батарея сіла

    def get_state(self):
        """Повертає поточний стан робота у вигляді словника (зручно для відправки JSON/WebSocket)"""
        return {
            "x": self.x,
            "y": self.y,
            "battery": round(self.battery, 1), # Округлюємо до 1 знаку після коми
            "status": self.status
        }