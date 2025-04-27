import pygame
import random
import numpy as np
import os

# Configuración
WIDTH, HEIGHT = 800, 600
CELL_SIZE = 10
FPS = 30

MAP_WIDTH = 100
MAP_HEIGHT = 100
MAX_AGENTS = 200

# Tiempos en milisegundos
BUSH_REGEN_TIME = 10000
MIN_LIFESPAN = 120000
MAX_LIFESPAN = 240000

BEST_BRAIN_FILE = 'best_brain.npz'

# Colores
BLACK = (0, 0, 0)
BUSH_COLOR = (0, 200, 0)
LAKE_COLOR = (0, 100, 255)
GRID_COLOR = (40, 40, 40)
STAGE_COLORS = {
    'child': (200, 50, 200),  # Morado
    'adult': (50, 50, 200),   # Azul
    'elder': (150, 150, 150), # Gris
    'dead': (100, 0, 0)       # Rojo oscuro
}

# Inicializar Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

offset_x = 0
offset_y = 0
move_speed = 10

# Recursos
bushes = {(random.randrange(MAP_WIDTH), random.randrange(MAP_HEIGHT)) for _ in range(50)}
lakes = {(random.randrange(MAP_WIDTH), random.randrange(MAP_HEIGHT)) for _ in range(30)}
bush_regen = []

# Seguimiento del mejor cerebro
best_age = 0
best_brain = None

# Guardar y cargar cerebro
def save_brain(brain):
    np.savez(BEST_BRAIN_FILE, W1=brain.W1, W2=brain.W2)

def load_brain():
    if os.path.exists(BEST_BRAIN_FILE):
        data = np.load(BEST_BRAIN_FILE)
        brain = SimpleBrain()
        brain.W1 = data['W1']
        brain.W2 = data['W2']
        return brain
    return None

# Red neuronal simple
class SimpleBrain:
    def __init__(self, input_size=10, hidden_size=6, output_size=6):
        self.W1 = np.random.randn(input_size, hidden_size) * 0.1
        self.W2 = np.random.randn(hidden_size, output_size) * 0.1

    def forward(self, inputs):
        h = np.tanh(inputs @ self.W1)
        return h @ self.W2

    def mutate(self):
        self.W1 += np.random.randn(*self.W1.shape) * 0.05
        self.W2 += np.random.randn(*self.W2.shape) * 0.05

    def copy(self):
        new = SimpleBrain()
        new.W1 = self.W1.copy()
        new.W2 = self.W2.copy()
        return new

# Agente inteligente
class AgentCell:
    def __init__(self, x, y, brain=None):
        self.x = x
        self.y = y
        self.hunger = 100.0
        self.thirst = 100.0
        self.birth_time = pygame.time.get_ticks()
        self.life_span = random.uniform(MIN_LIFESPAN, MAX_LIFESPAN)
        self.brain = brain.copy() if brain else SimpleBrain()
        self.alive = True

    @property
    def age(self):
        return pygame.time.get_ticks() - self.birth_time

    @property
    def stage(self):
        if self.age < self.life_span * 0.25:
            return 'child'
        elif self.age < self.life_span * 0.75:
            return 'adult'
        else:
            return 'elder'

    def sense(self):
        def info(dx, dy):
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT:
                if (nx, ny) in bushes:
                    return 1
                if (nx, ny) in lakes:
                    return 2
                for a in agent_cells:
                    if a.alive and a.x == nx and a.y == ny:
                        return 3
            return 0

        inputs = [
            info(0, -1)/3, info(0, 1)/3, info(-1, 0)/3, info(1, 0)/3,
            self.hunger/100, self.thirst/100
        ] + [random.random() for _ in range(4)]
        return np.array(inputs)

    def move(self):
        global best_age, best_brain
        if not self.alive:
            return

        if self.age > self.life_span:
            self.die()
            return

        action = int(np.argmax(self.brain.forward(self.sense())))
        moves = [(0,0),(0,-1),(0,1),(-1,0),(1,0),(0,0)]  # (quieto, arriba, abajo, izq, der, ataque)
        dx, dy = moves[action] if 0 <= action < len(moves) else (0,0)
        self.x = max(0, min(self.x + dx, MAP_WIDTH-1))
        self.y = max(0, min(self.y + dy, MAP_HEIGHT-1))

        if (self.x, self.y) in bushes:
            self.hunger = min(100, self.hunger + 50)
            bushes.remove((self.x, self.y))
            bush_regen.append(((self.x, self.y), pygame.time.get_ticks() + BUSH_REGEN_TIME))
        if (self.x, self.y) in lakes:
            self.thirst = min(100, self.thirst + 50)

        self.hunger -= 0.5
        self.thirst -= 0.5
        if self.hunger <= 0 or self.thirst <= 0:
            self.die()
            return

        if action == 5 and self.stage in ('adult', 'elder'):
            for other in agent_cells:
                if other is not self and other.alive and other.x == self.x and other.y == self.y:
                    if random.random() > 0.5:
                        other.die()
                    else:
                        self.die()
                    break

    def die(self):
        global best_age, best_brain
        self.alive = False
        if self.age > best_age:
            best_age = self.age
            best_brain = self.brain.copy()
            save_brain(best_brain)

    def can_reproduce(self):
        return self.alive and self.stage == 'adult' and self.hunger > 70 and self.thirst > 70

    def reproduce(self):
        child = AgentCell(self.x, self.y, brain=self.brain)
        child.brain.mutate()
        self.hunger -= 30
        self.thirst -= 30
        return child

# Cargar cerebro si existe
best_brain = load_brain()

# Crear agentes iniciales
if best_brain:
    agent_cells = [AgentCell(random.randrange(MAP_WIDTH), random.randrange(MAP_HEIGHT), brain=best_brain) for _ in range(20)]
else:
    agent_cells = [AgentCell(random.randrange(MAP_WIDTH), random.randrange(MAP_HEIGHT)) for _ in range(20)]

# Bucle principal
running = True
while running:
    clock.tick(FPS)
    now = pygame.time.get_ticks()
    screen.fill(BLACK)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w: offset_y += move_speed
            if event.key == pygame.K_s: offset_y -= move_speed
            if event.key == pygame.K_a: offset_x += move_speed
            if event.key == pygame.K_d: offset_y -= move_speed
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            gx = int((mx - offset_x) / CELL_SIZE)
            gy = int((my - offset_y) / CELL_SIZE)
            if 0 <= gx < MAP_WIDTH and 0 <= gy < MAP_HEIGHT:
                agent_cells.append(AgentCell(gx, gy, brain=best_brain if best_brain else None))

    # Regenerar arbustos
    for pos, regen_time in bush_regen[:]:
        if now >= regen_time:
            bushes.add(pos)
            bush_regen.remove((pos, regen_time))

    # Mover agentes y reproducir
    children = []
    for agent in agent_cells:
        agent.move()
        if agent.can_reproduce():
            children.append(agent.reproduce())

    agent_cells = [a for a in agent_cells if a.alive]
    agent_cells.extend(children)

    if len(agent_cells) > MAX_AGENTS:
        agent_cells = sorted(agent_cells, key=lambda a: a.age)[:MAX_AGENTS]

    # Dibujar
    for x, y in bushes:
        dx, dy = x*CELL_SIZE + offset_x, y*CELL_SIZE + offset_y
        if -CELL_SIZE < dx < WIDTH and -CELL_SIZE < dy < HEIGHT:
            pygame.draw.rect(screen, BUSH_COLOR, (dx, dy, CELL_SIZE, CELL_SIZE))
    for x, y in lakes:
        dx, dy = x*CELL_SIZE + offset_x, y*CELL_SIZE + offset_y
        if -CELL_SIZE < dx < WIDTH and -CELL_SIZE < dy < HEIGHT:
            pygame.draw.rect(screen, LAKE_COLOR, (dx, dy, CELL_SIZE, CELL_SIZE))

    for agent in agent_cells:
        color = STAGE_COLORS[agent.stage] if agent.alive else STAGE_COLORS['dead']
        dx, dy = agent.x*CELL_SIZE + offset_x, agent.y*CELL_SIZE + offset_y
        if -CELL_SIZE < dx < WIDTH and -CELL_SIZE < dy < HEIGHT:
            pygame.draw.rect(screen, color, (dx, dy, CELL_SIZE, CELL_SIZE))

    for x in range(0, WIDTH, CELL_SIZE):
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, CELL_SIZE):
        pygame.draw.line(screen, GRID_COLOR, (0, y), (WIDTH, y))

    pygame.display.flip()

pygame.quit()