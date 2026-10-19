import pygame
import constants as C

COIN = 0
POTION = 1


class Item(pygame.sprite.Sprite):
  def __init__(self, x, y, item_type, animation_list):
    super().__init__()
    self.item_type = item_type
    self.animation_list = animation_list
    self.frame_index = 0
    self.update_time = pygame.time.get_ticks()
    self.image = animation_list[0]
    self.rect = self.image.get_rect(center=(x, y))

  def animate(self, now):
    if len(self.animation_list) > 1 and now - self.update_time > C.ITEM_ANIM_COOLDOWN:
      self.frame_index = (self.frame_index + 1) % len(self.animation_list)
      self.image = self.animation_list[self.frame_index]
      self.update_time = now

  def update(self, player, sounds, now):
    if self.rect.colliderect(player.rect):
      if self.item_type == COIN:
        player.score += 1
        sounds['coin'].play()
      else:
        player.health = min(player.health + 10, 100)
        sounds['heal'].play()
      self.kill()
      return
    self.animate(now)

  def draw(self, surface, cam):
    surface.blit(self.image, (self.rect.x - cam[0], self.rect.y - cam[1]))
