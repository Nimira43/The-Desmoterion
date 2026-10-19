import csv
import pygame
import constants as C
from character import Character
from items import Item

T = C.TILE_SIZE
H = C.HALF_TILE


def load_level_data(level):
  with open(f"levels/level{level}_data.csv", newline="") as f:
    return [[int(t) for t in row] for row in csv.reader(f) if row]


def cell_of(px, py):
  return (int(px) + H) // T, (int(py) + H) // T


class World():
  def __init__(self, data, tile_list, item_images, mob_animations):
    self.rows = len(data)
    self.cols = max(len(r) for r in data)
    self.tiles = [[None] * self.cols for _ in range(self.rows)]
    self.walls = [[False] * self.cols for _ in range(self.rows)]
    self.exit_rect = None
    self.item_list = []
    self.player = None
    self.character_list = []

    floor = tile_list[C.TILE_FLOOR]
    for y, row in enumerate(data):
      for x, tile in enumerate(row):
        if tile < 0:
          continue
        wx, wy = x * T, y * T
        image = tile_list[tile]

        if tile == C.TILE_WALL:
          self.walls[y][x] = True
        elif tile == C.TILE_EXIT:
          self.exit_rect = pygame.Rect(wx - H, wy - H, T, T)
        elif tile == C.TILE_COIN:
          self.item_list.append(Item(wx, wy, 0, item_images[0]))
          image = floor
        elif tile == C.TILE_POTION:
          self.item_list.append(Item(wx, wy, 1, [item_images[1]]))
          image = floor
        elif tile == C.TILE_PLAYER:
          self.player = Character(wx, wy, 100, mob_animations, 0, False, 1)
          image = floor
        elif C.TILE_ENEMY_FIRST <= tile <= C.TILE_ENEMY_LAST:
          self.character_list.append(Character(wx, wy, 100, mob_animations, tile - 11, False, 1))
          image = floor
        elif tile == C.TILE_BOSS:
          self.character_list.append(Character(wx, wy, 100, mob_animations, 6, True, 2))
          image = floor

        self.tiles[y][x] = image

  def is_wall(self, cx, cy):
    if 0 <= cy < self.rows and 0 <= cx < self.cols:
      return self.walls[cy][cx]
    return True  
  
  def walls_overlapping(self, rect):
    x0, y0 = cell_of(rect.left, rect.top)
    x1, y1 = cell_of(rect.right - 1, rect.bottom - 1)
    out = []
    for cy in range(y0, y1 + 1):
      for cx in range(x0, x1 + 1):
        if self.is_wall(cx, cy):
          out.append(pygame.Rect(cx * T - H, cy * T - H, T, T))
    return out

  def line_of_sight(self, a, b):
    ax, ay = a[0] + H, a[1] + H 
    bx, by = b[0] + H, b[1] + H
    cx, cy = int(ax // T), int(ay // T)
    ex, ey = int(bx // T), int(by // T)
    dx, dy = bx - ax, by - ay
    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1
    inf = float("inf")
    t_dx = abs(T / dx) if dx else inf
    t_dy = abs(T / dy) if dy else inf
    t_x = ((cx + (step_x > 0)) * T - ax) / dx if dx else inf
    t_y = ((cy + (step_y > 0)) * T - ay) / dy if dy else inf

    for _ in range(abs(ex - cx) + abs(ey - cy) + 1):
      if self.is_wall(cx, cy):
        return False
      if cx == ex and cy == ey:
        return True
      if t_x < t_y:
        t_x += t_dx
        cx += step_x
      else:
        t_y += t_dy
        cy += step_y
    return not self.is_wall(cx, cy)

  def draw(self, surface, cam):
    sw, sh = surface.get_size()
    x0, y0 = cell_of(cam[0], cam[1])
    x1, y1 = cell_of(cam[0] + sw, cam[1] + sh)
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, self.cols - 1), min(y1, self.rows - 1)
    blit = surface.blit
    ox, oy = H + cam[0], H + cam[1]
    for cy in range(y0, y1 + 1):
      row = self.tiles[cy]
      sy = cy * T - oy
      for cx in range(x0, x1 + 1):
        img = row[cx]
        if img is not None:
          blit(img, (cx * T - ox, sy))
