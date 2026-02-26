import heapq
import math

def heuristic(a, b):
    """
    Евристика: Евклідова відстань (по прямій).
    Краще підходить для сітки з діагональним рухом.
    """
    return math.hypot(a[0] - b[0], a[1] - b[1])

def astar(grid, start, goal):
    rows = len(grid)
    cols = len(grid[0])
    
    if not (0 <= start[0] < cols and 0 <= start[1] < rows): return []
    if not (0 <= goal[0] < cols and 0 <= goal[1] < rows): return []
    if grid[start[1]][start[0]] == 1 or grid[goal[1]][goal[0]] == 1:
        return []

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}
    
    # Напрямки: (dx, dy, вартість_кроку)
    directions = [
        # Прямі кроки (вартість 1)
        (0, -1, 1), (0, 1, 1), (-1, 0, 1), (1, 0, 1),
        # Діагональні кроки (вартість ~1.414)
        (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)
    ]
    
    while open_set:
        current = heapq.heappop(open_set)[1]
        
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path
            
        for dx, dy, cost in directions:
            nx, ny = current[0] + dx, current[1] + dy
            neighbor = (nx, ny)
            
            if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] == 0:
                
                # БОНУС: Заборона "зрізати кути". 
                # Якщо йдемо по діагоналі, перевіряємо чи не заблоковані сусідні прямі клітинки
                if cost > 1: 
                    if grid[current[1]][nx] == 1 or grid[ny][current[0]] == 1:
                        continue # Кут заблоковано, цей шлях неможливий
                
                tentative_g_score = g_score[current] + cost
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
                    
    return []