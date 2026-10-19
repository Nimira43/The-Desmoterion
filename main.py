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
  return pygame.transform.scale(image, (image.get_width() * scale, image.get_height() * scale))


def load_img(path, scale=1):
  return scale_img(pygame.image.load(path).convert_alpha(), scale)


def load_sound(path, volume):
  sound = mixer.Sound(path)
  sound.set_volume(volume)
  return sound


mixer.music.load('assets/audio/music.mp3')
mixer.music.set_volume(0.3)
mixer.music.play(-1, 0.0, 5000)
sounds = {
  'shot': load_sound('assets/audio/arrow_shot.mp3', 0.5),
  'hit': load_sound('assets/audio/arrow_hit.mp3', 0.5),
  'coin': load_sound('assets/audio/coin.mp3', 0.5),
  'heal': load_sound('assets/audio/heal.mp3', 0.5),
}

heart_empty = load_img('assets/images/items/heart_empty.png', C.ITEM_SCALE)
heart_half = load_img('assets/images/items/heart_half.png', C.ITEM_SCALE)
heart_full = load_img('assets/images/items/heart_full.png', C.ITEM_SCALE)

coin_images = [load_img(f'assets/images/items/coin_f{i}.png', C.ITEM_SCALE) for i in range(4)]
red_potion = load_img('assets/images/items/potion_red.png', C.POTION_SCALE)
item_images = [coin_images, red_potion]

bow_image = load_img('assets/images/weapons/bow.png', C.WEAPON_SCALE)
arrow_image = load_img('assets/images/weapons/arrow.png', C.WEAPON_SCALE)
fireball_image = load_img('assets/images/weapons/fireball.png', C.FIREBALL_SCALE)

tile_list = [
  pygame.transform.scale(pygame.image.load(f'assets/images/tiles/{i}.png').convert_alpha(), (C.TILE_SIZE, C.TILE_SIZE))
  for i in range(C.TILE_TYPES)
]

mob_types = ['elf', 'imp', 'skeleton', 'goblin', 'mud_crab', 'zombie', 'demon']
animation_types = ['idle', 'run']
mob_animations = []
for mob in mob_types:
  actions = [[load_img(f'assets/images/characters/{mob}/{anim}/{i}.png', C.SCALE) for i in range(4)]
             for anim in animation_types]
  flipped = [[pygame.transform.flip(img, True, False) for img in frames] for frames in actions]
  mob_animations.append([actions, flipped])


def draw_text(text, fnt, colour, x, y, center=False):
  img = fnt.render(text, True, colour)
  screen.blit(img, img.get_rect(center=(x, y)) if center else (x, y))


def level_exists(n):
  return os.path.exists(f'levels/level{n}_data.csv')


class Camera():
  def __init__(self):
    self.x = 0
    self.y = 0

  def follow(self, rect):
    W, H, TH = C.SCREEN_WIDTH, C.SCREEN_HEIGHT, C.SCROLL_THRESH
    sx, sy = rect.x - self.x, rect.y - self.y
    if sx + rect.w > W - TH:
      self.x += sx + rect.w - (W - TH)
    elif sx < TH:
      self.x -= TH - sx
    if sy + rect.h > H - TH:
      self.y += sy + rect.h - (H - TH)
    elif sy < TH:
      self.y -= TH - sy

  @property
  def pos(self):
    return (self.x, self.y)

  @property
  def view(self):
    return pygame.Rect(self.x, self.y, C.SCREEN_WIDTH, C.SCREEN_HEIGHT)


class DamageText(pygame.sprite.Sprite):
  def __init__(self, x, y, damage, colour):
    super().__init__()
    self.image = font.render(damage, True, colour)
    self.rect = self.image.get_rect(center=(x, y))
    self.counter = 0

  def update(self):
    self.rect.y -= 1
    self.counter += 1
    if self.counter > 30:
      self.kill()

  def draw(self, surface, cam):
    surface.blit(self.image, (self.rect.x - cam[0], self.rect.y - cam[1]))


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


class Game():
  def __init__(self):
    self.level = 1
    self.bow = Weapon(bow_image, arrow_image)
    self.score_coin = Item(C.SCREEN_WIDTH - 115, 23, 0, coin_images)
    self._score_cache = (None, None)
    self.load(1)

  def load(self, level, health=None, score=0):
    self.level = level
    self.world = World(load_level_data(level), tile_list, item_images, mob_animations)
    self.player = self.world.player
    if health is not None:
      self.player.health = health
    self.player.score = score
    self.enemies = self.world.character_list
    self.items = pygame.sprite.Group(self.world.item_list)
    self.arrows = pygame.sprite.Group()
    self.fireballs = pygame.sprite.Group()
    self.damage_texts = pygame.sprite.Group()
    self.camera = Camera()
    self.camera.follow(self.player.rect)
    self.level_text = font.render(f'LEVEL: {level}', True, C.WHITE)
    self.bow.fired = True  

  def level_complete(self):
    ex = self.world.exit_rect
    if ex is None or not ex.colliderect(self.player.rect):
      return False
    return math.dist(self.player.rect.center, ex.center) < 20

  def update(self, keys, mouse_pos, mouse_down):
    now = pygame.time.get_ticks()
    player, world = self.player, self.world

    dx = (keys[pygame.K_d] - keys[pygame.K_a]) * C.SPEED
    dy = (keys[pygame.K_s] - keys[pygame.K_w]) * C.SPEED
    player.move(dx, dy, world)
    self.camera.follow(player.rect)
    cam, view = self.camera.pos, self.camera.view

    for enemy in self.enemies:
      fireball = enemy.ai(player, world, fireball_image, now)
      if fireball:
        self.fireballs.add(fireball)
      enemy.update(now)
    self.enemies = [e for e in self.enemies if e.alive]
    player.update(now)

    arrow = self.bow.update(player, cam, mouse_pos, mouse_down, now)
    if arrow:
      self.arrows.add(arrow)
      sounds['shot'].play()
    for arrow in self.arrows.sprites():
      damage, pos = arrow.update(world, view, self.enemies)
      if damage:
        self.damage_texts.add(DamageText(pos.centerx, pos.y, str(damage), C.RED))
        sounds['hit'].play()

    self.damage_texts.update()
    self.fireballs.update(world, view, player, now)
    self.items.update(player, sounds, now)
    self.score_coin.animate(now)

  def draw(self):
    cam = self.camera.pos
    screen.fill(C.BG)
    self.world.draw(screen, cam)
    for item in self.items:
      item.draw(screen, cam)
    for enemy in self.enemies:
      enemy.draw(screen, cam)
    self.player.draw(screen, cam)
    self.bow.draw(screen, self.player, cam)
    for group in (self.arrows, self.fireballs, self.damage_texts):
      for sprite in group:
        sprite.draw(screen, cam)
    self.draw_info()

  def draw_info(self):
    pygame.draw.rect(screen, C.PANEL, (0, 0, C.SCREEN_WIDTH, C.PANEL_HEIGHT))
    pygame.draw.line(screen, C.WHITE, (0, C.PANEL_HEIGHT), (C.SCREEN_WIDTH, C.PANEL_HEIGHT))
    hp = self.player.health
    half_drawn = False
    for i in range(5):
      if hp >= (i + 1) * 20:
        heart = heart_full
      elif hp % 20 > 0 and not half_drawn:
        heart = heart_half
        half_drawn = True
      else:
        heart = heart_empty
      screen.blit(heart, (10 + i * 50, 0))
    screen.blit(self.level_text, (C.SCREEN_WIDTH / 2, 15))
    if self._score_cache[0] != self.player.score:
      self._score_cache = (self.player.score, font.render(f'X{self.player.score}', True, C.WHITE))
    screen.blit(self._score_cache[1], (C.SCREEN_WIDTH - 100, 15))
    self.score_coin.draw(screen, (0, 0))


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
