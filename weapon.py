import math
import random
import pygame
import constants as C

_rot_cache = {}


def rotated(image, angle):
  key = (id(image), round(angle) % 360)
  img = _rot_cache.get(key)
  if img is None:
    img = pygame.transform.rotate(image, key[1])
    _rot_cache[key] = img
  return img


def _blit_centered(surface, image, cx, cy):
  surface.blit(image, (cx - image.get_width() // 2, cy - image.get_height() // 2))


class Weapon():
  def __init__(self, image, arrow_image):
    self.original_image = image
    self.arrow_image = arrow_image
    self.angle = 0
    self.fired = True 
    self.last_shot = pygame.time.get_ticks()

  def update(self, player, cam, mouse_pos, mouse_down, now):
    arrow = None
    px, py = player.rect.center

    self.angle = math.degrees(math.atan2(-(mouse_pos[1] - (py - cam[1])), mouse_pos[0] - (px - cam[0])))

    if mouse_down and not self.fired and now - self.last_shot >= C.SHOT_COOLDOWN:
      arrow = Arrow(self.arrow_image, px, py, self.angle)
      self.fired = True
      self.last_shot = now
    if not mouse_down:
      self.fired = False
    return arrow

  def draw(self, surface, player, cam):
    _blit_centered(surface, rotated(self.original_image, self.angle),
                   player.rect.centerx - cam[0], player.rect.centery - cam[1])


class Projectile(pygame.sprite.Sprite):
  def __init__(self, image, x, y, angle, speed):
    super().__init__()
    self.image = rotated(image, angle - 90)
    self.rect = self.image.get_rect(center=(x, y))
    self.fx, self.fy = float(x), float(y)
    rad = math.radians(angle)
    self.dx = math.cos(rad) * speed
    self.dy = -math.sin(rad) * speed

  def step(self, world, view):
    self.fx += self.dx
    self.fy += self.dy
    self.rect.center = (round(self.fx), round(self.fy))
    if not view.colliderect(self.rect) or world.walls_overlapping(self.rect):
      self.kill()
      return False
    return True

  def draw(self, surface, cam):
    _blit_centered(surface, self.image, self.rect.centerx - cam[0], self.rect.centery - cam[1])


class Arrow(Projectile):
  def __init__(self, image, x, y, angle):
    super().__init__(image, x, y, angle, C.ARROW_SPEED)

  def update(self, world, view, enemy_list):
    if not self.step(world, view):
      return 0, None
    for enemy in enemy_list:
      if enemy.alive and enemy.rect.colliderect(self.rect):
        damage = 10 + random.randint(-5, 5)
        enemy.health -= damage
        enemy.hit = True
        self.kill()
        return damage, enemy.rect
    return 0, None


class Fireball(Projectile):
  def __init__(self, image, x, y, target_x, target_y):
    angle = math.degrees(math.atan2(-(target_y - y), target_x - x))
    super().__init__(image, x, y, angle, C.FIREBALL_SPEED)

  def update(self, world, view, player, now):
    if not self.step(world, view):
      return
    if not player.hit and player.rect.colliderect(self.rect):
      player.take_hit(10, now)
      self.kill()
