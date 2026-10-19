import math
import pygame
import constants as C
import weapon

DIAG = math.sqrt(2) / 2


def _sign(v):
  return (v > 0) - (v < 0)


class Character():
  def __init__(self, x, y, health, mob_animations, char_type, boss, size):
    self.char_type = char_type
    self.boss = boss
    self.score = 0
    self.flip = False
    self.animations = mob_animations[char_type]  
    self.frame_index = 0
    self.action = 0 
    now = pygame.time.get_ticks()
    self.update_time = now
    self.running = False
    self.health = health
    self.alive = True
    self.hit = False
    self.last_hit = now
    self.last_attack = now
    self.stunned = False

    self.rect = pygame.Rect(0, 0, C.TILE_SIZE * size, C.TILE_SIZE * size)
    self.rect.center = (x, y)
    self.fx = float(self.rect.x)
    self.fy = float(self.rect.y)

  @property
  def image(self):
    return self.animations[self.flip][self.action][self.frame_index]

  def move(self, dx, dy, world):
    self.running = dx != 0 or dy != 0
    if dx < 0:
      self.flip = True
    elif dx > 0:
      self.flip = False
    if dx and dy:
      dx *= DIAG
      dy *= DIAG

    if dx:
      self.fx += dx
      self.rect.x = round(self.fx)
      hits = [w for w in world.walls_overlapping(self.rect) if w.colliderect(self.rect)]
      for wall in hits:
        if dx > 0:
          self.rect.right = wall.left
        else:
          self.rect.left = wall.right
        self.fx = float(self.rect.x)
      if hits and not dy:
        self._slide(hits, world, axis=1, amount=abs(dx))

    if dy:
      self.fy += dy
      self.rect.y = round(self.fy)
      hits = [w for w in world.walls_overlapping(self.rect) if w.colliderect(self.rect)]
      for wall in hits:
        if dy > 0:
          self.rect.bottom = wall.top
        else:
          self.rect.top = wall.bottom
        self.fy = float(self.rect.y)
      if hits and not dx:
        self._slide(hits, world, axis=0, amount=abs(dy))

  def _slide(self, hits, world, axis, amount):
    if axis == 0: 
      lo, hi = self.rect.left, self.rect.right
      overlap_l = max(w.right for w in hits) - lo if all(w.centerx < self.rect.centerx for w in hits) else None
      overlap_r = hi - min(w.left for w in hits) if all(w.centerx > self.rect.centerx for w in hits) else None
    else:  
      lo, hi = self.rect.top, self.rect.bottom
      overlap_l = max(w.bottom for w in hits) - lo if all(w.centery < self.rect.centery for w in hits) else None
      overlap_r = hi - min(w.top for w in hits) if all(w.centery > self.rect.centery for w in hits) else None

    if overlap_l is not None and 0 < overlap_l <= C.CORNER_SLIDE:
      shift = min(amount, overlap_l)
    elif overlap_r is not None and 0 < overlap_r <= C.CORNER_SLIDE:
      shift = -min(amount, overlap_r)
    else:
      return

    old = self.rect.copy()
    if axis == 0:
      self.rect.x += round(shift)
    else:
      self.rect.y += round(shift)
    if any(w.colliderect(self.rect) for w in world.walls_overlapping(self.rect)):
      self.rect = old 
    self.fx, self.fy = float(self.rect.x), float(self.rect.y)

  def ai(self, player, world, fireball_image, now):
    if not self.alive:
      return None
    fireball = None

    px, py = player.rect.center
    sx, sy = self.rect.center
    dist = math.hypot(px - sx, py - sy)

    ai_dx = ai_dy = 0
    if dist > C.RANGE and world.line_of_sight((sx, sy), (px, py)):
      ai_dx = _sign(px - sx) * C.ENEMY_SPEED
      ai_dy = _sign(py - sy) * C.ENEMY_SPEED

    if not self.stunned:
      self.move(ai_dx, ai_dy, world)
      # melee attack
      if dist < C.ATTACK_RANGE and not player.hit:
        player.take_hit(10, now)
      # bosses shoot fireballs
      if self.boss and dist < C.FIREBALL_RANGE and now - self.last_attack >= C.FIREBALL_COOLDOWN:
        fireball = weapon.Fireball(fireball_image, sx, sy, px, py)
        self.last_attack = now

    if self.hit:
      self.hit = False
      self.last_hit = now
      self.stunned = True
      self.running = False
      self.update_action(0, now)
    if now - self.last_hit > C.STUN_COOLDOWN:
      self.stunned = False

    return fireball

  def take_hit(self, amount, now):
    self.health -= amount
    self.hit = True
    self.last_hit = now

  def update(self, now):
    if self.health <= 0:
      self.health = 0
      self.alive = False

    if self.char_type == 0 and self.hit and now - self.last_hit > C.PLAYER_HIT_COOLDOWN:
      self.hit = False

    self.update_action(1 if self.running else 0, now)

    if now - self.update_time > C.ANIM_COOLDOWN:
      self.frame_index = (self.frame_index + 1) % len(self.animations[0][self.action])
      self.update_time = now

  def update_action(self, new_action, now):
    if new_action != self.action:
      self.action = new_action
      self.frame_index = 0
      self.update_time = now

  def draw(self, surface, cam):
    x = self.rect.x - cam[0]
    y = self.rect.y - cam[1]
    if self.char_type == 0:
      y -= C.SCALE * C.OFFSET
    surface.blit(self.image, (x, y))
