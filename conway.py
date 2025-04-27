import pygame
import random

# Configuración
WIDTH, HEIGHT = 800, 600
CELL_SIZE = 10
FPS = 60

# Colores
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
ALIVE_COLOR = (50, 200, 50)
GRID_COLOR = (40, 40, 40)

# Inicializar
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Mapa más grande que la pantalla
MAP_WIDTH = 200
MAP_HEIGHT = 200
grid = [[random.choice([0, 1]) for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]

# Offset para mover el mapa
offset_x = 0
offset_y = 0
move_speed = 10

def count_neighbors(x, y):
    count = 0
    for dy in [-1, 0, 1]:
        for dx in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT:
                count += grid[ny][nx]
    return count

def update_grid():
    global grid
    new_grid = [[0 for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            neighbors = count_neighbors(x, y)
            if grid[y][x] == 1:
                if neighbors == 2 or neighbors == 3:
                    new_grid[y][x] = 1
            else:
                if neighbors == 3:
                    new_grid[y][x] = 1
    grid = new_grid

running = True
while running:
    clock.tick(FPS)
    screen.fill(BLACK)

    # Eventos
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Movimiento con teclas
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]:
        offset_y += move_speed
    if keys[pygame.K_s]:
        offset_y -= move_speed
    if keys[pygame.K_a]:
        offset_x += move_speed
    if keys[pygame.K_d]:
        offset_x -= move_speed

    # Dibujar
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if grid[y][x] == 1:
                draw_x = x * CELL_SIZE + offset_x
                draw_y = y * CELL_SIZE + offset_y
                if -CELL_SIZE < draw_x < WIDTH and -CELL_SIZE < draw_y < HEIGHT:
                    pygame.draw.rect(screen, ALIVE_COLOR, (draw_x, draw_y, CELL_SIZE, CELL_SIZE))

    # Dibujar la cuadrícula
    for x in range(0, WIDTH, CELL_SIZE):
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, CELL_SIZE):
        pygame.draw.line(screen, GRID_COLOR, (0, y), (WIDTH, y))

    update_grid()
    pygame.display.flip()

pygame.quit()
