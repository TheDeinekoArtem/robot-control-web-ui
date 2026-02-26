import heapq

def heuristic(a, b):
    """
    Евристична функція: Манхеттенська відстань.
    Розраховує приблизну відстань між двома точками на сітці, 
    де можна рухатися лише по горизонталі та вертикалі.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(grid, start, goal):
    """
    Алгоритм A* для пошуку найкоротшого шляху на 2D сітці.
    :param grid: двовимірний масив (список списків), де 0 - вільно, 1 - перешкода.
    :param start: кортеж (x, y) - початкова точка.
    :param goal: кортеж (x, y) - кінцева точка.
    :return: список координат [(x1,y1), (x2,y2)...] або порожній список, якщо шляху немає.
    """
    rows = len(grid)
    cols = len(grid[0])
    
    # Перевірка: чи не виходять старт/фініш за межі карти та чи не є вони стіною
    if not (0 <= start[0] < cols and 0 <= start[1] < rows): return []
    if not (0 <= goal[0] < cols and 0 <= goal[1] < rows): return []
    if grid[start[1]][start[0]] == 1 or grid[goal[1]][goal[0]] == 1:
        return []

    # Черга з пріоритетом для відкритих вузлів: зберігає кортежі (f_score, (x, y))
    open_set = []
    heapq.heappush(open_set, (0, start))
    
    # Словник для збереження "звідки ми прийшли" (щоб потім відновити маршрут)
    came_from = {}
    
    # g_score: точна вартість шляху від старту до поточної точки
    g_score = {start: 0}
    
    # f_score: орієнтовна загальна вартість (g_score + евристика до фінішу)
    f_score = {start: heuristic(start, goal)}
    
    # Дозволені напрямки руху (Вгору, Вниз, Вліво, Вправо). Діагоналі вимкнено для простоти.
    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    
    while open_set:
        # Дістаємо вузол з найменшим f_score
        current = heapq.heappop(open_set)[1]
        
        # Якщо дійшли до цілі - відновлюємо шлях назад
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse() # Перевертаємо, щоб шлях був від старту до фінішу
            return path
            
        # Перевіряємо всіх 4-х сусідів поточної клітинки
        for dx, dy in directions:
            neighbor = (current[0] + dx, current[1] + dy)
            nx, ny = neighbor
            
            # Якщо сусід в межах карти і не є стіною (0 - вільно)
            if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] == 0:
                # Вартість кроку на сусідню клітинку = 1
                tentative_g_score = g_score[current] + 1
                
                # Якщо ми знайшли коротший шлях до сусіда
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
                    
    # Якщо черга спорожніла, а ціль не знайдено - шляху не існує
    return []