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
CELL_SIZE = 2             # tamaño de cada casilla en píxeles
WORLD_W = MAP_WIDTH * CELL_SIZE
WORLD_H = MAP_HEIGHT * CELL_SIZE
PANEL_WIDTH = 200         # ancho del panel de estadísticas
SCREEN_W = WORLD_W * WORLD_COLS + PANEL_WIDTH
SCREEN_H = WORLD_H * WORLD_ROWS
FPS = 30
DT = 100                  # ms por paso de simulación

# Tiempos en milisegundos
BUSH_REGEN_TIME = 3000
MIN_LIFESPAN    = 120_000
MAX_LIFESPAN    = 240_000

# Población y recursos
INITIAL_AGENTS = 30
MAX_AGENTS     = 1000
BUSH_COUNT     = 150
LAKE_COUNT     = 50

# Archivos persistentes
BEST_BRAIN_FILE = 'best_brain.npz'
STATS_FILE      = 'stats.npz'

# Variables globales de estado
best_age       = 0
best_brain     = None
resets_count   = 0
cumulative_time_ms = 0

# Colores
BLACK           = (0, 0, 0)
PANEL_BG_COLOR  = (30, 30, 30)
BUSH_COLOR      = (0, 200, 0)
LAKE_COLOR      = (0, 100, 255)
BOUNDARY_COLOR  = (80, 80, 80)
STAGE_COLORS    = {
    'child': (200, 50, 200),
    'adult': (255, 0, 0),
    'elder': (150,150,150)
}

# --------------------
# Carga inicial de estadísticas
# --------------------
if os.path.exists(STATS_FILE):
    stats = np.load(STATS_FILE)
    resets_count       = int(stats.get('resets_count', 0))
    cumulative_time_ms = int(stats.get('cumulative_time_ms', 0))
else:
    resets_count = 0
    cumulative_time_ms = 0

# --------------------
# Guardar y cargar cerebro
# --------------------
def save_brain(brain):
    np.savez(BEST_BRAIN_FILE, W1=brain.W1, W2=brain.W2)

def load_brain():
    global best_brain, best_age
    if os.path.exists(BEST_BRAIN_FILE):
        data = np.load(BEST_BRAIN_FILE)
        brain = SimpleBrain()
        brain.W1 = data['W1']
        brain.W2 = data['W2']
        best_brain = brain.copy()
        # best_age ya se inicializa en 0; se actualizará al primer reset
        print(f"Cerebro cargado: mejor edad previa = {best_age} ms")
        return brain
    print("No se encontró cerebro previo, usando aleatorio.")
    return None

# --------------------
# Red neuronal + REINFORCE simple
# --------------------
class SimpleBrain:
    def __init__(self,
                 input_size=31,   # 5×5 visión=25 + hambre+sed=2 + memoria=2 + emociones=2
                 hidden_size=32,
                 output_size=6,
                 lr=1e-3):
        self.W1 = np.random.randn(input_size, hidden_size) * 0.1
        self.W2 = np.random.randn(hidden_size, output_size) * 0.1
        self.lr = lr

    def forward(self, x):
        h = np.tanh(x @ self.W1)
        logits = h @ self.W2
        exp   = np.exp(logits - np.max(logits))
        return exp / exp.sum(), h

    def select_action(self, x):
        probs, h = self.forward(x)
        action   = np.random.choice(len(probs), p=probs)
        logp     = np.log(probs[action] + 1e-8)
        return action, logp, h

    def update_policy(self, logps, rewards, hs, xs, acts):
        G = 0
        for t in reversed(range(len(rewards))):
            G = rewards[t] + 0.99 * G
            x, h = xs[t], hs[t]
            probs, _ = self.forward(x)
            dlogits = probs.copy()
            dlogits[acts[t]] -= 1
            grad_W2 = np.outer(h, dlogits) * G
            grad_h  = (self.W2 @ dlogits) * (1 - h**2)
            grad_W1 = np.outer(x, grad_h) * G
            self.W2 -= self.lr * grad_W2
            self.W1 -= self.lr * grad_W1

    def mutate(self, sigma=0.05):
        self.W1 += np.random.randn(*self.W1.shape) * sigma
        self.W2 += np.random.randn(*self.W2.shape) * sigma

    def copy(self):
        b = SimpleBrain()
        b.W1, b.W2, b.lr = self.W1.copy(), self.W2.copy(), self.lr
        return b

# --------------------
# Agente con memoria, visión, emociones y RL
# --------------------
class AgentCell:
    def __init__(self, x, y, brain=None, world=None):
        self.x, self.y     = x, y
        self.hunger        = 100.0
        self.thirst        = 100.0
        self.age           = 0
        self.life_span     = random.uniform(MIN_LIFESPAN, MAX_LIFESPAN)
        self.brain         = brain.copy() if brain else SimpleBrain()
        self.alive         = True
        self.world         = world
        self.prev_obs      = np.zeros(2)
        self.logps, self.rewards, self.hs, self.xs, self.acts = [], [], [], [], []

    @property
    def stage(self):
        frac = self.age / self.life_span
        if frac < 0.25: return 'child'
        if frac < 0.75: return 'adult'
        return 'elder'

    def sense(self):
        vision = []
        R = 2
        for dy in range(-R, R+1):
            for dx in range(-R, R+1):
                nx, ny = self.x + dx, self.y + dy
                if 0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT:
                    if (nx, ny) in self.world.bushes:
                        vision.append(1)
                    elif (nx, ny) in self.world.lakes:
                        vision.append(2)
                    else:
                        occ = any(o.alive and o.x==nx and o.y==ny for o in self.world.agents)
                        vision.append(3 if occ else 0)
                else:
                    vision.append(0)
        base      = [self.hunger/100, self.thirst/100]
        happiness = (self.hunger + self.thirst)/200
        fear      = 1 - happiness
        return np.array(vision + base + list(self.prev_obs) + [happiness, fear])

    def move(self):
        if not self.alive: return
        if self.age > self.life_span: return self.die()

        obs = self.sense()
        a, logp, h = self.brain.select_action(obs)
        self.logps.append(logp); self.hs.append(h); self.xs.append(obs); self.acts.append(a)
        self.rewards.append(+0.1)

        moves = [(0,0),(0,-1),(0,1),(-1,0),(1,0),(0,0)]
        dx, dy = moves[a]
        self.x = np.clip(self.x+dx, 0, MAP_WIDTH-1)
        self.y = np.clip(self.y+dy, 0, MAP_HEIGHT-1)

        if (self.x, self.y) in self.world.bushes:
            self.hunger = min(100, self.hunger+80)
            self.rewards[-1] += +1.0
            self.world.bushes.remove((self.x, self.y))
            self.world.bush_regen.append(((self.x, self.y), self.world.time_ms + BUSH_REGEN_TIME))

        if (self.x, self.y) in self.world.lakes:
            self.thirst = min(100, self.thirst+80)
            self.rewards[-1] += +1.0

        self.hunger -= 0.5; self.thirst -= 0.5
        self.rewards[-1] -= 0.1

        if self.hunger <= 0 or self.thirst <= 0:
            return self.die()

        if a == 5 and self.stage in ('adult','elder'):
            for o in self.world.agents:
                if o is not self and o.alive and o.x==self.x and o.y==self.y:
                    if random.random()>0.5:
                        o.die(); self.rewards[-1]+=+0.5
                    else:
                        self.die(); self.rewards[-1]-=+0.5
                    break

        if self.alive and self.stage=='adult' and self.hunger>70 and self.thirst>70:
            child = self.reproduce()
            self.world.new_agents.append(child)
            self.rewards[-1] += +2.0

        self.prev_obs = obs[:2]

    def die(self):
        self.alive = False
        self.brain.update_policy(self.logps, self.rewards, self.hs, self.xs, self.acts)
        if self.world and self.world.time_ms > self.world.local_best_age:
            self.world.local_best_age   = self.world.time_ms
            self.world.local_best_brain = self.brain.copy()

    def reproduce(self):
        self.hunger -= 30; self.thirst -= 30
        return AgentCell(self.x, self.y, brain=self.brain, world=self.world)

# --------------------
# Mundo enriquecido
# --------------------
class SmallWorld:
    def __init__(self, world_id):
        self.id = world_id
        self.reset()

    def reset(self):
        global best_brain, best_age, resets_count
        b = best_brain.copy() if best_brain else None
        self.bushes     = {(random.randrange(MAP_WIDTH), random.randrange(MAP_HEIGHT)) for _ in range(BUSH_COUNT)}
        self.lakes      = {(random.randrange(MAP_WIDTH), random.randrange(MAP_HEIGHT)) for _ in range(LAKE_COUNT)}
        self.bush_regen = []
        self.agents     = [AgentCell(random.randrange(MAP_WIDTH),
                                     random.randrange(MAP_HEIGHT),
                                     brain=b, world=self)
                           for _ in range(INITIAL_AGENTS)]
        self.time_ms           = 0
        self.local_best_age    = 0
        self.local_best_brain  = b.copy() if b else None
        self.new_agents        = []
        resets_count += 1
        print(f"[World {self.id}] Reiniciado: {len(self.agents)} agentes (Total resets: {resets_count})")

    def update(self):
        for pos, t in list(self.bush_regen):
            if self.time_ms >= t:
                self.bushes.add(pos)
                self.bush_regen.remove((pos, t))
        self.new_agents = []
        for ag in self.agents:
            ag.move()
            ag.age += DT
        self.agents = [a for a in self.agents if a.alive] + self.new_agents
        if len(self.agents) > MAX_AGENTS:
            self.agents = sorted(self.agents, key=lambda a: a.age)[:MAX_AGENTS]
        self.time_ms += DT
        if not self.agents:
            print(f"[World {self.id}] murieron todos en {self.time_ms} ms")
            self.handle_reset()

    def handle_reset(self):
        global best_age, best_brain
        if self.local_best_age > best_age:
            best_age   = self.local_best_age
            best_brain = self.local_best_brain.copy()
            save_brain(best_brain)
            print(f"[World {self.id}] ¡Mejor global: {best_age} ms!")
        self.reset()

# --------------------
# Ejecución
# --------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
clock  = pygame.time.Clock()

# Cargar cerebro y registrar tiempo inicial
_ = load_brain()
start_time_ms = pygame.time.get_ticks()

# Crear entornos
envs = [SmallWorld(i) for i in range(NUM_WORLDS)]

# Fuente para panel
font = pygame.font.SysFont(None, 24)

running = True
while running:
    now_ms = pygame.time.get_ticks()
    elapsed_ms = now_ms - start_time_ms
    total_ms = cumulative_time_ms + elapsed_ms

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

    screen.fill(BLACK)

    # Dibujar universos
    for idx, w in enumerate(envs):
        w.update()
        r, c = divmod(idx, WORLD_COLS)
        ox, oy = c * WORLD_W, r * WORLD_H
        # arbustos y lagos
        for x, y in w.bushes:
            pygame.draw.rect(screen, BUSH_COLOR, (ox + x*CELL_SIZE, oy + y*CELL_SIZE, CELL_SIZE, CELL_SIZE))
        for x, y in w.lakes:
            pygame.draw.rect(screen, LAKE_COLOR, (ox + x*CELL_SIZE, oy + y*CELL_SIZE, CELL_SIZE, CELL_SIZE))
        # agentes
        for ag in w.agents:
            col = STAGE_COLORS[ag.stage]
            cx = ox + ag.x*CELL_SIZE + CELL_SIZE//2
            cy = oy + ag.y*CELL_SIZE + CELL_SIZE//2
            pygame.draw.circle(screen, col, (cx, cy), CELL_SIZE//2)
        # borde
        pygame.draw.rect(screen, BOUNDARY_COLOR, (ox, oy, WORLD_W, WORLD_H), 1)

    # Panel lateral
    panel_x = WORLD_W * WORLD_COLS
    pygame.draw.rect(screen, PANEL_BG_COLOR, (panel_x, 0, PANEL_WIDTH, SCREEN_H))
    lines = [
        f"Mundos creados: {resets_count}",
        f"Tiempo global:",
        f"  {total_ms//1000} s",
        f"  {total_ms//60000} m",
        f"Mejor tiempo:",
        f"  {best_age} ms",
        f"  {best_age/1000:.2f} s",
        f"  {best_age/60000:.2f} m",
    ]
    for i, text in enumerate(lines):
        surf = font.render(text, True, (255,255,255))
        screen.blit(surf, (panel_x + 10, 10 + i * 28))

    pygame.display.flip()
    clock.tick(FPS)

# Al cerrar, persisto estadísticas
cumulative_time_ms += pygame.time.get_ticks() - start_time_ms
np.savez(STATS_FILE,
         resets_count=resets_count,
         cumulative_time_ms=cumulative_time_ms)

pygame.quit()
