import math
import os
import unicodedata
import pygame
import constants as C

FONT_DIR = 'assets/fonts'
WHITE = (255, 255, 255)


def _plain(s):
  return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower()


def find_font_path():
  override = getattr(C, 'FONT_FILE', None)
  if override and os.path.exists(override):
    return override
  try:
    files = sorted(f for f in os.listdir(FONT_DIR) if f.lower().endswith(('.ttf', '.otf')))
  except FileNotFoundError:
    return None
  for key in ('ithornet', 'atari'):
    for f in files:
      if key in _plain(f):
        return os.path.join(FONT_DIR, f)
  return os.path.join(FONT_DIR, files[0]) if files else None


FONT_PATH = None
_font_cache = {}
_fallback_cache = {}
_notdef_cache = {}
FALLBACK_FONTS = 'georgia,palatinolinotype,bookantiqua,timesnewroman,dejavuserif,liberationserif,freeserif,dejavusans'


def game_font(size):
  global FONT_PATH
  if FONT_PATH is None:
    FONT_PATH = find_font_path() or ''
  if size not in _font_cache:
    try:
      _font_cache[size] = pygame.font.Font(FONT_PATH or None, size)
    except (OSError, pygame.error):
      _font_cache[size] = pygame.font.Font(None, size)
  return _font_cache[size]


def fallback_font(size):
  if size not in _fallback_cache:
    _fallback_cache[size] = pygame.font.SysFont(FALLBACK_FONTS, size, bold=True)
  return _fallback_cache[size]


def strip_marks(s):
  return ''.join(unicodedata.normalize('NFKD', c)[0] for c in s)


def supports(font, text):
  key = id(font)
  if key not in _notdef_cache:
    probe = font.render('', False, WHITE)
    _notdef_cache[key] = (probe.get_size(), pygame.image.tobytes(probe, 'RGBA'))
  nd_size, nd_bytes = _notdef_cache[key]
  for ch in set(text) - {' '}:
    m = font.metrics(ch)
    if not m or m[0] is None:
      return False
    img = font.render(ch, False, WHITE)
    if img.get_size() == nd_size and pygame.image.tobytes(img, 'RGBA') == nd_bytes:
      return False
  return True


def font_for(text, size):
  f = game_font(size)
  return f if supports(f, strip_marks(text)) else fallback_font(size)


def render_mask(font, text):
  if supports(font, text):
    return font.render(text, True, WHITE)
  base = strip_marks(text)
  img = font.render(base, True, WHITE)
  marked = [i for i, c in enumerate(text) if '̄' in unicodedata.normalize('NFD', c)]
  if not marked:
    return img
  head = max(4, font.get_height() // 6)
  out = pygame.Surface((img.get_width(), img.get_height() + head), pygame.SRCALPHA)
  out.blit(img, (0, head))
  bar_h = max(2, font.get_height() // 16)
  for i in marked:
    x0 = font.size(base[:i])[0]
    minx, maxx, _, maxy, _ = font.metrics(base[i])[0]
    glyph_top = head + font.get_ascent() - maxy
    inset = (maxx - minx) * 0.12
    rect = pygame.Rect(x0 + minx + inset, max(0, glyph_top - bar_h * 2 - 1), (maxx - minx) - inset * 2, bar_h)
    pygame.draw.rect(out, WHITE, rect)
  return out


def vgradient(size, stops):
  w, h = size
  surf = pygame.Surface((w, h), pygame.SRCALPHA)
  n = len(stops) - 1
  for y in range(h):
    t = y / max(1, h - 1) * n
    i = min(int(t), n - 1)
    f = t - i
    a, b = stops[i], stops[i + 1]
    col = [int(a[k] + (b[k] - a[k]) * f) for k in range(3)]
    pygame.draw.line(surf, (*col, 255), (0, y), (w, y))
  return surf


def tint(mask, colour):
  s = mask.copy()
  s.fill((*colour, 255), special_flags=pygame.BLEND_RGBA_MULT)
  return s


def blur(surface, factor=6):
  w, h = surface.get_size()
  small = pygame.transform.smoothscale(surface, (max(1, w // factor), max(1, h // factor)))
  return pygame.transform.smoothscale(small, (w, h))


GOLD = [(255, 244, 196), (247, 196, 92), (196, 120, 34), (110, 52, 12)]
BLOOD = [(255, 150, 120), (200, 40, 26), (120, 12, 8), (60, 4, 4)]


class CarvedText():
  def __init__(self, font, text, stops=GOLD, depth=5, outline=2, glow=(255, 110, 20), spacing=0):
    if spacing:
      parts = [render_mask(font, ch) for ch in text]
      w = sum(p.get_width() for p in parts) + spacing * (len(parts) - 1)
      h = max(p.get_height() for p in parts)
      mask = pygame.Surface((w, h), pygame.SRCALPHA)
      x = 0
      for p in parts:
        mask.blit(p, (x, h - p.get_height()))
        x += p.get_width() + spacing
    else:
      mask = render_mask(font, text)

    pad = outline + depth + 14
    w, h = mask.get_width() + pad * 2, mask.get_height() + pad * 2
    self.surface = pygame.Surface((w, h), pygame.SRCALPHA)

    dark = tint(mask, (18, 8, 4))
    for ox in range(-outline, outline + 1):  
      for oy in range(-outline, outline + 1):
        self.surface.blit(dark, (pad + ox, pad + oy))
    edge = tint(mask, (70, 32, 10))
    for d in range(1, depth + 1):  
      self.surface.blit(edge if d < depth else dark, (pad, pad + d))
    self.surface.blit(tint(mask, (255, 250, 225)), (pad, pad - 1)) 
    fill = mask.copy()
    fill.blit(vgradient(mask.get_size(), stops), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    self.surface.blit(fill, (pad, pad))

    self.glow = None
    if glow:
      g = pygame.Surface((w, h))
      g.blit(tint(mask, glow), (pad, pad))
      g = blur(blur(g, 5), 3)
      g.blit(g, (0, 0), special_flags=pygame.BLEND_ADD)  
      self.glow = []
      for k in range(1, 9):
        lvl = g.copy()
        v = int(255 * k / 8)
        lvl.fill((v, v, v), special_flags=pygame.BLEND_MULT)
        self.glow.append(lvl)

    self.mask_rgb = pygame.Surface((w, h))
    m = mask.copy()
    m.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
    self.mask_rgb.blit(m, (pad, pad))
    self._shine = None
    self.rect = self.surface.get_rect()

  def draw(self, surface, center, glow_alpha=140, shine_pos=None):
    self.rect.center = center
    if self.glow:
      i = max(0, min(7, int(glow_alpha / 255 * 8) - 1))
      surface.blit(self.glow[i], self.rect, special_flags=pygame.BLEND_ADD)
    surface.blit(self.surface, self.rect)
    if shine_pos is not None:
      self._draw_shine(surface, shine_pos)

  def _draw_shine(self, surface, t):
    w, h = self.surface.get_size()
    if self._shine is None:
      band = pygame.Surface((140 + h, h))
      for i in range(110):
        k = 1 - abs(i - 55) / 55
        col = (int(170 * k), int(140 * k), int(90 * k))
        pygame.draw.line(band, col, (i, h), (i + h * 0.6, 0), 2)
      self._shine = (band, pygame.Surface((w, h)))
    band, tmp = self._shine
    tmp.fill((0, 0, 0))
    tmp.blit(band, (int(-band.get_width() + (w + band.get_width()) * t), 0))
    tmp.blit(self.mask_rgb, (0, 0), special_flags=pygame.BLEND_MULT)
    surface.blit(tmp, self.rect, special_flags=pygame.BLEND_ADD)


def fit_font(text, max_width, start, minimum=20):
  size = start
  while size > minimum:
    f = font_for(text, size)
    if render_mask(f, text).get_width() <= max_width:
      return f
    size -= 4
  return font_for(text, minimum)


class MenuButton():
  def __init__(self, font, label, action, center):
    self.action = action
    self.label = label
    self.normal = CarvedText(font, label, stops=[(206, 190, 160), (150, 128, 100), (90, 72, 56)], depth=3, glow=None)
    self.hover = CarvedText(font, label, depth=3, glow=(255, 120, 30))
    self.center = center
    self.rect = self.normal.surface.get_rect(center=center).inflate(40, -16)

  def draw(self, surface, selected, t):
    cx, cy = self.center
    if selected:
      pulse = 0.5 + 0.5 * math.sin(t * 5)
      self.hover.draw(surface, (cx, cy), glow_alpha=int(110 + 90 * pulse))
      half = self.hover.surface.get_width() // 2 - 10
      off = 6 * math.sin(t * 4)
      for side in (-1, 1):
        x = cx + side * (half + 14 + off)
        pts = [(x, cy - 9), (x + 7 * side, cy), (x, cy + 9), (x - 7 * side, cy)]
        pygame.draw.polygon(surface, (255, 190, 80), pts)
        pygame.draw.polygon(surface, (90, 30, 6), pts, 2)
    else:
      self.normal.draw(surface, (cx, cy))


class Menu():
  def __init__(self, items, center_x, top_y, spacing, size=30, tick_sound=None):
    self.buttons = [MenuButton(font_for(label, size), label, action, (center_x, top_y + i * spacing))
                    for i, (label, action) in enumerate(items)]
    self.selected = 0
    self.tick = tick_sound
    self._last_mouse = None

  def _select(self, i):
    if i != self.selected:
      self.selected = i
      if self.tick:
        self.tick.play()

  def handle(self, events, mouse_pos):
    if mouse_pos != self._last_mouse:
      self._last_mouse = mouse_pos
      for i, b in enumerate(self.buttons):
        if b.rect.collidepoint(mouse_pos):
          self._select(i)
    n = len(self.buttons)
    for e in events:
      if e.type == pygame.KEYDOWN:
        if e.key in (pygame.K_w, pygame.K_UP):
          self._select((self.selected - 1) % n)
        elif e.key in (pygame.K_s, pygame.K_DOWN):
          self._select((self.selected + 1) % n)
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
          return self.buttons[self.selected].action
      elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
        for b in self.buttons:
          if b.rect.collidepoint(e.pos):
            return b.action
    return None

  def draw(self, surface, t):
    for i, b in enumerate(self.buttons):
      b.draw(surface, i == self.selected, t)

