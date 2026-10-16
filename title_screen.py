import array
import math
import random
import pygame
import constants as C
import ui

W, H = C.SCREEN_WIDTH, C.SCREEN_HEIGHT
GATE_X = W // 2
ARCH_Y = 345
R_IN, R_OUT = 105, 145
FLOOR_Y = 470
OPEN = pygame.Rect(GATE_X - R_IN, ARCH_Y - R_IN, R_IN * 2, FLOOR_Y - (ARCH_Y - R_IN))
TORCHES = [(GATE_X - 232, 292), (GATE_X + 232, 292)]
AMBIENT = (34, 27, 30)


def radial(radius, colour, power=1.8, alpha=False):
  size = radius * 2
  surf = pygame.Surface((size, size), pygame.SRCALPHA if alpha else 0)
  for r in range(radius, 0, -1):
    k = (1 - r / radius) ** power
    if alpha:
      pygame.draw.circle(surf, (*colour, int(255 * k)), (radius, radius), r)
    else:
      pygame.draw.circle(surf, [int(c * k) for c in colour], (radius, radius), r)
  return surf


def shade(col, k):
  return tuple(max(0, min(255, int(c * k))) for c in col)


def opening_mask():
  m = pygame.Surface(OPEN.size, pygame.SRCALPHA)
  pygame.draw.circle(m, (255, 255, 255, 255), (R_IN, R_IN), R_IN)
  pygame.draw.rect(m, (255, 255, 255, 255), (0, R_IN, R_IN * 2, OPEN.h - R_IN))
  return m


def synth(seconds, fn, volume):
  init = pygame.mixer.get_init()
  if not init or init[1] != -16:
    return None
  rate, _, chans = init
  data = array.array('h')
  for i in range(int(rate * seconds)):
    v = int(max(-1.0, min(1.0, fn(i / rate))) * 32767 * volume)
    data.extend([v] * chans)
  try:
    return pygame.mixer.Sound(buffer=data.tobytes())
  except pygame.error:
    return None

def make_sounds():
  rng = random.Random(3)
  state = {'b': 0.0}

  def rumble(t):  
    state['b'] = state['b'] * 0.985 + (rng.random() * 2 - 1) * 0.06
    env = min(1, t / 0.08) * min(1, (1.6 - t) / 0.5)
    ratchet = 0.0
    phase = (t * 17) % 1
    if phase < 0.08:
      ratchet = (rng.random() * 2 - 1) * (1 - phase / 0.08) * 0.6
    return (state['b'] * 6 + ratchet + math.sin(t * 2 * math.pi * 42) * 0.25) * env

  def tick(t):
    return (math.sin(t * 2 * math.pi * 1900) * 0.6 + (rng.random() * 2 - 1) * 0.4) * math.exp(-t * 90)

  return synth(1.6, rumble, 0.55), synth(0.06, tick, 0.18)


class TitleScene():
  def __init__(self):
    rng = random.Random(7)
    self.rng = random.Random()
    self.wall = self._build_wall(rng)
    self.lightmap = pygame.Surface((W, H))
    self.torch_light = [radial(340, shade((255, 168, 92), 0.55 + 0.45 * i / 11), 1.5) for i in range(12)]
    self.gate_light = [radial(230, shade((140, 26, 14), 0.5 + 0.5 * i / 7), 1.6) for i in range(8)]
    self.mask = opening_mask()
    self.interior = self._build_interior()
    self.inner_glow = [radial(150, shade((190, 34, 12), 0.4 + 0.6 * i / 7), 1.4) for i in range(8)]
    self.portcullis_raw = self._build_portcullis()
    self.portcullis = self._clip(self.portcullis_raw, 0)
    self.flame_halo = radial(60, (255, 120, 40), 1.6)
    self.eye_glow = {s: [radial(int(s * 5), shade((220, 30, 10), k / 6), 1.5) for k in range(7)]
                     for s in (2.5, 3, 4, 7)}
    self.ember_dots = [[radial(r, c, 1.2) for c in ((255, 236, 160), (255, 170, 60), (240, 90, 20), (170, 30, 10))]
                       for r in (2, 3, 5)]
    self.fog = [self._build_fog(rng, 46), self._build_fog(rng, 30)]
    self.vignette = self._build_vignette()

    self.eyes = [
      dict(x=384, y=328, sp=30, s=7),    
      dict(x=339, y=398, sp=15, s=4),
      dict(x=459, y=372, sp=15, s=4),
      dict(x=429, y=438, sp=15, s=3),
      dict(x=399, y=284, sp=15, s=2.5),
    ]
    for e in self.eyes:
      e['blink_at'] = self.rng.uniform(1, 5)
      e['fade_in'] = self.rng.uniform(0.6, 2.4)
    self.embers = []
    self.raise_amount = 0.0 
    self.eye_alpha = 1.0
    self.start_time = None
    self.flicker_phase = [0.0, 2.1]

    # title
    self.the = ui.CarvedText(ui.font_for('THE', 26), 'THE', depth=2, outline=1, glow=None, spacing=10)
    self.title = ui.CarvedText(ui.fit_font('DESMŌTĒRION', 700, 104), 'DESMŌTĒRION', depth=6, outline=2)
    greek = 'ΔΕΣΜΩΤΗΡΙΟΝ'
    self.greek = ui.CarvedText(ui.font_for(greek, 20), greek, stops=ui.BLOOD, depth=1, outline=1,
                               glow=(160, 20, 10), spacing=7)
    hint = 'WASD  MOVE      MOUSE  AIM & LOOSE      ESC  PAUSE'
    self.hint = ui.font_for(hint, 13).render(hint, True, (120, 100, 84))
    self.rumble, self.tick = make_sounds()

  def _build_wall(self, rng):
    pass

  def _build_interior(self):
    pass

  def _build_portcullis(self):
    pass

  def _clip(self, raw, offset):
    pass

  def _build_fog(self, rng, alpha):
    pass

  def _build_vignette(self):
    pass

  def open_gate(self):
    pass

  def _flicker(self, t, i):
    pass

  def _spawn_embers(self, dt):
    pass

  def update(self, dt, t):
    pass

  def draw(self, screen, t, mouse=(GATE_X, 0), show_title=True):
    pass

  def draw_title(self, screen, t):
    pass

  def _draw_flame(self, screen, x, y, t, ph, f):
    pass

  def _draw_eyes(self, screen, t, age, mouse):
    pass


class Overlay():
  def __init__(self, scene):
    self.vignette = scene.vignette
    self.dark = pygame.Surface((W, H), pygame.SRCALPHA)
    self.dark.fill((8, 2, 2, 170))
    self.snapshot = None

  def capture(self, screen):
    self.snapshot = screen.copy()

  def draw(self, screen):
    if self.snapshot:
      screen.blit(self.snapshot, (0, 0))
    screen.blit(self.dark, (0, 0))
    screen.blit(self.vignette, (0, 0))