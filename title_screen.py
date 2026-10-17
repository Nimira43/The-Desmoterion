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

    self.the = ui.CarvedText(ui.font_for('The', 26), 'The', depth=2, outline=1, glow=None, spacing=10)
    self.title = ui.CarvedText(ui.fit_font('Desmoterion', 700, 104), 'Desmoterion', depth=6, outline=2)
    greek = 'ΔΕΣΜΩΤΗΡΙΟΝ'
    self.greek = ui.CarvedText(ui.font_for(greek, 20), greek, stops=ui.BLOOD, depth=1, outline=1,
                               glow=(160, 20, 10), spacing=7)
    hint = 'WASD  MOVE      MOUSE  AIM & LOOSE      ESC  PAUSE'
    self.hint = ui.font_for(hint, 13).render(hint, True, (120, 100, 84))
    self.rumble, self.tick = make_sounds()

  def _build_wall(self, rng):
    wall = pygame.Surface((W, H))
    wall.fill((22, 18, 17))  # mortar
    bh, bw = 30, 66
    for row in range(FLOOR_Y // bh + 1):
      x = -((row % 2) * bw // 2) - rng.randint(0, 10)
      y = row * bh
      while x < W:
        ww = bw + rng.randint(-16, 16)
        base = rng.randint(84, 118)
        col = (base + 8, base, base - 8)
        r = pygame.Rect(x + 2, y + 2, ww - 3, bh - 3)
        pygame.draw.rect(wall, col, r, border_radius=3)
        pygame.draw.line(wall, shade(col, 1.25), (r.left + 2, r.top), (r.right - 3, r.top))
        pygame.draw.line(wall, shade(col, 0.6), (r.left + 2, r.bottom - 1), (r.right - 3, r.bottom - 1))
        for _ in range(ww * bh // 30):
          px, py = rng.randint(r.left, r.right - 1), rng.randint(r.top, r.bottom - 1)
          if 0 <= px < W and 0 <= py < H:
            wall.set_at((px, py), shade(col, rng.uniform(0.7, 1.15)))
        if rng.random() < 0.12:  # crack
          cx, cy = rng.randint(r.left + 6, r.right - 6), r.top + 2
          for _ in range(3):
            nx, ny = cx + rng.randint(-6, 6), cy + rng.randint(5, 9)
            pygame.draw.line(wall, shade(col, 0.45), (cx, cy), (nx, min(ny, r.bottom - 2)))
            cx, cy = nx, ny
        x += ww

    pygame.draw.rect(wall, (30, 25, 24), (0, FLOOR_Y, W, H - FLOOR_Y))
    y, rh = FLOOR_Y + 2, 18
    while y < H:
      x = -rng.randint(0, 60)
      while x < W:
        sw = rng.randint(70, 120) + rh
        base = rng.randint(66, 88)
        r = pygame.Rect(x + 2, y, sw - 4, rh - 3)
        pygame.draw.rect(wall, (base + 4, base, base - 4), r, border_radius=2)
        pygame.draw.line(wall, (base + 30, base + 24, base + 16), r.topleft, r.topright)
        x += sw
      y += rh
      rh = int(rh * 1.3)
    pygame.draw.line(wall, (12, 9, 8), (0, FLOOR_Y), (W, FLOOR_Y), 3)

    step = pygame.Rect(GATE_X - R_OUT - 14, FLOOR_Y - 2, (R_OUT + 14) * 2, 16)
    pygame.draw.rect(wall, (110, 102, 96), step, border_radius=2)
    pygame.draw.line(wall, (150, 140, 128), step.topleft, step.topright, 2)
    pygame.draw.rect(wall, (50, 44, 42), (step.x, step.bottom - 5, step.w, 5))

    for side in (-1, 1):
      x0 = GATE_X + side * R_IN if side > 0 else GATE_X - R_OUT
      y = ARCH_Y
      i = 0
      while y < FLOOR_Y - 2:
        h = min(32, FLOOR_Y - 2 - y)
        wdt = R_OUT - R_IN + (8 if i % 2 else 0)
        x = x0 if side > 0 else x0 - (8 if i % 2 else 0)
        r = pygame.Rect(x, y, wdt, h - 2)
        base = 128 + rng.randint(-10, 10)
        pygame.draw.rect(wall, (base + 6, base, base - 6), r, border_radius=2)
        pygame.draw.line(wall, (base + 50, base + 44, base + 34), r.topleft, r.topright)
        pygame.draw.line(wall, (base - 60,) * 3, r.bottomleft, r.bottomright)
        y += h
        i += 1

    n = 13
    for i in range(n):
      a0 = math.pi + math.pi * i / n
      a1 = math.pi + math.pi * (i + 1) / n
      key = i == n // 2
      ro = R_OUT + (16 if key else 0)
      pts = []
      for a in (a0 + 0.012, a1 - 0.012):
        pts.append((GATE_X + math.cos(a) * (R_IN + 1), ARCH_Y + math.sin(a) * (R_IN + 1)))
      for a in (a1 - 0.012, a0 + 0.012):
        pts.append((GATE_X + math.cos(a) * ro, ARCH_Y + math.sin(a) * ro))
      pts = [pts[0], pts[1], pts[2], pts[3]]
      base = (150 if key else 126) + rng.randint(-10, 10)
      col = (base + 6, base, base - 8)
      pygame.draw.polygon(wall, col, pts)
      pygame.draw.polygon(wall, shade(col, 0.5), pts, 2)
      if key:  
        kx, ky = GATE_X, ARCH_Y - R_IN - 24
        pygame.draw.polygon(wall, (60, 52, 48), [(kx, ky - 13), (kx + 9, ky), (kx, ky + 13), (kx - 9, ky)])
        pygame.draw.polygon(wall, (190, 180, 168), [(kx, ky - 13), (kx + 9, ky), (kx, ky + 13), (kx - 9, ky)], 1)
        pygame.draw.circle(wall, (20, 14, 12), (kx, ky), 3)

    for cx, length in ((52, 250), (118, 170), (W - 118, 200), (W - 52, 270)):
      y = -8
      i = 0
      while y < length:
        if i % 2 == 0:
          pygame.draw.ellipse(wall, (70, 64, 60), (cx - 7, y, 14, 22), 4)
          pygame.draw.arc(wall, (150, 136, 120), (cx - 7, y, 14, 22), 1.8, 3.6, 2)
        else:
          pygame.draw.rect(wall, (58, 52, 50), (cx - 2, y + 2, 5, 18), border_radius=2)
          pygame.draw.line(wall, (140, 126, 110), (cx - 1, y + 4), (cx - 1, y + 17))
        y += 15
        i += 1
      pygame.draw.circle(wall, (66, 60, 56), (cx, y + 14), 15, 5)
      pygame.draw.arc(wall, (150, 136, 120), (cx - 15, y - 1, 30, 30), 2.0, 3.8, 2)

    for tx, ty in TORCHES:
      iron, rim = (64, 56, 52), (190, 150, 110)
      pygame.draw.rect(wall, iron, (tx - 11, ty + 34, 22, 34), border_radius=3)
      for ry in (ty + 40, ty + 60):
        pygame.draw.circle(wall, rim, (tx, ry), 2)
      pygame.draw.rect(wall, iron, (tx - 3, ty + 14, 6, 24))
      cup = [(tx - 16, ty + 2), (tx + 16, ty + 2), (tx + 9, ty + 16), (tx - 9, ty + 16)]
      pygame.draw.polygon(wall, iron, cup)
      pygame.draw.line(wall, rim, (tx - 16, ty + 2), (tx + 16, ty + 2), 2)
    return wall

  def _build_interior(self):
    s = ui.vgradient(OPEN.size, [(2, 1, 1), (6, 2, 2), (26, 8, 6)])
    s.blit(self.mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return s

  def _build_portcullis(self):
    w, h = OPEN.w, OPEN.h + 30
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    iron, hi, lo = (34, 30, 30), (120, 86, 60), (14, 12, 12)
    xs = list(range(14, w - 6, 30))
    for y in range(18, h - 40, 48):  
      pygame.draw.rect(s, iron, (0, y, w, 8))
      pygame.draw.line(s, hi, (0, y), (w, y))
      pygame.draw.line(s, lo, (0, y + 7), (w, y + 7))
    for x in xs: 
      pygame.draw.rect(s, iron, (x - 5, 0, 10, h - 34))
      pygame.draw.line(s, hi, (x - 5, 0), (x - 5, h - 34))
      pygame.draw.line(s, lo, (x + 4, 0), (x + 4, h - 34))
      tip = [(x - 5, h - 34), (x + 5, h - 34), (x, h - 14)]
      pygame.draw.polygon(s, iron, tip)
      pygame.draw.line(s, hi, tip[0], tip[2])
      for y in range(18, h - 40, 48):  
        pygame.draw.circle(s, (80, 64, 52), (x, y + 4), 3)
        pygame.draw.circle(s, (170, 130, 90), (x - 1, y + 3), 1)
    return s

  def _clip(self, raw, offset):
    s = pygame.Surface(OPEN.size, pygame.SRCALPHA)
    s.blit(raw, (0, -offset - 16))
    s.blit(self.mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return s

  def _build_fog(self, rng, alpha):
    fog = pygame.Surface((W * 2, 200), pygame.SRCALPHA)
    blobs = [radial(r, (150, 120, 120), 1.3, alpha=True) for r in (60, 90, 120)]
    for b in blobs:
      b.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    for _ in range(70):
      b = rng.choice(blobs)
      x = rng.randint(0, W * 2 - b.get_width())
      y = rng.randint(30, 200 - b.get_height() // 2) - b.get_height() // 3
      fog.blit(b, (x, y))
    left = fog.subsurface((0, 0, W, 200)).copy()
    fog.blit(left, (W, 0))
    return fog

  def _build_vignette(self):
    size = 400
    v = pygame.Surface((size, size), pygame.SRCALPHA)
    v.fill((0, 0, 0, 235))
    half = size // 2
    for r in range(int(half * 1.42), 0, -1):
      k = max(0.0, (r / half - 0.55) / 0.87)
      pygame.draw.circle(v, (0, 0, 0, int(235 * min(1, k) ** 1.6)), (half, half), r)
    return pygame.transform.smoothscale(v, (W, H))

  def open_gate(self):
    if self.rumble:
      self.rumble.play()

  def _flicker(self, t, i):
    p = self.flicker_phase[i]
    v = 0.72 + 0.14 * math.sin(t * 7.3 + p) + 0.08 * math.sin(t * 17.9 + p * 2) + self.rng.uniform(-0.06, 0.06)
    return max(0.0, min(1.0, v))

  def _spawn_embers(self, dt):
    for tx, ty in TORCHES:
      if self.rng.random() < dt * 22:
        self.embers.append([tx + self.rng.uniform(-6, 6), ty - 20, self.rng.uniform(-12, 12),
                            self.rng.uniform(-75, -40), 0.0, self.rng.uniform(1.2, 2.6), self.rng.randrange(2),
                            self.rng.uniform(0, 6)])
    if self.rng.random() < dt * (7 + 30 * self.raise_amount):
      self.embers.append([self.rng.uniform(OPEN.left + 10, OPEN.right - 10), FLOOR_Y - self.rng.uniform(0, 40),
                          self.rng.uniform(-8, 8), self.rng.uniform(-45, -20), 0.0, self.rng.uniform(3, 6),
                          self.rng.choice((0, 0, 1)), self.rng.uniform(0, 6)])

  def update(self, dt, t):
    if self.start_time is None:
      self.start_time = t
    self._spawn_embers(dt)
    alive = []
    for e in self.embers:
      e[4] += dt
      if e[4] < e[5] and e[1] > -10:
        e[0] += (e[2] + math.sin(t * 2.3 + e[7]) * 14) * dt
        e[1] += e[3] * dt
        alive.append(e)
    self.embers = alive[-260:]

  def draw(self, screen, t, mouse=(GATE_X, 0), show_title=True):
    age = t - (self.start_time or t)

    lm = self.lightmap
    lm.fill(AMBIENT)
    flick = []
    for i, (tx, ty) in enumerate(TORCHES):
      f = self._flicker(t, i)
      flick.append(f)
      img = self.torch_light[int(f * 11)]
      r = img.get_width() // 2
      lm.blit(img, (tx - r + self.rng.randint(-2, 2), ty - 20 - r + self.rng.randint(-2, 2)),
              special_flags=pygame.BLEND_ADD)
    pulse = 0.5 + 0.5 * math.sin(t * 1.7)
    g = self.gate_light[min(7, int((pulse * 0.7 + self.raise_amount * 0.3) * 7.99))]
    lm.blit(g, (GATE_X - g.get_width() // 2, FLOOR_Y - 60 - g.get_height() // 2), special_flags=pygame.BLEND_ADD)
    screen.blit(self.wall, (0, 0))
    screen.blit(lm, (0, 0), special_flags=pygame.BLEND_MULT)

    screen.blit(self.interior, OPEN)
    screen.set_clip(OPEN)
    ig = self.inner_glow[min(7, int((pulse * 0.6 + 0.4 * self.raise_amount) * 7.99))]
    screen.blit(ig, (GATE_X - 150, FLOOR_Y - 120), special_flags=pygame.BLEND_ADD)
    self._draw_eyes(screen, t, age, mouse)
    screen.set_clip(None)

    if self.raise_amount > 0:
      if self.raise_amount < 1:
        screen.blit(self._clip(self.portcullis_raw, int(self.raise_amount * (OPEN.h + 30))), OPEN)
    else:
      screen.blit(self.portcullis, OPEN)

    for i, (tx, ty) in enumerate(TORCHES):
      self._draw_flame(screen, tx, ty, t, i * 2.7, flick[i])
    for e in self.embers:
      life = e[4] / e[5]
      dots = self.ember_dots[e[6]]
      img = dots[min(3, int(life * 4))]
      screen.blit(img, (e[0] - img.get_width() // 2, e[1] - img.get_height() // 2), special_flags=pygame.BLEND_ADD)
    for k, fog in enumerate(self.fog):
      speed = 14 if k == 0 else 26
      off = int(t * speed) % W
      y = FLOOR_Y - 90 + k * 40
      screen.blit(fog, (-off, y))
    screen.blit(self.vignette, (0, 0))

    if show_title:
      self.draw_title(screen, t)
      screen.blit(self.hint, self.hint.get_rect(center=(W // 2, H - 14)))

  def draw_title(self, screen, t):
    cy = 34
    self.the.draw(screen, (W // 2, cy))
    half = self.the.surface.get_width() // 2
    for side in (-1, 1):
      x0, x1 = W // 2 + side * (half - 4), W // 2 + side * (half + 120)
      pygame.draw.line(screen, (150, 104, 44), (x0, cy), (x1, cy), 2)
      pygame.draw.line(screen, (60, 30, 10), (x0, cy + 2), (x1, cy + 2), 1)
      pts = [(x1, cy - 6), (x1 + 6 * side, cy), (x1, cy + 6), (x1 - 6 * side, cy)]
      pygame.draw.polygon(screen, (230, 170, 70), pts)
      pygame.draw.polygon(screen, (60, 26, 8), pts, 1)

    cycle = t % 7.0
    shine = cycle / 1.3 if cycle < 1.3 else None
    glow = int(120 + 50 * math.sin(t * 1.6))
    self.title.draw(screen, (W // 2, 102), glow_alpha=glow, shine_pos=shine)
    self.greek.draw(screen, (W // 2, 164), glow_alpha=90)

  def _draw_flame(self, screen, x, y, t, ph, f):
    wob = math.sin(t * 9 + ph) * 3 + math.sin(t * 23 + ph * 3) * 1.6
    h = 34 + math.sin(t * 13 + ph) * 5 + f * 6
    halo = self.flame_halo
    screen.blit(halo, (x - 60, y - 30 - 60), special_flags=pygame.BLEND_ADD)
    for scale, col in ((1.0, (200, 56, 12)), (0.74, (255, 140, 34)), (0.46, (255, 228, 150))):
      r = 12 * scale
      hh = h * scale
      by = y - 2
      pts = [(x + math.cos(a) * r, by + math.sin(a) * r * 0.7) for a in (0, 0.6, 1.2, 1.57, 1.9, 2.5, 3.14)]
      pts += [(x - r * 0.85 + wob * 0.3 * scale, by - hh * 0.45),
              (x + wob * scale, by - hh),
              (x + r * 0.85 + wob * 0.3 * scale, by - hh * 0.45)]
      pygame.draw.polygon(screen, col, pts)

  def _draw_eyes(self, screen, t, age, mouse):
    if self.eye_alpha <= 0:
      return
    for e in self.eyes:
      vis = min(1.0, max(0.0, (age - e['fade_in']) / 1.2)) * self.eye_alpha
      if vis <= 0:
        continue
      if t > e['blink_at'] + 0.14:
        e['blink_at'] = t + self.rng.uniform(2.0, 6.0)
      open_k = 0.12 if e['blink_at'] <= t <= e['blink_at'] + 0.14 else 1.0
      s = e['s']
      dx = max(-1.0, min(1.0, (mouse[0] - e['x']) / 300)) * s * 0.45
      dy = max(-1.0, min(1.0, (mouse[1] - e['y']) / 300)) * s * 0.25
      levels = self.eye_glow[s]
      gk = vis * (0.75 + 0.25 * math.sin(t * 2 + e['x'])) * open_k
      g = levels[min(len(levels) - 1, int(gk * len(levels)))]
      for side in (-1, 1):
        ex, ey = e['x'] + side * e['sp'], e['y']
        screen.blit(g, (ex - g.get_width() // 2, ey - g.get_height() // 2), special_flags=pygame.BLEND_ADD)
        w, hgt = s * 2.6, s * 1.5 * open_k
        inner = -side                       
        ox, ix = ex - inner * w / 2, ex + inner * w / 2
        core = shade((255, 96, 36), 0.35 + 0.65 * vis)
        if hgt < 1.5:                       
          pygame.draw.line(screen, core, (ox, ey), (ix, ey + 1))
          continue
        
        pts = [(ox, ey - hgt * 0.3), (ix, ey + hgt * 0.2)]
        for k in range(1, 7):
          u = 1 - 2 * k / 7
          pts.append((ex + inner * u * w / 2, ey + hgt * 0.15 + hgt * 0.45 * math.sqrt(1 - u * u)))
        pygame.draw.polygon(screen, core, pts)
        hot = shade((255, 220, 150), vis)
        pygame.draw.circle(screen, hot, (ex + dx * 0.5, ey + hgt * 0.2), max(1, s * 0.28))
        if s >= 4:                          
          pygame.draw.ellipse(screen, (60, 0, 0), (ex - s * 0.18 + dx, ey - hgt * 0.1 + dy, s * 0.36, hgt * 0.65))


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