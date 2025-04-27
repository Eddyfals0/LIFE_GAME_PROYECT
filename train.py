import pygame
import random
import numpy as np
import os

# --------------------
# Configuración general
# --------------------
MAP_WIDTH, MAP_HEIGHT = 100, 100
WORLD_COLS, WORLD_ROWS = 4, 4
NUM_WORLDS = WORLD_COLS * WORLD_ROWS
CELL_SIZE = 2  # tamaño de cada casilla en píxeles
WORLD_W = MAP_WIDTH * CELL_SIZE
WORLD_H = MAP_HEIGHT * CELL_SIZE
SCREEN_W = WORLD_W * WORLD_COLS
SCREEN_H = WORLD_H * WORLD_ROWS
FPS = 30
DT = 100  # ms por paso de simulación

# Tiempos en milisegundos
BUSH_REGEN_TIME = 10000
MIN_LIFESPAN = 120000
MAX_LIFESPAN = 240000

# Límites de población
INITIAL_AGENTS = 20
MAX_AGENTS = 200

# Archivo y variables globales para el mejor cerebro
BEST_BRAIN_FILE = 'best_brain.npz'
best_age = 0
best_brain = None

# Colores
BLACK = (0, 0, 0)
BUSH_COLOR = (0, 200, 0)
LAKE_COLOR = (0, 100, 255)
AGENT_COLOR = (200, 50, 200)
BOUNDARY_COLOR = (80, 80, 80)  # color para divisiones

# Colores por etapa de agente
STAGE_COLORS = {
    'child': (200, 50, 200),   # morado para niños
    'adult': (50, 50, 200),    # azul para adultos
    'elder': (150, 150, 150)   # gris para ancianos
}

# --------------------
# Guardar y cargar cerebro
# --------------------

def save_brain(brain):
    np.savez(BEST_BRAIN_FILE, W1=brain.W1, W2=brain.W2)


def load_brain():
    global best_brain
    if os.path.exists(BEST_BRAIN_FILE):
        data = np.load(BEST_BRAIN_FILE)
        brain = SimpleBrain()
        brain.W1 = data['W1']
        brain.W2 = data['W2']
        best_brain = brain.copy()
        print(f"Cerebro cargado: mejor edad previa = {best_age} ms")
        return brain
    print("No se encontró cerebro previo, usando nuevos cerebros aleatorios.")
    return None

# --------------------
# Red neuronal simple
# --------------------
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

# --------------------
# Agente
# --------------------
class AgentCell:
    def __init__(self, x, y, brain=None, world=None):
        self.x, self.y = x, y
        self.hunger, self.thirst = 100.0, 100.0
        self.age = 0  # ms de simulación acumulados
        self.life_span = random.uniform(MIN_LIFESPAN, MAX_LIFESPAN)
        self.brain = brain.copy() if brain else SimpleBrain()
        self.alive = True
        self.world = world

    @property
    def stage(self):
        fraction = self.age / self.life_span
        if fraction < 0.25:
            return 'child'
        elif fraction < 0.75:
            return 'adult'
        else:
            return 'elder'

    def sense(self):
        def info(dx, dy):
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT:
                if (nx, ny) in self.world.bushes:
                    return 1
                if (nx, ny) in self.world.lakes:
                    return 2
                for o in self.world.agents:
                    if o.alive and o.x == nx and o.y == ny:
                        return 3
            return 0
        return np.array([
            info(0, -1)/3, info(0, 1)/3, info(-1, 0)/3, info(1, 0)/3,
            self.hunger/100, self.thirst/100
        ] + [random.random() for _ in range(4)])

    def move(self):
        if not self.alive:
            return
        if self.age > self.life_span:
            return self.die()
        action = int(np.argmax(self.brain.forward(self.sense())))
        moves = [(0,0),(0,-1),(0,1),(-1,0),(1,0),(0,0)]
        dx, dy = moves[action] if action < len(moves) else (0,0)
        self.x = max(0, min(self.x + dx, MAP_WIDTH - 1))
        self.y = max(0, min(self.y + dy, MAP_HEIGHT - 1))
        # Comer arbusto
        if (self.x, self.y) in self.world.bushes:
            self.hunger = min(100, self.hunger + 50)
            self.world.bushes.remove((self.x, self.y))
            self.world.bush_regen.append(((self.x, self.y), self.world.time_ms + BUSH_REGEN_TIME))
        # Beber lago
        if (self.x, self.y) in self.world.lakes:
            self.thirst = min(100, self.thirst + 50)
        # Decaimiento
        self.hunger -= 0.5
        self.thirst -= 0.5
        if self.hunger <= 0 or self.thirst <= 0:
            return self.die()
        # Ataque (solo adultos/elder)
        if action == 5 and self.stage in ('adult', 'elder'):
            for o in self.world.agents:
                if o is not self and o.alive and o.x == self.x and o.y == self.y:
                    if random.random() > 0.5:
                        o.die()
                    else:
                        self.die()
                    break

    def die(self):
        self.alive = False
        if self.world and self.world.time_ms > self.world.local_best_age:
            self.world.local_best_age = self.world.time_ms
            self.world.local_best_brain = self.brain.copy()

    def can_reproduce(self):
        return self.alive and self.stage == 'adult' and self.hunger > 70 and self.thirst > 70

    def reproduce(self):
        child = AgentCell(self.x, self.y, brain=self.brain, world=self.world)
        child.brain.mutate()
        self.hunger -= 30
        self.thirst -= 30
        return child

# --------------------
# Mundo pequeño para display
# --------------------
class SmallWorld:
    def __init__(self, world_id):
        self.id = world_id
        self.reset()

    def reset(self):
        global best_brain, best_age
        brain = best_brain if best_brain else None
        self.bushes = {(random.randrange(MAP_WIDTH), random.randrange(MAP_HEIGHT)) for _ in range(50)}
        self.lakes = {(random.randrange(MAP_WIDTH), random.randrange(MAP_HEIGHT)) for _ in range(30)}
        self.bush_regen = []
        self.agents = []
        for _ in range(INITIAL_AGENTS):
            x, y = random.randrange(MAP_WIDTH), random.randrange(MAP_HEIGHT)
            self.agents.append(AgentCell(x, y, brain=brain, world=self))
        self.time_ms = 0
        self.local_best_age = 0
        self.local_best_brain = brain.copy() if brain else None
        print(f"[World {self.id}] Reiniciado. Población: {len(self.agents)}")

    def update(self):
        # Regenerar arbustos
        for pos, t in list(self.bush_regen):
            if self.time_ms >= t:
                self.bushes.add(pos)
                self.bush_regen.remove((pos, t))
        # Mover y reproducir agentes
        new_agents = []
        for ag in self.agents:
            ag.move()
            ag.age += DT
            if ag.can_reproduce():
                new_agents.append(ag.reproduce())
        # Filtrar vivos y añadir hijos
        self.agents = [a for a in self.agents if a.alive]
        self.agents.extend(new_agents)
        # Limitar población
        if len(self.agents) > MAX_AGENTS:
            self.agents = sorted(self.agents, key=lambda a: a.age)[:MAX_AGENTS]
        # Avanzar tiempo
        self.time_ms += DT
        # Si mueren todos, reiniciar
        if not self.agents:
            print(f"[World {self.id}] Todos murieron en {self.time_ms} ms")
            self.handle_reset()

    def handle_reset(self):
        global best_age, best_brain
        if self.local_best_age > best_age:
            best_age = self.local_best_age
            best_brain = self.local_best_brain.copy()
            save_brain(best_brain)
            print(f"[World {self.id}] Mejor global actualizado: {best_age} ms")
        self.reset()

# --------------------
# Inicialización Pygame y entornos
# --------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
clock = pygame.time.Clock()
# Cargar cerebro global
_ = load_brain()
# Crear entornos
envs = [SmallWorld(i) for i in range(NUM_WORLDS)]

# --------------------
# Bucle principal
# --------------------
running = True
while running:
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False
    screen.fill(BLACK)
    # Actualizar y dibujar cada mundo
    for idx, w in enumerate(envs):
        w.update()
        row, col = divmod(idx, WORLD_COLS)
        off_x = col * WORLD_W
        off_y = row * WORLD_H
        # Dibujar arbustos y lagos
        for x, y in w.bushes:
            pygame.draw.rect(screen, BUSH_COLOR,
                             (off_x + x*CELL_SIZE, off_y + y*CELL_SIZE, CELL_SIZE, CELL_SIZE))
        for x, y in w.lakes:
            pygame.draw.rect(screen, LAKE_COLOR,
                             (off_x + x*CELL_SIZE, off_y + y*CELL_SIZE, CELL_SIZE, CELL_SIZE))
        # Dibujar agentes con color según etapa
        for ag in w.agents:
            color = STAGE_COLORS[ag.stage]
            cx = off_x + ag.x*CELL_SIZE + CELL_SIZE//2
            cy = off_y + ag.y*CELL_SIZE + CELL_SIZE//2
            pygame.draw.circle(screen, color, (cx, cy), CELL_SIZE//2)
        # Dibujar borde de mundo
        pygame.draw.rect(screen, BOUNDARY_COLOR, (off_x, off_y, WORLD_W, WORLD_H), 1)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
