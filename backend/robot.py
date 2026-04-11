class VirtualRobot:
    """
    Represents the autonomous agent with energy management and movement logic.
    """

    def __init__(self, start_x=0, start_y=0):
        self.x = start_x
        self.y = start_y
        self.battery = 100.0
        self.status = "idle"
        self.path = []
        self.history = []
        self.total_distance = 0

    def set_path(self, new_path):
        """Updates the robot's target path and status."""
        self.path = new_path
        self.status = "moving" if self.path else "idle"

    def move_step(self, grid=None, astar_func=None):
        """
        Executes a single step along the path with precise energy control and safety checks.
        """
        if self.status == "moving" and self.path:
            next_point = self.path[0]

            # Determine if movement is diagonal for accurate energy consumption
            is_diagonal = (
                abs(next_point[0] - self.x) == 1 and abs(next_point[1] - self.y) == 1
            )
            step_cost = 0.7 if is_diagonal else 0.5

            is_going_home = len(self.path) > 0 and self.path[-1] == (0, 0)

            # SAFETY LOCK: Prevent battery from dropping below zero
            if self.battery - step_cost <= 0:
                self.battery = 0.0
                self.status = "error"
                self.path = []
                return

            # SMART RESERVE: Home path simulation
            # If not heading home, calculate if enough battery remains for a safe return
            if not is_going_home and grid and astar_func:
                # Simulate path from the NEXT point to base (0,0)
                home_path = astar_func(grid, next_point, (0, 0))

                if home_path is None or len(home_path) == 0:
                    # Block movement if it leads to an unreachable base state
                    self.status = "error"
                    self.path = []
                    return
                else:
                    # Calculate exact energy cost for the return journey
                    cost_home = 0
                    curr = next_point
                    for p in home_path:
                        is_diag = abs(p[0] - curr[0]) == 1 and abs(p[1] - curr[1]) == 1
                        cost_home += 0.7 if is_diag else 0.5
                        curr = p

                    # Abort mission if battery falls below return cost + 1% buffer
                    if self.battery - step_cost < cost_home + 1.0:
                        print(
                            f"⚠️ RESERVE ALERT! Required: {cost_home:.1f}%, Remaining: {self.battery - step_cost:.1f}%"
                        )
                        self.status = "error"
                        self.path = []
                        return

            # Execute physical movement after all safety validations
            if not self.history or self.history[-1] != (self.x, self.y):
                self.history.append((self.x, self.y))

            self.x, self.y = next_point
            self.path.pop(0)
            self.battery -= step_cost
            self.total_distance += 1

            if not self.path:
                self.status = "idle"

            # Base recharge logic: Auto-refill battery when at (0, 0)
            if self.x == 0 and self.y == 0:
                self.battery = 100.0

    def get_state(self):
        """Returns the current telemetry and state of the robot."""
        return {
            "x": self.x,
            "y": self.y,
            "battery": round(self.battery, 1),
            "status": self.status,
            "history": self.history,
            "total_distance": self.total_distance,
            "path": self.path,
        }
