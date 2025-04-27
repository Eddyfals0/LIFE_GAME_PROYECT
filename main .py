import pygame
import sys
import random
import math
from pygame.locals import *

# Configuración inicial
pygame.init()
ANCHO_VENTANA = 800
ALTO_VENTANA = 700
TAMANO_CELDA = 20
STATS_ALTO = 60

# Colores
COLOR_FONDO = (34, 139, 34)    # Verde bosque
COLOR_LINEAS = (0, 100, 0)      # Verde oscuro
COLOR_PERSONAJE = (255, 0, 0)   # Rojo
COLOR_STATS = (50, 50, 50)      # Gris oscuro
COLOR_TEXTO = (255, 255, 255)   # Blanco
COLOR_ARBOL = (139, 69, 19)     # Marrón
COLOR_ARBUSTO = (0, 100, 0)     # Verde oscuro
COLOR_RIO = (64, 164, 223)      # Azul claro
COLOR_BARRA = (255, 0, 0)       # Rojo para barras de recursos

# Ventana y fuente
ventana = pygame.display.set_mode((ANCHO_VENTANA, ALTO_VENTANA))
pygame.display.set_caption("Simulador de Vida")
fuente = pygame.font.SysFont('Arial', 24)
reloj = pygame.time.Clock()

# Límites de celdas
MAX_COLUMNAS = (ANCHO_VENTANA // TAMANO_CELDA) - 1
MAX_FILAS = ((ALTO_VENTANA - STATS_ALTO) // TAMANO_CELDA) - 1

total_elementos = []  # Lista global de elementos

# Clases
class RecursoCelda:
    """
    Representa un recurso (agua o comida) en una sola celda.
    """
    def __init__(self, x, y, capacidad_max, color):
        self.x = x
        self.y = y
        self.capacidad_max = capacidad_max
        self.capacidad = capacidad_max
        self.color = color
        self.ultima_interaccion = 0

    @property
    def posiciones(self):
        return [(self.x, self.y)]

class Arbol:
    """
    Árbol de 3 celdas, sin barra de recurso.
    """
    def __init__(self, x, y):
        self.posiciones = [
            (x, y),
            (x, y + 1),
            (x, y + 2)
        ]
        self.color = COLOR_ARBOL

class Personaje:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.stats = {
            'vida': 100,
            'agua': 100,
            'comida': 100,
            'frío': 0,
            'calor': 0
        }
        self.ultima_actualizacion = {
            'agua': 0,
            'comida': 0,
            'vida': 0
        }

    def actualizar_stats(self, current_time):
        # Disminuir agua cada 5 segundos
        if current_time - self.ultima_actualizacion['agua'] > 5000:
            self.stats['agua'] = max(0, self.stats['agua'] - 5)
            self.ultima_actualizacion['agua'] = current_time
        # Disminuir comida cada 10 segundos
        if current_time - self.ultima_actualizacion['comida'] > 10000:
            self.stats['comida'] = max(0, self.stats['comida'] - 5)
            self.ultima_actualizacion['comida'] = current_time
        # Aumentar vida si agua y comida > 70% (cada 2 segundos)
        if current_time - self.ultima_actualizacion['vida'] > 2000:
            if self.stats['agua'] > 70 and self.stats['comida'] > 70:
                self.stats['vida'] = min(100, self.stats['vida'] + 5)
            self.ultima_actualizacion['vida'] = current_time

    def interactuar_con_elemento(self, elemento, current_time):
        # Determinar si es agua o comida según el color del recurso
        if elemento.color == COLOR_RIO:
            stat = 'agua'
        elif elemento.color == COLOR_ARBUSTO:
            stat = 'comida'
        else:
            return

        faltante = 100 - self.stats[stat]
        # Si ya está al máximo o recurso vacío, no hacer nada
        if faltante <= 0 or elemento.capacidad <= 0:
            return

        cantidad = min(faltante, elemento.capacidad)
        self.stats[stat] += cantidad
        elemento.capacidad -= cantidad
        elemento.ultima_interaccion = current_time

        # Si el recurso se agota, lo eliminamos
        if elemento.capacidad <= 0:
            total_elementos.remove(elemento)

# Generación de elementos
def generar_elementos():
    elementos = []
    celdas_ocupadas = set()

    # Ríos (cada celda como recurso independiente)
    for _ in range(random.randint(1, 3)):
        ancho = random.randint(2, 9)
        alto  = random.randint(2, 9)
        x0 = random.randint(0, MAX_COLUMNAS - ancho)
        y0 = random.randint(0, MAX_FILAS    - alto)
        celdas = [(x0 + dx, y0 + dy) for dx in range(ancho) for dy in range(alto)]
        if any(c in celdas_ocupadas for c in celdas):
            continue
        for (cx, cy) in celdas:
            recurso = RecursoCelda(cx, cy, capacidad_max=3000, color=COLOR_RIO)
            elementos.append(recurso)
            celdas_ocupadas.add((cx, cy))

    # Árboles (sin barra de recurso)
    for _ in range(random.randint(4, 14)):
        x = random.randint(0, MAX_COLUMNAS)
        y = random.randint(0, MAX_FILAS - 2)
        posiciones = [(x, y), (x, y+1), (x, y+2)]
        if any(pos in celdas_ocupadas for pos in posiciones):
            continue
        arbol = Arbol(x, y)
        elementos.append(arbol)
        for pos in arbol.posiciones:
            celdas_ocupadas.add(pos)

    # Arbustos (2 celdas independientes)
    for _ in range(random.randint(10, 20)):
        x = random.randint(0, MAX_COLUMNAS - 1)
        y = random.randint(0, MAX_FILAS)
        if (x, y) in celdas_ocupadas or (x+1, y) in celdas_ocupadas:
            continue
        for cx in (x, x+1):
            recurso = RecursoCelda(cx, y, capacidad_max=500, color=COLOR_ARBUSTO)
            elementos.append(recurso)
            celdas_ocupadas.add((cx, y))

    return elementos

# Dibujado
def dibujar_cuadricula():
    for x in range(0, ANCHO_VENTANA, TAMANO_CELDA):
        pygame.draw.line(ventana, COLOR_LINEAS, (x, STATS_ALTO), (x, ALTO_VENTANA))
    for y in range(STATS_ALTO, ALTO_VENTANA, TAMANO_CELDA):
        pygame.draw.line(ventana, COLOR_LINEAS, (0, y), (ANCHO_VENTANA, y))


def dibujar_elementos():
    for elemento in total_elementos:
        for (x, y) in elemento.posiciones:
            pygame.draw.rect(
                ventana,
                elemento.color,
                (
                    x * TAMANO_CELDA,
                    STATS_ALTO + y * TAMANO_CELDA,
                    TAMANO_CELDA,
                    TAMANO_CELDA
                )
            )
            if isinstance(elemento, RecursoCelda):
                porcentaje = elemento.capacidad / elemento.capacidad_max
                if porcentaje < 1.0:
                    largo = math.ceil(TAMANO_CELDA * porcentaje)
                    pygame.draw.rect(
                        ventana,
                        COLOR_BARRA,
                        (
                            x * TAMANO_CELDA,
                            STATS_ALTO + y * TAMANO_CELDA + TAMANO_CELDA - 3,
                            largo,
                            3
                        )
                    )

# Sombrea circular alrededor del personaje
def dibujar_sombra():
    center_x = personaje.x * TAMANO_CELDA + TAMANO_CELDA // 2
    center_y = STATS_ALTO + personaje.y * TAMANO_CELDA + TAMANO_CELDA // 2
    radius = TAMANO_CELDA * 3
    pygame.draw.circle(ventana, (0, 0, 0), (center_x, center_y), radius, width=3)


def dibujar_personaje():
    x = personaje.x * TAMANO_CELDA
    y = STATS_ALTO + personaje.y * TAMANO_CELDA
    pygame.draw.rect(ventana, COLOR_PERSONAJE, (x, y, TAMANO_CELDA, TAMANO_CELDA))


def dibujar_stats():
    pygame.draw.rect(ventana, COLOR_STATS, (0, 0, ANCHO_VENTANA, STATS_ALTO))
    x_pos, y_pos = 20, 15
    for nombre, valor in personaje.stats.items():
        texto = fuente.render(f"{nombre.capitalize()}: {valor}%", True, COLOR_TEXTO)
        ventana.blit(texto, (x_pos, y_pos))
        x_pos += 150

# Movimiento
teclas_activas = {K_w: {'inicio': 0, 'ultimo_mov': 0},
                  K_s: {'inicio': 0, 'ultimo_mov': 0},
                  K_a: {'inicio': 0, 'ultimo_mov': 0},
                  K_d: {'inicio': 0, 'ultimo_mov': 0}}

def manejar_movimiento(tecla, current_time):
    nueva_x, nueva_y = personaje.x, personaje.y
    if tecla == K_w and nueva_y > 0:
        nueva_y -= 1
    elif tecla == K_s and nueva_y < MAX_FILAS:
        nueva_y += 1
    elif tecla == K_a and nueva_x > 0:
        nueva_x -= 1
    elif tecla == K_d and nueva_x < MAX_COLUMNAS:
        nueva_x += 1

    colision = False
    for elemento in total_elementos:
        if (nueva_x, nueva_y) in elemento.posiciones:
            colision = True
            if isinstance(elemento, RecursoCelda):
                personaje.interactuar_con_elemento(elemento, pygame.time.get_ticks())
            break

    if not colision:
        personaje.x, personaje.y = nueva_x, nueva_y
        return True
    return False

# Inicialización y bucle principal
personaje = Personaje(MAX_COLUMNAS // 2, MAX_FILAS // 2)
total_elementos = generar_elementos()

def main():
    while True:
        current_time = pygame.time.get_ticks()

        for evento in pygame.event.get():
            if evento.type == QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == KEYDOWN and evento.key in teclas_activas:
                teclas_activas[evento.key]['inicio'] = current_time
                teclas_activas[evento.key]['ultimo_mov'] = current_time
                manejar_movimiento(evento.key, current_time)
            if evento.type == KEYUP and evento.key in teclas_activas:
                teclas_activas[evento.key]['inicio'] = 0

        # Movimiento continuo
        teclas = pygame.key.get_pressed()
        for tecla in (K_w, K_s, K_a, K_d):
            if teclas[tecla]:
                presionado = current_time - teclas_activas[tecla]['inicio']
                if presionado > 500:
                    desde_ultimo = current_time - teclas_activas[tecla]['ultimo_mov']
                    if desde_ultimo >= 300:
                        if manejar_movimiento(tecla, current_time):
                            teclas_activas[tecla]['ultimo_mov'] = current_time

        # Actualizar stats y dibujar
        personaje.actualizar_stats(current_time)
        ventana.fill(COLOR_FONDO)
        dibujar_cuadricula()
        dibujar_elementos()
        dibujar_sombra()
        dibujar_personaje()
        dibujar_stats()
        pygame.display.update()
        reloj.tick(60)

if __name__ == "__main__":
    main()
