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
        """Робить один крок по маршруту"""
        if self.status == "moving" and self.path:
            if self.battery > 0:
                prev_x, prev_y = self.x, self.y
                next_point = self.path.pop(0)
                self.x, self.y = next_point
                
                # РІЗНЕ СПОЖИВАННЯ ЕНЕРГІЇ
                is_diagonal = abs(self.x - prev_x) == 1 and abs(self.y - prev_y) == 1
                self.battery -= (0.7 if is_diagonal else 0.5)
                
                if not self.path:
                    self.status = "idle"
                    
                # Якщо приїхали на базу (0, 0) - автоматично заряджаємось
                if self.x == 0 and self.y == 0:
                    self.battery = 100.0
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