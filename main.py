import math
import os
import pygame
from pygame import mixer
import constants as C
from weapon import Weapon
from items import Item
from world import World, load_level_data
import ui
from title_screen import TitleScene, Overlay
from ui import Menu


mixer.init()
pygame.init()


screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
GAME_TITLE = 'The Desmōtērion'
pygame.display.set_caption(GAME_TITLE)
clock = pygame.time.Clock()
font = ui.game_font(20)  


def scale_img(image, scale):
  pass


def load_img(path, scale=1):
  pass


def load_sound(path, volume):
  sound = mixer.Sound(path)
  sound.set_volume(volume)
  return sound


def draw_text(text, fnt, colour, x, y, center=False):
  img = fnt.render(text, True, colour)
  screen.blit(img, img.get_rect(center=(x, y)) if center else (x, y))


def level_exists(n):
  pass




#==============================================


class Camera():
  pass


class DamageText(pygame.sprite.Sprite):
  pass


#================================================


class ScreenFade():
  def __init__(self, direction, colour, speed):
    self.direction = direction
    self.colour = colour
    self.speed = speed
    self.fade_counter = 0

  def fade(self):
    self.fade_counter += self.speed
    W, H, f = C.SCREEN_WIDTH, C.SCREEN_HEIGHT, self.fade_counter
    if self.direction == 1:  # whole screen opens out from the centre
      pygame.draw.rect(screen, self.colour, (0 - f, 0, W // 2, H))
      pygame.draw.rect(screen, self.colour, (W // 2 + f, 0, W, H))
      pygame.draw.rect(screen, self.colour, (0, 0 - f, W, H // 2))
      pygame.draw.rect(screen, self.colour, (0, H // 2 + f, W, H))
    elif self.direction == 2:  # curtain falls down
      pygame.draw.rect(screen, self.colour, (0, 0, W, f))
    return self.fade_counter >= W

#========================================


class Game():
  def __init__(self):
    pass

  def load(self, level, health=None, score=0):
    pass

  def level_complete(self):
    pass

  def update(self, keys, mouse_pos, mouse_down):
    pass

  def draw(self):
    pass

  def draw_info(self):
    pass

#===============================================

OPEN_TIME = 1.5   
FADE_TIME = 0.5 


def ease_in_out(x):
  return x * x * (3 - 2 * x)


def main():
  game = Game()
  scene = TitleScene()
  overlay = Overlay(scene)
  intro_fade = ScreenFade(1, C.BLACK, 4)
  death_fade = ScreenFade(2, C.BLOOD, 4)
  black = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
  cx, cy = C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2
  tick = scene.tick
  main_menu = Menu([('ENTER THE PRISON', 'start'), ('FLEE', 'quit')], cx, 508, 44, tick_sound=tick)
  pause_menu = Menu([('RESUME', 'resume'), ('FLEE', 'quit')], cx, cy + 40, 50, tick_sound=tick)
  won_menu = Menu([('DESCEND AGAIN', 'again'), ('FLEE', 'quit')], cx, 508, 44, tick_sound=tick)
  death_menu = Menu([('RISE AGAIN', 'restart')], cx, cy + 70, 50, tick_sound=tick)
  paused_text = ui.CarvedText(ui.fit_font('PAUSED', 500, 72), 'PAUSED')
  dead_text = ui.CarvedText(ui.fit_font('YOU HAVE PERISHED', 700, 64), 'YOU HAVE PERISHED', stops=ui.BLOOD,
                            glow=(120, 0, 0))
  won_text = ui.CarvedText(ui.fit_font('YOU ESCAPED', 700, 80), 'YOU ESCAPED')
  coins_font = ui.font_for('COINS 0123456789', 24)
  state = 'menu'
  start_intro = False
  open_started = 0.0
  last = pygame.time.get_ticks() / 1000
  run = True

  while run:
    clock.tick(C.FPS)
    now = pygame.time.get_ticks() / 1000
    dt, last = min(0.05, now - last), now

    events = pygame.event.get()
    for event in events:
      if event.type == pygame.QUIT:
        run = False
      elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        if state == 'playing' and game.player.alive:
          overlay.capture(screen)
          state = 'paused'
          events = []  
        elif state == 'paused':
          state = 'playing'
          game.bow.fired = True
    mouse_pos = pygame.mouse.get_pos()

    if state in ('menu', 'opening', 'won'):
      scene.update(dt, now)
      scene.draw(screen, now, mouse_pos, show_title=state != 'won')

    if state == 'menu':
      action = main_menu.handle(events, mouse_pos)
      main_menu.draw(screen, now)
      if action == 'start':
        state, open_started = 'opening', now
        scene.open_gate()
      elif action == 'quit':
        run = False

    elif state == 'opening':
      p = (now - open_started) / OPEN_TIME
      scene.raise_amount = ease_in_out(min(1.0, p))
      scene.eye_alpha = max(0.0, 1 - p * 2.5)
      if p < 1:  
        k = int(3 * (1 - p))
        screen.scroll(scene.rng.randint(-k, k), scene.rng.randint(-k, k))
      fade = (now - open_started - OPEN_TIME) / FADE_TIME
      if fade > 0:
        black.set_alpha(int(255 * min(1, fade)))
        screen.blit(black, (0, 0))
      if fade >= 1:
        game.load(1)
        state, start_intro = 'playing', True
        intro_fade.fade_counter = 0

    elif state == 'paused':
      overlay.draw(screen)
      paused_text.draw(screen, (cx, cy - 70), glow_alpha=150)
      action = pause_menu.handle(events, mouse_pos)
      pause_menu.draw(screen, now)
      if action == 'resume':
        state = 'playing'
        game.bow.fired = True
      elif action == 'quit':
        run = False

    elif state == 'won':
      won_text.draw(screen, (cx, 92), glow_alpha=int(130 + 50 * math.sin(now * 2)), shine_pos=(now % 5) / 1.3 if now % 5 < 1.3 else None)
      coins = coins_font.render(f'COINS  {game.player.score}', True, (240, 200, 120))
      screen.blit(coins, coins.get_rect(center=(cx, 160)))
      action = won_menu.handle(events, mouse_pos)
      won_menu.draw(screen, now)
      if action == 'again':
        game.load(1)
        state, start_intro = 'playing', True
      elif action == 'quit':
        run = False

    else:  
      if game.player.alive:
        game.update(pygame.key.get_pressed(), mouse_pos, pygame.mouse.get_pressed()[0])
      game.draw()

      if game.player.alive and game.level_complete():
        if level_exists(game.level + 1):
          game.load(game.level + 1, game.player.health, game.player.score)
          start_intro = True
        else:
          scene.raise_amount, scene.eye_alpha = 1.0, 0.0  
          state = 'won'

      if start_intro and intro_fade.fade():
        start_intro = False
        intro_fade.fade_counter = 0

      if not game.player.alive and death_fade.fade():
        dead_text.draw(screen, (cx, cy - 40), glow_alpha=160)
        if death_menu.handle(events, mouse_pos) == 'restart':
          death_fade.fade_counter = 0
          start_intro = True
          game.load(game.level, score=game.player.score)
        else:
          death_menu.draw(screen, now)

    pygame.display.update()

  pygame.quit()


if __name__ == '__main__':
  main()