"""Small UI kit: buttons, segmented toggles, a text field and floating messages."""
import pygame

from . import art


class Button:
    def __init__(self, rect, label, action, size=24, accent=art.CYAN, icon=None, kind="body"):
        self.rect = pygame.Rect(rect)
        self.label = label          # str or callable returning str
        self.action = action
        self.size = size
        self.accent = accent
        self.icon = icon
        self.kind = kind
        self.hover = False
        self.hot = 0.0
        self.enabled = True

    def text(self):
        return self.label() if callable(self.label) else self.label

    def handle(self, event, audio=None):
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            was = self.hover
            self.hover = self.rect.collidepoint(event.pos)
            if self.hover and not was and audio:
                audio.play("hover")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            if audio:
                audio.play("click")
            self.action()
            return True
        return False

    def update(self, dt):
        target = 1.0 if self.hover and self.enabled else 0.0
        self.hot += (target - self.hot) * min(1.0, dt * 12)

    def draw(self, surface):
        r = self.rect.move(0, -int(self.hot * 2))
        base = (34, 46, 84) if self.enabled else (40, 44, 56)
        col = tuple(int(base[i] + (self.accent[i] * 0.35 - base[i] * 0.2) * self.hot) for i in range(3))
        if self.hot > 0.05:
            art.blit_glow(surface, r.center, int(r.w * 0.6), tuple(int(c * 0.25 * self.hot) for c in self.accent))
        art.panel(surface, r, col, 235, 12, self.accent if self.hover else art.PANEL_EDGE, 2)
        color = art.INK if self.enabled else art.INK_DIM
        x = r.centerx
        if self.icon:
            img = self.icon
            total = img.get_width() + 10 + art.font(self.size, True, self.kind).size(self.text())[0]
            ix = r.centerx - total // 2
            surface.blit(img, img.get_rect(midleft=(ix, r.centery)))
            x = ix + img.get_width() + 10 + art.font(self.size, True, self.kind).size(self.text())[0] // 2
        art.text(surface, self.text(), (x, r.centery), self.size, color, True, self.kind, "center")


class Segmented:
    """A row of options, one selected (language, difficulty, music on/off)."""

    def __init__(self, rect, options, get, set_, size=18, accent=art.GOLD):
        self.rect = pygame.Rect(rect)
        self.options = options      # list of (value, label or callable)
        self.get = get
        self.set = set_
        self.size = size
        self.accent = accent
        self.hover = None

    def _cells(self):
        n = len(self.options)
        w = self.rect.w / n
        return [pygame.Rect(int(self.rect.x + i * w), self.rect.y, int(w), self.rect.h) for i in range(n)]

    def handle(self, event, audio=None):
        if event.type == pygame.MOUSEMOTION:
            self.hover = None
            for i, c in enumerate(self._cells()):
                if c.collidepoint(event.pos):
                    self.hover = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for (value, _), c in zip(self.options, self._cells()):
                if c.collidepoint(event.pos):
                    if audio:
                        audio.play("click")
                    self.set(value)
                    return True
        return False

    def draw(self, surface):
        art.panel(surface, self.rect, (18, 24, 46), 230, self.rect.h // 2, art.PANEL_EDGE, 2)
        current = self.get()
        for i, ((value, label), c) in enumerate(zip(self.options, self._cells())):
            label = label() if callable(label) else label
            if value == current:
                inner = c.inflate(-6, -6)
                pygame.draw.rect(surface, self.accent, inner, border_radius=inner.h // 2)
                art.text(surface, label, c.center, self.size, (24, 20, 10), True, anchor="center", shadow=False)
            else:
                col = art.INK if self.hover == i else art.INK_DIM
                art.text(surface, label, c.center, self.size, col, True, anchor="center", shadow=False)


class TextField:
    """Single line text entry, used for typing chess moves and names."""

    def __init__(self, rect, max_len=12, placeholder="", size=34, kind="mono", allowed=None):
        self.rect = pygame.Rect(rect)
        self.value = ""
        self.max_len = max_len
        self.placeholder = placeholder
        self.size = size
        self.kind = kind
        self.allowed = allowed
        self.active = True
        self.shake = 0.0
        self.flash = 0.0
        self.flash_color = art.GREEN
        self.time = 0.0

    def handle(self, event, audio=None):
        """Returns 'submit' when Enter is pressed, 'changed' after an edit, else None."""
        if not self.active or event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return "submit"
        if event.key == pygame.K_BACKSPACE:
            if event.mod & pygame.KMOD_CTRL:
                self.value = ""
            else:
                self.value = self.value[:-1]
            if audio:
                audio.play("key")
            return "changed"
        ch = event.unicode
        if ch and ch.isprintable() and len(self.value) < self.max_len:
            if self.allowed is None or ch in self.allowed:
                self.value += ch
                if audio:
                    audio.play("key")
                return "changed"
        return None

    def error(self):
        self.shake = 0.4
        self.flash = 0.5
        self.flash_color = art.RED

    def ok(self):
        self.flash = 0.4
        self.flash_color = art.GREEN

    def update(self, dt):
        self.time += dt
        self.shake = max(0.0, self.shake - dt)
        self.flash = max(0.0, self.flash - dt)

    def draw(self, surface, label_color=art.INK):
        import math
        dx = int(math.sin(self.shake * 60) * 10 * self.shake / 0.4) if self.shake else 0
        r = self.rect.move(dx, 0)
        edge = art.CYAN if self.active else art.PANEL_EDGE
        if self.flash:
            k = self.flash / 0.5
            edge = tuple(int(edge[i] + (self.flash_color[i] - edge[i]) * k) for i in range(3))
            art.blit_glow(surface, r.center, r.w // 2, tuple(int(c * 0.3 * k) for c in self.flash_color))
        art.panel(surface, r, (10, 14, 30), 245, 14, edge, 3)
        f = art.font(self.size, True, self.kind)
        if self.value:
            img = f.render(self.value, True, label_color)
        else:
            img = art.font(max(14, self.size // 2), False).render(self.placeholder, True, art.INK_DIM)
        rect = img.get_rect(midleft=(r.x + 18, r.centery))
        surface.blit(img, rect)
        if self.active and int(self.time * 2) % 2 == 0:
            x = rect.right + 3 if self.value else r.x + 16
            pygame.draw.line(surface, art.CYAN, (x, r.y + 14), (x, r.bottom - 14), 3)


class Popups:
    """Floating texts like '+300' that rise and fade."""

    def __init__(self):
        self.items = []

    def add(self, s, pos, color=art.GOLD, size=34, life=1.4):
        self.items.append([s, list(pos), color, size, life, life])

    def update(self, dt):
        for it in self.items:
            it[1][1] -= 40 * dt
            it[4] -= dt
        self.items = [it for it in self.items if it[4] > 0]

    def draw(self, surface):
        for s, pos, color, size, life, total in self.items:
            f = art.font(size, True, "num")
            img = f.render(s, True, color)
            a = int(255 * min(1.0, life / (total * 0.5)))
            img.set_alpha(a)
            sh = f.render(s, True, (0, 0, 0))
            sh.set_alpha(a // 2)
            r = img.get_rect(center=pos)
            surface.blit(sh, r.move(2, 3))
            surface.blit(img, r)


class Particles:
    def __init__(self):
        self.items = []

    def burst(self, pos, color, n=28, speed=220):
        import random
        for _ in range(n):
            ang = random.uniform(0, 6.283)
            sp = random.uniform(speed * 0.3, speed)
            import math
            self.items.append([pos[0], pos[1], math.cos(ang) * sp, math.sin(ang) * sp - 60,
                               random.uniform(0.5, 1.0), color, random.randint(2, 5)])

    def update(self, dt):
        for p in self.items:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 380 * dt
            p[4] -= dt
        self.items = [p for p in self.items if p[4] > 0]

    def draw(self, surface):
        for x, y, _vx, _vy, life, color, size in self.items:
            art.blit_glow(surface, (x, y), size * 3, tuple(int(c * 0.5) for c in color), min(1, life * 2))
            pygame.draw.circle(surface, color, (int(x), int(y)), max(1, int(size * life)))
