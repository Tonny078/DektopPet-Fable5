"""
FableCat — a living desktop pixel-cat.
- Watches your mouse cursor when it moves: eyes, head and ears track it,
  pupils dilate when it gets excited. When the cursor rests, the cat's gaze
  wanders on its own.
- Climbs real windows: walks to a window's side, scrambles up the edge and
  strolls along the title bar. Rides the window if you move it, falls if you
  close it. Skips maximized/fullscreen windows.
- Mood/energy system: playful when rested, lazy when tired, naps to recharge.
- Chases the cursor and pounces on it; sometimes a butterfly visits.
- Toss physics: fling it and it arcs, stretches mid-air, lands with a squash
  and a puff of dust. Legs dangle while you carry it.
- Cat rituals: sits, grooms a paw, yawns before sleeping, stretches on waking.
- Whiskers, inner ears, chest patch, tabby/calico markings per theme.
- Emote bubbles (!, ?, music note), purr vibration, drifting Zzz.
"""

import tkinter as tk
import math, random, time
from collections import deque

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

# ── Constants ──────────────────────────────────────────────────────────────────
TRANSPARENT = "#010101"
LG    = 70
SCALE = 4
W = H = LG * SCALE
CX = CY = 35
FEET = (CY + 14) * SCALE     # screen-px from window top to the cat's paws

def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

COLOR_SCHEMES = {
    "Shadow":   {"FUR": (61,50,67),    "OUT": (42,34,46),    "LGT": (97,82,104),    "SHD": (35,29,39),    "NOSE": (220,128,164), "INN": (112,82,112),  "ACC": (132,113,145), "EYE": (100,209,255), "PAT": "none"},
    "Ginger":   {"FUR": (230,126,34),  "OUT": (168,67,0),    "LGT": (247,169,65),   "SHD": (180,83,22),   "NOSE": (132,63,40),   "INN": (247,166,135), "ACC": (139,77,31),   "EYE": (82,220,182),  "PAT": "tabby"},
    "Grey":     {"FUR": (127,140,141), "OUT": (44,62,80),    "LGT": (184,195,198),  "SHD": (91,105,108),  "NOSE": (235,155,170), "INN": (174,142,154), "ACC": (88,101,106),  "EYE": (120,225,255), "PAT": "tabby"},
    "Snow":     {"FUR": (236,240,241), "OUT": (149,165,166), "LGT": (255,255,255),  "SHD": (204,216,219), "NOSE": (230,150,170), "INN": (245,190,205), "ACC": (178,195,198), "EYE": (80,180,255),  "PAT": "none"},
    "Midnight": {"FUR": (25,28,42),    "OUT": (12,14,22),    "LGT": (63,72,104),    "SHD": (8,10,16),     "NOSE": (190,96,140),  "INN": (80,55,86),    "ACC": (86,100,145),  "EYE": (116,255,206), "PAT": "none"},
    "Fable":    {"FUR": (238,232,218), "OUT": (81,68,59),    "LGT": (255,248,232),  "SHD": (202,192,174), "NOSE": (226,128,151), "INN": (244,176,188), "ACC": (218,112,37),  "EYE": (96,215,150),  "PAT": "calico"}
}

(BK, FUR, OUT, EYE, WHI, LGT, SHD, NOSE, INN, ACC,
 GLOW, HEART, ZZZ, DUST, WHK) = range(15)

HEART_PIX = [(1,0),(3,0),(0,1),(1,1),(2,1),(3,1),(4,1),(1,3),(2,4)]

EMOTES = {
    "!":    [(1,0),(1,1),(1,2),(1,4)],
    "?":    [(0,0),(1,0),(2,0),(2,1),(1,2),(1,4)],
    "note": [(2,0),(3,0),(2,1),(2,2),(1,3),(2,3),(1,4),(2,4)],
}

# Energy gained (+) or spent (-) per second, per state
ENERGY_RATE = {"SLEEP": 0.05, "SIT": 0.03, "GROOM": 0.03, "IDLE": 0.02,
               "WALK": -0.004, "RUN": -0.035, "CHASE": -0.045, "POUNCE": -0.03,
               "FALL": 0.0, "STRETCH": 0.01, "YAWN": 0.02, "CLIMB": -0.03,
               "CIRCLE": 0.0, "ZOOM": -0.06, "PUSH": -0.025, "PEEK": -0.01}

# ── Win32: real windows the cat can climb and walk on ──────────────────────────
try:
    import ctypes
    from ctypes import wintypes
    _user32 = ctypes.windll.user32
    _user32.IsWindow.argtypes = [wintypes.HWND]
    _user32.IsWindowVisible.argtypes = [wintypes.HWND]
    _user32.IsIconic.argtypes = [wintypes.HWND]
    _user32.IsZoomed.argtypes = [wintypes.HWND]
    _user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    _user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
                                     ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                     wintypes.UINT]
    _user32.SetWindowPos.restype = wintypes.BOOL
    _user32.GetForegroundWindow.argtypes = []
    _user32.GetForegroundWindow.restype = wintypes.HWND       # 64-bit safe
    _user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    _user32.GetAncestor.restype = wintypes.HWND
    _user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    _user32.SetCursorPos.restype = wintypes.BOOL
    _user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    _user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    _user32.GetAsyncKeyState.restype = ctypes.c_short

    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [("ACLineStatus",       ctypes.c_ubyte),
                    ("BatteryFlag",        ctypes.c_ubyte),
                    ("BatteryLifePercent", ctypes.c_ubyte),
                    ("SystemStatusFlag",   ctypes.c_ubyte),
                    ("BatteryLifeTime",    wintypes.DWORD),
                    ("BatteryFullLifeTime", wintypes.DWORD)]
    _kernel32 = ctypes.windll.kernel32
    _kernel32.GetSystemPowerStatus.argtypes = [ctypes.POINTER(SYSTEM_POWER_STATUS)]
    _kernel32.GetSystemPowerStatus.restype = wintypes.BOOL

    HWND_TOPMOST = wintypes.HWND(-1)
    GA_ROOT = 2
    # ASYNC so a hung target app can never freeze the animation thread
    SWP_PUSH_FLAGS = 0x1 | 0x4 | 0x10 | 0x4000   # NOSIZE|NOZORDER|NOACTIVATE|ASYNCWINDOWPOS
    SWP_Z_FLAGS    = 0x2 | 0x1 | 0x10            # NOMOVE|NOSIZE|NOACTIVATE
    try:
        _dwm = ctypes.windll.dwmapi
        _dwm.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                               ctypes.c_void_p, wintypes.DWORD]
    except OSError:
        _dwm = None
    _WIN32 = True
except (ImportError, AttributeError, OSError):
    _WIN32 = False

WS_CAPTION = 0x00C00000
EDGE_PAD = 8   # invisible resize border on window sides

def _raw_rect(hwnd):
    """Unpadded (left, top, right, bottom) — required for SetWindowPos moves."""
    if not _WIN32 or not hwnd: return None
    r = wintypes.RECT()
    if not _user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    return (r.left, r.top, r.right, r.bottom)

def _own_hwnd(root):
    """Real top-level HWND of the Tk root (winfo_id is the inner TkChild)."""
    if not _WIN32: return 0
    try:
        return int(_user32.GetAncestor(wintypes.HWND(root.winfo_id()), GA_ROOT) or 0)
    except Exception:
        return 0

def _win_rect(hwnd):
    """(left, top, right) of a window while it is still a valid platform, else None."""
    if not _WIN32 or not hwnd: return None
    u = _user32
    if not u.IsWindow(hwnd) or not u.IsWindowVisible(hwnd) or u.IsIconic(hwnd) or u.IsZoomed(hwnd):
        return None
    r = wintypes.RECT()
    if not u.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    return (r.left + EDGE_PAD, r.top, r.right - EDGE_PAD)

def _work_area_bottom(sh):
    """Top of the (bottom) taskbar — the cat's true ground level."""
    if _WIN32:
        try:
            rc = wintypes.RECT()
            if _user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rc), 0):  # SPI_GETWORKAREA
                return rc.bottom
        except Exception:
            pass
    return sh - 40

def _enum_platforms(sw, sh, limit=6):
    """Visible, captioned, non-maximized windows, topmost in z-order first."""
    if not _WIN32: return []
    plats = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _lp):
        if len(plats) >= limit:
            return False
        try:
            u = _user32
            if not u.IsWindowVisible(hwnd) or u.IsIconic(hwnd) or u.IsZoomed(hwnd):
                return True
            if (u.GetWindowLongW(hwnd, -16) & WS_CAPTION) != WS_CAPTION:
                return True
            if _dwm is not None:   # skip cloaked UWP ghost windows
                cloaked = wintypes.DWORD(0)
                if _dwm.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked),
                                              ctypes.sizeof(cloaked)) == 0 and cloaked.value:
                    return True
            rect = _win_rect(hwnd)
            if rect is None: return True
            l, tp, rt = rect
            if rt - l < 260: return True                          # too narrow to walk on
            if tp < 170 or tp > sh - 160: return True             # no head-room / too low
            if l <= 2 and tp <= 2 and rt >= sw - 2: return True   # borderless fullscreen
            plats.append({"hwnd": int(hwnd) if hwnd else 0, "left": l, "top": tp, "right": rt})
        except Exception:
            pass
        return True
    _user32.EnumWindows(cb, 0)
    return plats


class InteractiveShadowCat:
    def __init__(self):
        self.root = tk.Tk()
        self._setup_window()
        self._init_state()
        self._bind_events()
        self._last_ts = time.perf_counter()
        self._anim()
        self.root.mainloop()

    def _setup_window(self):
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", TRANSPARENT)
        self.root.configure(bg=TRANSPARENT)

        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()

        self.pos_x = self.sw - W - 50
        self.ground_y = _work_area_bottom(self.sh) - FEET   # paws on the taskbar top
        self.pos_y = self.ground_y
        self._last_geo = (int(self.pos_x), int(self.pos_y))
        self.root.geometry(f"{W}x{H}+{int(self.pos_x)}+{int(self.pos_y)}")

        self.canvas = tk.Canvas(self.root, width=W, height=H, bg=TRANSPARENT, highlightthickness=0, bd=0)
        self.canvas.pack()

        if _PIL:
            self._pil_small = Image.new('RGB', (LG, LG), (1, 1, 1))
            self._pil_big   = Image.new('RGB', (W,  H),  (1, 1, 1))
            self._photo     = ImageTk.PhotoImage(self._pil_big)
            self._img_id    = self.canvas.create_image(0, 0, anchor="nw", image=self._photo)

        self.buf = [[BK] * LG for _ in range(LG)]
        self._blank_row = [BK] * LG

        self.root.update_idletasks()
        self._hwnd = _own_hwnd(self.root)

    def _init_state(self):
        self.t = 0.0
        self.state = "IDLE"   # IDLE, WALK, RUN, POUNCE, SLEEP, FALL, SIT, GROOM, STRETCH, YAWN, CHASE
        self.state_t = 0.0
        self.blink_t = 3.0
        self.blinking = False
        self.ear_twitch = 0.0
        self.ear_perk = 0.0
        self.sleepy = False          # menu-forced nap flag
        self.pet_timer = 0.0
        self.particles = []
        self.vx = 0.0
        self.vy = 0.0
        self.is_dragging = False
        self.drag_hist = deque(maxlen=6)

        self.facing = 1
        self.target_x = self.pos_x
        self.speed = 0.0
        self.move_timer = 2.0
        self.pounce_phase = 0.0
        self.pounce_luck = False
        self.chase_target = None     # None | "cursor" | "bf"

        self.energy = 0.7
        self.pupil = 0.5
        self.squash = 0.0
        self.drop = 5.0     # per-pose vertical offset that puts paws on the baseline
        self.zoom_left = 0
        self.hover_t = 0.0
        self.slow_blink = 0.0
        self.slow_blink_cd = 0.0
        self.dust_t = 0.0
        self.emote_cd = 0.0

        self.mx = self.root.winfo_pointerx()
        self.my = self.root.winfo_pointery()
        self.cursor_speed = 0.0
        self.cursor_idle_t = 99.0
        self.look = (0.0, 0.0)
        self.gaze_t = 0.0
        self.gaze_pt = (0.5, 0.1)
        self.head_lean = 0.0
        self.watching_bf = False
        self.butterfly = None

        self.climb_enabled = True
        self.platforms = []          # climbable windows, rescanned periodically
        self.plat_scan_t = 0.0
        self.floor_hwnd = None       # window the cat stands on (None = ground)
        self.floor_prev = None       # its last known (left, top, right)
        self.floor_y = self.ground_y
        self.climb = None            # {"hwnd", "side", "phase"} during CLIMB

        self.mischief_enabled = True
        self.mischief_next = time.monotonic() + 45.0
        self.push = None             # PUSH state data
        self.peek = None             # PEEK state data
        self.peek_next = time.monotonic() + 60.0
        self._z_lowered = False      # True while hiding behind a window
        self.fg_hwnd = 0             # current foreground window
        self.fg_scan_t = 0.0
        self.attn = None             # [x, y, ttl] gaze-attention point
        self.batt_t = 1.0
        self.batt_low = False

        self._set_theme("Shadow")

    def _set_theme(self, name):
        theme = COLOR_SCHEMES[name]
        self.pattern = theme.get("PAT", "none")
        self.palette_rgb = [
            (1, 1, 1), theme["FUR"], theme["OUT"], theme["EYE"],
            (255,255,255), theme["LGT"], theme["SHD"], theme["NOSE"],
            theme["INN"], theme["ACC"], (255,232,120), (255,93,134), (180,180,255),
            _mix(theme["SHD"], (228, 228, 228), 0.55),   # DUST
            _mix(theme["LGT"], (255, 255, 255), 0.5),    # WHK
        ]

    # ── Pixel helpers ──────────────────────────────────────────────────────────
    def _px(self, x, y, col, sz=1):
        ix, iy = int(x), int(y)
        for dy in range(sz):
            for dx in range(sz):
                nx, ny = ix + dx, iy + dy
                if 0 <= nx < LG and 0 <= ny < LG: self.buf[ny][nx] = col

    def _px_masked(self, x, y, col):
        ix, iy = int(x), int(y)
        if 0 <= ix < LG and 0 <= iy < LG and self.buf[iy][ix] == FUR:
            self.buf[iy][ix] = col

    def _ellipse(self, cx, cy, rx, ry, col, outline=None):
        irx2, iry2 = 1.0 / (rx * rx), 1.0 / (ry * ry)
        for dy in range(-int(ry) - 1, int(ry) + 2):
            for dx in range(-int(rx) - 1, int(rx) + 2):
                d = dx * dx * irx2 + dy * dy * iry2
                if d <= 1:
                    self._px(cx + dx, cy + dy, outline if outline and d > 0.78 else col)

    def _ellipse_masked(self, cx, cy, rx, ry, col):
        irx2, iry2 = 1.0 / (rx * rx), 1.0 / (ry * ry)
        for dy in range(-int(ry) - 1, int(ry) + 2):
            for dx in range(-int(rx) - 1, int(rx) + 2):
                if dx * dx * irx2 + dy * dy * iry2 <= 1:
                    self._px_masked(cx + dx, cy + dy, col)

    def _line(self, x0, y0, x1, y1, col):
        steps = max(abs(int(x1 - x0)), abs(int(y1 - y0)), 1)
        for i in range(steps + 1):
            t = i / steps
            self._px(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), col)

    # ── Particles / emotes ─────────────────────────────────────────────────────
    def _spawn(self, x, y, kind, vx=0.0, vy=0.0, ttl=1.0):
        self.particles.append({"x": x, "y": y, "vx": vx, "vy": vy,
                               "ttl": ttl, "ttl0": ttl, "kind": kind})

    def _emote(self, kind):
        if self.emote_cd > 0: return
        self.emote_cd = 1.2
        self._spawn(CX + 5 * self.facing - 2, CY - 24, "emote_" + kind, vy=-4, ttl=1.4)

    def _dust_puff(self, n=1, spread=6):
        for _ in range(n):
            self._spawn(CX + random.uniform(-spread, spread), CY + 12 + random.uniform(-1, 1),
                        "dust", vx=random.uniform(-14, 14), vy=random.uniform(-22, -6),
                        ttl=random.uniform(0.35, 0.6))

    def _burst(self, x, y, n=8):
        for i in range(n):
            a = i / n * math.tau
            self._spawn(x, y, "sparkle", vx=math.cos(a) * 26, vy=math.sin(a) * 26 - 10, ttl=0.7)

    # ── State machine ──────────────────────────────────────────────────────────
    def _change_state(self, new):
        self.state = new
        self.state_t = 0.0
        if new == "IDLE":
            self.move_timer = random.uniform(1.5, 4.0)
        elif new == "POUNCE":
            self.pounce_phase = 0.0
            self.pounce_luck = random.random() < 0.45
        elif new == "SIT":
            self.move_timer = random.uniform(2.0, 5.0)
        elif new == "GROOM":
            self.move_timer = random.uniform(2.0, 3.5)
        elif new == "CHASE":
            self._emote("!")
        elif new == "ZOOM":
            self.zoom_left = 3
            self.target_x = self._far_target()
            self._emote("!")

    def _move_window(self):
        ix, iy = int(self.pos_x), int(self.pos_y)
        if (ix, iy) != self._last_geo:
            self._last_geo = (ix, iy)
            self.root.geometry(f"+{ix}+{iy}")

    def _clamp_walls(self):
        if self.pos_x < 0: self.pos_x = 0
        if self.pos_x > self.sw - W: self.pos_x = self.sw - W

    def _update_ai(self, dt):
        if self.is_dragging: return
        if self.floor_hwnd is None and self.pos_y > self.ground_y:
            self.pos_y = self.ground_y

        # Airborne (falling / tossed) — climbing/peeking pin themselves in place
        if self.state not in ("CLIMB", "PEEK") and (self.pos_y < self.floor_y - 0.5 or self.vy < -0.01):
            self._physics_air()
            self._move_window()
            return

        # Skidding along the ground after a toss
        if abs(self.vx) > 0.4:
            self.pos_x += self.vx
            self.vx *= 0.86
            self._clamp_walls()
            self.dust_t -= dt
            if self.dust_t <= 0:
                self._dust_puff(1, spread=4)
                self.dust_t = 0.1
            self._move_window()
            return
        self.vx = 0.0

        handler = getattr(self, "_st_" + self.state.lower(), None)
        if handler: handler(dt)
        self._move_window()

    def _physics_air(self):
        if self.state != "FALL":
            self._change_state("FALL")
        self.vy += 0.8
        self.pos_y += self.vy
        self.pos_x += self.vx
        self.vx *= 0.995
        if self.pos_x <= 0 or self.pos_x >= self.sw - W:
            self._clamp_walls()
            self.vx = -self.vx * 0.6
        if self.pos_y < -H // 2:
            self.pos_y = -H // 2
            self.vy = abs(self.vy) * 0.3
        # Catch a window top on the way down
        if self.vy > 0:
            cxs = self.pos_x + CX * SCALE
            feet = self.pos_y + FEET
            prev_feet = feet - self.vy
            best = None
            for p in self.platforms:
                if (p["left"] + 10 <= cxs <= p["right"] - 10 and
                        prev_feet <= p["top"] + 4 and feet >= p["top"]):
                    if best is None or p["top"] < best["top"]:
                        best = p
            if best is not None:
                self.pos_y = best["top"] - FEET
                self.floor_hwnd = best["hwnd"]
                self.floor_prev = (best["left"], best["top"], best["right"])
                self._land()
                return
        if self.pos_y >= self.ground_y:
            self.pos_y = self.ground_y
            self.floor_hwnd = None
            self._land()

    def _land(self):
        self.squash = min(1.0, abs(self.vy) / 14.0)
        if self.squash > 0.3:
            self._dust_puff(5, spread=8)
            if self.squash > 0.6: self._emote("!")
        self.vy = 0.0
        self._change_state("IDLE")

    def _st_fall(self, dt):
        self._change_state("IDLE")

    def _st_idle(self, dt):
        self.speed = 0
        if self.pet_timer > 0: return
        if self.energy < 0.06 and not self.sleepy:
            self._change_state("YAWN")
            return
        # Glance toward a moving cursor
        if self.cursor_idle_t < 1.0:
            cat_cx = self.pos_x + CX * SCALE
            if abs(self.mx - cat_cx) > 40:
                self.facing = 1 if self.mx > cat_cx else -1
        self.move_timer -= dt
        if self.move_timer <= 0:
            self._pick_next_action()

    def _pick_next_action(self):
        on_win = self.floor_hwnd is not None
        if self.energy < 0.2:                  # weary: keep it slow and restful
            opts = [("WALK", 0.7), ("SIT", 1.8), ("IDLE", 1.0)]
        else:
            opts = [("WALK", 1.0),
                    ("RUN", 0.25 + 0.9 * self.energy),
                    ("POUNCE", 0.15 + 0.35 * self.energy),
                    ("SIT", 0.5 + 1.3 * (1.0 - self.energy)),
                    ("IDLE", 0.6)]
            if self.energy > 0.8:              # playful: itching for action
                opts.append(("POUNCE", 0.4))
                opts.append(("ZOOM", 0.5))
            if self.cursor_idle_t < 1.5 and self.energy > 0.4:
                opts.append(("CHASE_CUR", 1.8 * self.energy))
            if self.butterfly is not None and self.energy > 0.25:
                opts.append(("CHASE_BF", 2.4 * max(0.3, self.energy)))
            if not on_win and self.climb_enabled and self.platforms and self.energy > 0.35:
                opts.append(("CLIMB", 0.9 * self.energy))
            if (_WIN32 and self.mischief_enabled and self.energy > 0.3 and
                    time.monotonic() >= self.mischief_next and (on_win or self.platforms)):
                opts.append(("PUSH", 0.8 * max(0.0, self.energy - 0.3)))
            if (_WIN32 and not on_win and self.platforms and self.energy > 0.4 and
                    time.monotonic() >= self.peek_next):
                opts.append(("PEEK", 0.6))
        if on_win:
            opts.append(("HOP_OFF", 0.5))

        m = self._daypart_mult()
        if m.get("NAP") and self.state != "SLEEP":
            opts.append(("NAP", m["NAP"] * (1.5 - self.energy)))
        opts = [(n, w * m.get(n, 1.0)) for n, w in opts]
        if self.batt_low:                      # conserve energy in solidarity
            opts = [(n, w * (2.0 if n in ("SIT", "IDLE", "NAP") else
                             0.0 if n in ("ZOOM", "PUSH") else 0.5)) for n, w in opts]
        opts = [(n, w) for n, w in opts if w > 0]
        if not opts:
            opts = [("IDLE", 1.0)]

        total = sum(w for _, w in opts)
        r = random.uniform(0, total)
        name = opts[-1][0]
        for n, w in opts:
            r -= w
            if r <= 0:
                name = n
                break

        if name in ("WALK", "RUN"):
            if on_win and self.floor_prev:
                l, _, rt = self.floor_prev
                lo, hi = int(l + 30 - CX * SCALE), int(rt - 30 - CX * SCALE)
                self.target_x = random.randint(lo, hi) if hi > lo else self.pos_x
            else:
                self.target_x = random.randint(50, self.sw - W - 50)
            self._change_state(name)
        elif name == "CLIMB":
            self._start_climb()
        elif name == "HOP_OFF":
            l, _, rt = self.floor_prev
            self.target_x = (l - 300) if random.random() < 0.5 else (rt + 300)
            self._change_state("WALK")   # walks off the edge and falls
        elif name == "POUNCE":
            self.facing = random.choice([-1, 1])
            self._change_state("POUNCE")
        elif name == "CHASE_CUR":
            self.chase_target = "cursor"
            self._change_state("CHASE")
        elif name == "CHASE_BF":
            self.chase_target = "bf"
            self._change_state("CHASE")
        elif name == "SIT":
            self._change_state("SIT")
        elif name == "ZOOM":
            self._change_state("ZOOM")
        elif name == "PUSH":
            self.mischief_next = time.monotonic() + random.uniform(60, 120)
            self._start_push()
        elif name == "PEEK":
            self.peek_next = time.monotonic() + random.uniform(80, 130)
            self._start_peek()
        elif name == "NAP":
            self._change_state("YAWN")
        else:
            self._change_state("IDLE")

    def _move_toward(self, speed):
        if abs(self.target_x - self.pos_x) < 8:
            self._change_state("IDLE")
            return
        self.speed = speed
        self.facing = 1 if self.target_x > self.pos_x else -1
        self.pos_x += self.facing * speed
        if self.pos_x <= 0 or self.pos_x >= self.sw - W:
            self._clamp_walls()
            self._change_state("IDLE")

    def _st_walk(self, dt):
        self._move_toward(1.6)

    def _st_run(self, dt):
        self._move_toward(4.5)
        self.dust_t -= dt
        if self.dust_t <= 0 and self.state == "RUN":
            self._spawn(CX - self.facing * 8, CY + 12, "dust",
                        vx=-self.facing * 10, vy=-14, ttl=0.4)
            self.dust_t = 0.15

    def _chase_pos(self):
        if self.chase_target == "bf":
            bf = self.butterfly
            return (bf["x"], bf["y"]) if bf else None
        return (self.mx, self.my)

    def _st_chase(self, dt):
        tgt = self._chase_pos()
        gave_up = (tgt is None or self.state_t > 6.0 or
                   (self.chase_target == "cursor" and self.cursor_idle_t > 2.5))
        if gave_up:
            self.chase_target = None
            self._emote("?")
            self._change_state("IDLE")
            return
        cat_cx = self.pos_x + CX * SCALE
        dx = tgt[0] - cat_cx
        if abs(dx) > 30:
            self.facing = 1 if dx > 0 else -1
        self.pos_x += self.facing * 5.5
        self._clamp_walls()
        self.dust_t -= dt
        if self.dust_t <= 0:
            self._spawn(CX - self.facing * 8, CY + 12, "dust",
                        vx=-self.facing * 10, vy=-14, ttl=0.4)
            self.dust_t = 0.15
        if abs(dx) < 90:
            self._change_state("POUNCE")

    def _st_pounce(self, dt):
        self.pounce_phase = self.state_t
        if self.state_t < 0.9:
            self.speed = 0   # butt-wiggle wind-up
        elif self.state_t < 1.4:
            self.pos_x += self.facing * 8.5
            self._clamp_walls()
            bf = self.butterfly
            if self.chase_target == "bf" and bf is not None:
                nx = self.pos_x + (CX + 12 * self.facing) * SCALE
                ny = self.pos_y + CY * SCALE
                if math.hypot(bf["x"] - nx, bf["y"] - ny) < 55 and self.pounce_luck:
                    self.butterfly = None
                    self._burst(CX + 10 * self.facing, CY - 4)
                    self._emote("note")
                    self.energy = max(0.0, self.energy - 0.1)
                    self.chase_target = None
                    self._change_state("SIT")   # satisfied
        else:
            if (self.chase_target == "cursor" and
                    0 <= self.mx - self.pos_x <= W and 0 <= self.my - self.pos_y <= H):
                self._burst(CX + 10 * self.facing, CY + 6)
                self._emote("note")
                self._bat_cursor()
            self.chase_target = None
            self._change_state("IDLE")

    def _st_sit(self, dt):
        self.move_timer -= dt
        if self.move_timer <= 0:
            if random.random() < 0.4:
                self._change_state("GROOM")
            else:
                self._change_state("IDLE")

    def _st_groom(self, dt):
        self.move_timer -= dt
        if self.move_timer <= 0:
            self._change_state("SIT")

    def _st_stretch(self, dt):
        if self.state_t > 1.6:
            if self.energy > 0.9 and random.random() < 0.5:
                self._change_state("ZOOM")     # post-nap zoomies
            else:
                self._change_state("IDLE")

    def _st_yawn(self, dt):
        if self.state_t > 1.2:
            self._change_state("CIRCLE")       # circle the spot before lying down

    def _st_circle(self, dt):
        if int(self.state_t / 0.4) != int(max(0.0, self.state_t - dt) / 0.4):
            self.facing *= -1                  # turn, turn, turn...
        if self.state_t > 1.6:
            self._change_state("SLEEP")

    def _st_zoom(self, dt):
        if abs(self.target_x - self.pos_x) < 12:
            self.zoom_left -= 1
            if self.zoom_left <= 0:
                self._change_state("POUNCE")
                return
            self.target_x = self._far_target()
        self.facing = 1 if self.target_x > self.pos_x else -1
        self.pos_x += self.facing * 7.0
        if self.pos_x <= 0 or self.pos_x >= self.sw - W:
            self._clamp_walls()
            self.target_x = self._far_target()
        self.dust_t -= dt
        if self.dust_t <= 0:
            self._spawn(CX - self.facing * 8, CY + 12, "dust",
                        vx=-self.facing * 12, vy=-16, ttl=0.4)
            self.dust_t = 0.08

    def _far_target(self):
        for _ in range(6):
            tx = random.randint(50, self.sw - W - 50)
            if abs(tx - self.pos_x) > 400:
                return tx
        return random.randint(50, self.sw - W - 50)

    def _st_sleep(self, dt):
        if random.random() < 0.02:
            self._spawn(CX + 10, CY - 10, "zzz", vy=-9, ttl=2.0)
        if not self.sleepy and self.energy > 0.96:
            self._change_state("STRETCH")

    def _start_climb(self):
        cands = []
        for p in self.platforms:
            for side, edge in ((-1, p["left"]), (1, p["right"])):
                pin = edge - CX * SCALE      # cat centre pinned on the edge
                if 0 <= pin <= self.sw - W:
                    cands.append((abs(pin - self.pos_x), p, side))
        if not cands:
            self._change_state("IDLE")
            return
        cands.sort(key=lambda c: c[0])
        fg = [c for c in cands if c[1]["hwnd"] == self.fg_hwnd]
        _, p, side = (random.choice(fg) if fg and random.random() < 0.7
                      else random.choice(cands[:3]))   # supervise the active window
        self.climb = {"hwnd": p["hwnd"], "side": side, "phase": "approach"}
        self._change_state("CLIMB")

    def _st_climb(self, dt):
        c = self.climb
        rect = _win_rect(c["hwnd"]) if (c and self.climb_enabled) else None
        if rect is None or self.state_t > 20:
            self.climb = None
            self._change_state("IDLE")   # gravity takes over if we're mid-wall
            return
        l, tp, rt = rect
        edge = l if c["side"] == -1 else rt
        pin = max(0, min(self.sw - W, edge - CX * SCALE))
        if c["phase"] == "approach":
            if abs(pin - self.pos_x) > 6:
                self.facing = 1 if pin > self.pos_x else -1
                self.pos_x += self.facing * 3.0
                self._clamp_walls()
            else:
                self.pos_x = pin
                self.facing = 1 if c["side"] == -1 else -1   # face the window
                c["phase"] = "up"
                self._emote("!")
        elif c["phase"] == "up":
            self.pos_x = pin                 # cling to the edge, even if it moves
            self.pos_y -= 3.5
            if random.random() < 0.06:
                self._dust_puff(1, spread=3)
            if self.pos_y <= tp - FEET:
                self.pos_y = tp - FEET
                c["phase"] = "over"
        else:                                # clamber over the corner onto the top
            inward = 1 if c["side"] == -1 else -1
            self.pos_x += inward * 4.0
            self.pos_y = tp - FEET
            cxs = self.pos_x + CX * SCALE
            if l + 30 <= cxs <= rt - 30:
                self.floor_hwnd = c["hwnd"]
                self.floor_prev = (l, tp, rt)
                self.climb = None
                self._change_state("IDLE")

    # ── Window mischief: PUSH ──────────────────────────────────────────────────
    def _start_push(self):
        if self.floor_hwnd is not None and self.floor_prev:
            l, tp, rt = self.floor_prev
            cxs = self.pos_x + CX * SCALE
            side = -1 if (cxs - l) <= (rt - cxs) else 1
            self.push = {"hwnd": self.floor_hwnd, "mode": "top", "dir": side,
                         "goal": random.uniform(30, 80), "moved": 0.0,
                         "phase": "approach", "stall": 0, "last": None}
            self._change_state("PUSH")
            return
        cands = []
        for p in self.platforms:
            for side, edge in ((-1, p["left"]), (1, p["right"])):
                pin = edge - CX * SCALE
                if 0 <= pin <= self.sw - W and abs(pin - self.pos_x) < 600:
                    cands.append((abs(pin - self.pos_x), p, side))
        if not cands:
            self._change_state("IDLE")
            return
        cands.sort(key=lambda c: c[0])
        fg = [c for c in cands if c[1]["hwnd"] == self.fg_hwnd]
        _, p, side = (random.choice(fg) if fg and random.random() < 0.7
                      else random.choice(cands[:2]))
        # standing at the left edge (side -1) she shoves the window right, and vice versa
        self.push = {"hwnd": p["hwnd"], "mode": "side", "dir": -side,
                     "goal": random.uniform(30, 80), "moved": 0.0,
                     "phase": "approach", "stall": 0, "last": None}
        self._change_state("PUSH")

    def _st_push(self, dt):
        p = self.push
        rect = _win_rect(p["hwnd"]) if (p and self.mischief_enabled) else None
        if rect is None or self.state_t > 8.0:
            self.push = None
            self._emote("?")
            self._change_state("IDLE")
            return
        l, tp, rt = rect
        if p["mode"] == "top":
            corner = (l + 30) if p["dir"] == -1 else (rt - 30)
            brace = corner - CX * SCALE
        else:
            edge = l if p["dir"] == 1 else rt
            brace = max(0, min(self.sw - W, edge - CX * SCALE))

        if p["phase"] == "approach":
            if abs(brace - self.pos_x) > 6:
                self.facing = 1 if brace > self.pos_x else -1
                self.pos_x += self.facing * 3.0
                self._clamp_walls()
            else:
                self.pos_x = brace
                self.facing = p["dir"]
                p["phase"] = "shove"
                self._emote("!")
            return

        # shove: nudge the real window a couple of px per frame, verify it moves
        r = _raw_rect(p["hwnd"])
        if r is None:
            self.push = None
            self._emote("?")
            self._change_state("IDLE")
            return
        if p["last"] is not None:
            actual = abs(r[0] - p["last"][0]) + abs(r[1] - p["last"][1])
            if actual < 1:
                p["stall"] += 1
                if p["stall"] >= 5:            # elevated/hung window: immovable
                    self.push = None
                    self._emote("?")
                    self._change_state("IDLE")
                    return
            else:
                p["stall"] = 0
                p["moved"] += actual
        p["last"] = r
        dx = p["dir"] * 2
        dy = 1 if p["mode"] == "top" else 0
        nx, ny = r[0] + dx, r[1] + dy
        half_w = (r[2] - r[0]) // 2
        if (nx + half_w < 0 or nx + half_w > self.sw or
                ny > _work_area_bottom(self.sh) - 200):
            p["moved"] = p["goal"]             # far enough — stop before real damage
        else:
            _user32.SetWindowPos(p["hwnd"], None, int(nx), int(ny), 0, 0, SWP_PUSH_FLAGS)
        if p["mode"] == "side":
            self.pos_x = brace                 # shuffle along, keeping her paws on it
        if p["moved"] >= p["goal"]:
            self.push = None
            self._dust_puff(3)
            self._emote("note")
            self._change_state("SIT")          # smug

    # ── Peek-a-boo: PEEK ───────────────────────────────────────────────────────
    def _start_peek(self):
        cands = [p for p in self.platforms if p["right"] - p["left"] >= 300]
        if not (_WIN32 and self._hwnd and cands):
            self._change_state("IDLE")
            return
        fg = [p for p in cands if p["hwnd"] == self.fg_hwnd]
        p = random.choice(fg) if fg and random.random() < 0.7 else random.choice(cands)
        self.peek = {"hwnd": p["hwnd"], "phase": "approach",
                     "bobs": random.randint(1, 3), "bob_t": 0.0}
        self._change_state("PEEK")

    def _st_peek(self, dt):
        pk = self.peek
        rect = _win_rect(pk["hwnd"]) if pk else None
        if rect is None or self.state_t > 12.0:
            self.peek = None
            self._restore_topmost()
            self._change_state("IDLE")         # mid-air -> natural FALL
            return
        l, tp, rt = rect
        lo, hi = l + 60 - CX * SCALE, rt - 60 - CX * SCALE
        if pk["phase"] == "approach":
            target = max(lo, min(hi, self.pos_x))
            if abs(target - self.pos_x) > 6:
                self.facing = 1 if target > self.pos_x else -1
                self.pos_x += self.facing * 3.0
                self._clamp_walls()
            else:
                pk["phase"] = "hide"
            return
        self.pos_x = max(lo, min(hi, self.pos_x))  # stay covered if the window moves
        if pk["phase"] == "hide":
            self._lower_behind(pk["hwnd"])
            self.floor_hwnd = None
            self.pos_y = tp + 20.0                 # fully hidden behind it
            pk["phase"] = "rise"
        elif pk["phase"] == "rise":
            top_y = tp - 44.0                      # just ears + eyes over the bar
            if self.pos_y > top_y:
                self.pos_y = max(top_y, self.pos_y - 140.0 * dt)
            else:
                pk["bob_t"] += dt
                self.pos_y = top_y + max(0.0, math.sin(pk["bob_t"] * 3.0)) * 30.0
                if pk["bob_t"] * 3.0 >= pk["bobs"] * math.tau:
                    pk["phase"] = "emerge"
        else:  # emerge: pop out on top of the title bar
            self._restore_topmost()
            self.pos_y = tp - FEET
            self.floor_hwnd = pk["hwnd"]
            self.floor_prev = (l, tp, rt)
            self.peek = None
            self._dust_puff(3)
            self._emote("!")
            self._change_state("IDLE")

    def _lower_behind(self, hwnd):
        if _WIN32 and self._hwnd:
            _user32.SetWindowPos(self._hwnd, hwnd, 0, 0, 0, 0, SWP_Z_FLAGS)
            self._z_lowered = True

    def _restore_topmost(self):
        if _WIN32 and self._hwnd and self._z_lowered:
            _user32.SetWindowPos(self._hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_Z_FLAGS)
            self._z_lowered = False

    # ── Real-world senses ──────────────────────────────────────────────────────
    def _bat_cursor(self):
        """One discrete swat of the real pointer — never while the user clicks."""
        if not (_WIN32 and self.mischief_enabled):
            return
        if _user32.GetAsyncKeyState(0x01) & 0x8000:
            return
        vx0 = _user32.GetSystemMetrics(76)
        vy0 = _user32.GetSystemMetrics(77)
        vx1 = vx0 + _user32.GetSystemMetrics(78) - 2
        vy1 = vy0 + _user32.GetSystemMetrics(79) - 2
        nx = max(vx0 + 2, min(vx1, self.mx + self.facing * random.randint(30, 60)))
        ny = max(vy0 + 2, min(vy1, self.my + random.randint(-10, 10)))
        _user32.SetCursorPos(int(nx), int(ny))

    def _poll_battery(self):
        if not _WIN32:
            return
        sps = SYSTEM_POWER_STATUS()
        if not _kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
            return
        if sps.BatteryFlag in (128, 255) or sps.BatteryLifePercent == 255:
            self.batt_low = False              # desktop / unknown: no-op
            return
        charging = sps.ACLineStatus == 1
        low = (not charging) and sps.BatteryLifePercent <= 20
        if charging and self.batt_low:
            self._emote("note")                # relief: power is back
        self.batt_low = low

    def _daypart_mult(self):
        h = time.localtime().tm_hour
        if h >= 23 or h < 7:                   # night: wind down, seek the bed ritual
            return {"RUN": 0.3, "POUNCE": 0.3, "ZOOM": 0.0, "CHASE_CUR": 0.4,
                    "CHASE_BF": 0.4, "SIT": 2.0, "IDLE": 1.5, "NAP": 1.0, "PUSH": 0.2}
        if h < 9:                              # morning zoomies hour
            return {"ZOOM": 2.5, "RUN": 1.6, "POUNCE": 1.4}
        return {}

    # ── Cursor & butterfly ─────────────────────────────────────────────────────
    def _update_cursor(self, dt):
        mx, my = self.root.winfo_pointerx(), self.root.winfo_pointery()
        sp = math.hypot(mx - self.mx, my - self.my) / max(dt, 1e-3)
        self.mx, self.my = mx, my
        self.cursor_speed = self.cursor_speed * 0.8 + sp * 0.2
        if sp > 60:
            self.cursor_idle_t = 0.0
            if self.cursor_speed > 900:
                self.ear_perk = 1.0
        else:
            self.cursor_idle_t += dt
        self.ear_perk = max(0.0, self.ear_perk - dt * 1.5)

        # Pick what to look at: the butterfly (if closer) or the cursor
        f = self.facing
        head_sx = self.pos_x + (CX + 7 * f) * SCALE
        head_sy = self.pos_y + (CY - 8) * SCALE
        tx, ty = mx, my
        self.watching_bf = False
        bf = self.butterfly
        if bf is not None:
            if math.hypot(bf["x"] - head_sx, bf["y"] - head_sy) < math.hypot(mx - head_sx, my - head_sy):
                tx, ty = bf["x"], bf["y"]
                self.watching_bf = True

        # Only stare when something is actually interesting; otherwise the
        # gaze wanders on its own with occasional lazy glances.
        interested = (self.state in ("CHASE", "POUNCE") or self.watching_bf or
                      self.cursor_idle_t < 2.5)
        if self.state == "CLIMB":
            want = (0.3 * f, -0.9)          # eyes up the wall
            lean = 0.0
        elif self.state == "PEEK":
            want = (0.2 * f, 0.9)           # peering down over the title bar
            lean = 0.0
        elif self.attn is not None:         # something on the desktop caught her eye
            dxl = (self.attn[0] - head_sx) / SCALE
            dyl = (self.attn[1] - head_sy) / SCALE
            want = (max(-1.2, min(1.2, dxl * 0.12)), max(-1.0, min(1.2, dyl * 0.1)))
            lean = max(-1.0, min(1.0, dxl * 0.02))
            self.attn[2] -= dt
            if self.attn[2] <= 0:
                self.attn = None
        elif interested:
            dxl = (tx - head_sx) / SCALE
            dyl = (ty - head_sy) / SCALE
            want = (max(-1.2, min(1.2, dxl * 0.12)), max(-1.0, min(1.2, dyl * 0.1)))
            lean = max(-1.0, min(1.0, dxl * 0.02))
        else:
            self.gaze_t -= dt
            if self.gaze_t <= 0:
                self.gaze_t = random.uniform(1.5, 4.5)
                self.gaze_pt = (0.6 * f + random.uniform(-0.6, 0.6),
                                random.uniform(-0.3, 0.5))
            want = self.gaze_pt
            lean = 0.0
        k = min(1.0, dt * 6)
        self.look = (self.look[0] + (want[0] - self.look[0]) * k,
                     self.look[1] + (want[1] - self.look[1]) * k)
        self.head_lean += (lean - self.head_lean) * k

    def _ground_screen_y(self):
        return self.ground_y + (CY + 14) * SCALE

    def _pick_waypoint(self, bf):
        cat_cx = self.pos_x + CX * SCALE
        if self.state in ("SIT", "GROOM", "SLEEP") and random.random() < 0.5:
            # the cat is calm — drift in close, maybe land on her
            bf["wx"] = min(max(cat_cx + random.uniform(-60, 60), 20), self.sw - 20)
            bf["wy"] = self.pos_y + (CY - 20) * SCALE + random.uniform(-30, 30)
        else:
            bf["wx"] = min(max(cat_cx + random.uniform(-220, 220), 20), self.sw - 20)
            bf["wy"] = self._ground_screen_y() - random.uniform(60, 230)
        bf["wp_t"] = random.uniform(1.5, 3.5)

    def _bf_perch(self):
        """Screen position on top of the cat's head."""
        top_local = 30 if self.state == "SLEEP" else 24
        return (self.pos_x + (CX + 2 * self.facing) * SCALE,
                self.pos_y + top_local * SCALE)

    def _update_butterfly(self, dt):
        bf = self.butterfly
        if bf is None:
            if self.state not in ("SLEEP", "YAWN", "CIRCLE") and random.random() < 0.0009:
                side = random.choice([-1, 1])
                x = min(max(self.pos_x + CX * SCALE + side * random.uniform(200, 320), 20), self.sw - 20)
                bf = {"x": x, "y": self._ground_screen_y() - random.uniform(100, 240),
                      "wx": x, "wy": 0, "phase": random.uniform(0, 9),
                      "wp_t": 0.0, "ttl": random.uniform(20, 35)}
                self._pick_waypoint(bf)
                self.butterfly = bf
                self._emote("!")
            return
        # Perched on the cat's head
        if bf.get("landed_t", 0) > 0:
            bf["phase"] += dt * 0.25            # slow, gentle wing folds
            bf["ttl"] -= dt
            bf["landed_t"] -= dt
            calm = (self.state in ("SIT", "GROOM", "SLEEP") and not self.is_dragging)
            bf["x"], bf["y"] = self._bf_perch()
            if bf["landed_t"] <= 0 or not calm:
                bf["landed_t"] = 0
                bf["y"] -= 14                   # flutter off upward
                bf["wp_t"] = 0
            return

        bf["phase"] += dt
        bf["ttl"] -= dt
        bf["wp_t"] -= dt
        if bf["wp_t"] <= 0:
            self._pick_waypoint(bf)

        # Land on a calm cat's head
        if (self.state in ("SIT", "GROOM", "SLEEP") and self.chase_target is None and
                bf["ttl"] > 4 and not bf.get("has_landed")):
            px_, py_ = self._bf_perch()
            if math.hypot(bf["x"] - px_, bf["y"] - py_) < 60 and random.random() < 0.03:
                bf["landed_t"] = random.uniform(2.0, 5.0)
                bf["has_landed"] = True
                self._spawn(CX + 2 * self.facing, CY - 22, "heart", vy=-8, ttl=1.2)
                return
        dx, dy = bf["wx"] - bf["x"], bf["wy"] - bf["y"]
        d = math.hypot(dx, dy) or 1.0
        spd = 75 * dt
        bf["x"] += dx / d * spd
        bf["y"] += dy / d * spd + math.sin(bf["phase"] * 9) * 1.3
        # Flee upward when the cat lunges close
        if self.state == "POUNCE":
            nx = self.pos_x + (CX + 12 * self.facing) * SCALE
            ny = self.pos_y + CY * SCALE
            if math.hypot(bf["x"] - nx, bf["y"] - ny) < 90:
                bf["y"] -= 150 * dt
        if bf["ttl"] <= 0 or bf["y"] < -60:
            self.butterfly = None

    # ── Drawing ────────────────────────────────────────────────────────────────
    def _draw_tail(self, cx, cy, f, mode):
        if mode == "curl":       # asleep, wrapped along the body
            tx, ty = cx - (4 * f), cy + 7
            for i in range(12):
                ang = i * 0.4
                ox = math.cos(ang) * (i * 0.8) * f
                oy = math.sin(ang) * (i * 0.3)
                self._px(tx + ox, ty + oy, OUT, 3)
                self._px(tx + ox + 0.5, ty + oy + 0.5, FUR, 2)
        elif mode == "wrap":     # sitting, tail around the front paws
            ty = cy + 8
            for i in range(13):
                tx = cx + (-6 + i) * f
                flick = math.sin(self.t * 3) * 0.8 if i > 9 else 0
                yy = ty + math.sin(self.t * 2 + i) * 0.3 + flick
                sz = 3 if i < 10 else 2
                self._px(tx, yy, OUT, sz)
                self._px(tx + 0.5, yy + 0.5, FUR, max(1, sz - 1))
        elif mode == "hook":     # happy/curious upright question-mark tail
            bx, by = cx - 8 * f, cy + 4
            sway = math.sin(self.t * 2.5) * 1.2
            for i in range(12):
                u = i / 11
                tx = bx - f * 3 * u + f * max(0.0, u - 0.7) * 14 + sway * u
                ty = by - 13 * u + max(0.0, u - 0.8) * 6
                sz = 3 if i < 8 else 2
                self._px(tx, ty, OUT, sz)
                self._px(tx + 0.5, ty + 0.5, FUR, max(1, sz - 1))
        elif mode == "hang":     # dragged: tail dangles below
            bx, by = cx - 7 * f, cy + 6
            for i in range(12):
                u = i / 11
                tx = bx + math.sin(self.t * 3 + u * 2.5) * (1 + 2 * u)
                ty = by + 12 * u
                sz = 3 if i < 7 else 2
                self._px(tx, ty, OUT, sz)
                self._px(tx + 0.5, ty + 0.5, FUR, max(1, sz - 1))
        else:                    # "sine" — the default flowing tail
            tx, ty = cx - (8 * f), cy + 4
            speed_mod = 6.0 if self.state in ("RUN", "CHASE", "ZOOM") else 3.0
            if self.state == "POUNCE" and self.pounce_phase < 0.9:
                speed_mod = 25.0
            speed_mod *= 0.6 + 0.8 * self.energy
            for i in range(15):
                curl = math.sin(self.t * speed_mod + i * 0.5) * 0.8
                tx -= 1.1 * f
                ty += curl - 0.1
                size = 4 if i < 7 else 3 if i < 12 else 2
                self._px(tx, ty, OUT, size)
                self._px(tx + 0.5, ty + 0.5, FUR, max(1, size - 1))

    def _draw_cat_body(self, cx, cy):
        f = self.facing
        st = self.state
        mode = ("sleep" if st == "SLEEP" else
                "sit" if st in ("SIT", "GROOM") else
                "stretch" if (st == "STRETCH" or
                              (st == "PUSH" and self.push and self.push["phase"] == "shove")) else
                "climb" if (st == "CLIMB" and self.climb and self.climb["phase"] == "up") else
                "drag" if self.is_dragging else "normal")

        purr = math.sin(self.t * 60) * 0.5 if self.pet_timer > 0 else 0
        breath_rate = 4.0 if st in ("RUN", "CHASE", "ZOOM") else 1.2 if mode == "sleep" else 2.0
        breath = math.sin(self.t * breath_rate) * 0.45

        if mode == "sleep":
            curr_y = cy + purr
            self._draw_tail(cx, curr_y, f, "curl")
            body_y = curr_y + 2 + breath
            self._ellipse(cx, body_y, 9, 5, FUR, OUT)
            return (cx + 6 * f, curr_y - 2, body_y)

        if mode == "sit":
            curr_y = cy + purr
            body_y = curr_y + 3 + breath * 0.6
            self._draw_tail(cx, body_y, f, "wrap")
            self._ellipse(cx - 3 * f, body_y + 3, 5, 4, FUR, OUT)      # haunch
            self._ellipse(cx, body_y, 5.5, 7, FUR, OUT)                # upright torso
            for leg_off in (2.5, 5):                                   # straight front legs
                x = cx + leg_off * f
                for yy in range(int(body_y + 2), int(body_y + 9)):
                    self._px(x, yy, OUT, 2)
                    self._px(x + 0.5, yy, FUR, 1)
            self._ellipse_masked(cx + 2 * f, body_y - 1, 1.8, 2.6, LGT)   # chest patch
            return (cx + 1.5 * f + self.head_lean, body_y - 9, body_y)

        if mode == "stretch":
            curr_y = cy + purr
            self._draw_tail(cx - 2 * f, curr_y - 2, f, "hook")
            self._ellipse(cx - 5 * f, curr_y - 1, 5, 5, FUR, OUT)      # raised rear
            self._ellipse(cx - 1 * f, curr_y + 3, 5, 4, FUR, OUT)      # arched middle
            self._ellipse(cx + 4 * f, curr_y + 6, 5, 3.5, FUR, OUT)    # low chest
            for off in (-7, -4):                                       # rear legs
                x = cx + off * f
                for yy in range(int(curr_y + 3), int(curr_y + 12)):
                    self._px(x, yy, OUT, 2)
                    self._px(x + 0.5, yy, FUR, 1)
            self._line(cx + 5 * f, curr_y + 7, cx + 11 * f, curr_y + 12, OUT)   # front legs
            self._line(cx + 5 * f, curr_y + 6, cx + 11 * f, curr_y + 11, FUR)   # stretched out
            self._px(cx + 11 * f, curr_y + 11, OUT, 2)
            return (cx + 8 * f, curr_y + 2, curr_y + 3)

        if mode == "climb":
            curr_y = cy + purr
            self._draw_tail(cx + 5 * f, curr_y + 2, f, "hang")   # hangs off the rump
            self._ellipse(cx, curr_y + 1, 4.5, 8, FUR, OUT)            # vertical body
            scr = math.sin(self.t * 10)                                # scrambling paws
            for i, ly_ in enumerate((-5, -1, 3, 7)):
                py_ = curr_y + ly_ + (scr if i % 2 == 0 else -scr) * 1.2
                self._px(cx + 3 * f, py_, OUT, 3)
                self._px(cx + 3 * f + 0.5, py_ + 0.5, FUR, 2)
            self._ellipse_masked(cx + 1 * f, curr_y - 2, 1.6, 3, LGT)  # chest patch
            return (cx + 1 * f + self.head_lean, curr_y - 9, curr_y + 1)

        # "normal" and "drag"
        run_bob = abs(math.sin(self.t * 12.0)) * 2.5 if st in ("RUN", "CHASE", "ZOOM") else 0
        if st == "FALL": run_bob = -5
        curr_y = cy - run_bob + purr
        sq = self.squash

        if mode == "drag":
            tail_mode = "hang"
        elif self.pet_timer > 0 or (st == "IDLE" and self.cursor_idle_t < 1.0 and self.energy > 0.55):
            tail_mode = "hook"
        else:
            tail_mode = "sine"
        self._draw_tail(cx, curr_y, f, tail_mode)

        body_y = curr_y + 3 + breath
        bw, bh = 9.0, 6.0
        if st == "POUNCE" and self.pounce_phase >= 0.9: bw = 12
        if st == "FALL" and abs(self.vy) > 5:
            bw *= 0.85
            bh *= 1.25
        bw *= 1 + 0.5 * sq
        bh *= 1 - 0.35 * sq
        self._ellipse(cx, body_y, bw, bh, FUR, OUT)
        self._ellipse_masked(cx + 5 * f, body_y + 1, 2, 2, LGT)        # chest patch

        walk_cycle = math.sin(self.t * (18.0 if st in ("RUN", "CHASE", "ZOOM") else 8.0))
        for i, lx in enumerate([-5, -1, 4, 8]):
            if mode == "drag":
                lift = 3 + math.sin(self.t * 4 + i * 0.9) * 1.5        # dangling legs
            elif st == "FALL":
                lift = 4
            elif st == "IDLE" or (st == "POUNCE" and self.pounce_phase < 0.9):
                lift = 0
            else:
                lift = (walk_cycle if i % 2 == 0 else -walk_cycle) * (3.5 if st in ("RUN", "CHASE", "ZOOM") else 1.5)
            px_ = cx + lx * f
            py_ = curr_y + 7 + lift
            self._px(px_, py_, OUT, 3)
            self._px(px_ + 0.5, py_ + 0.5, FUR, 2)

        wiggle = math.sin(self.t * 20) * 1.5 if (st == "POUNCE" and self.pounce_phase < 0.9) else 0
        hx = cx + 7 * f + wiggle + self.head_lean
        hy = curr_y - 4 + sq * 2
        return (hx, hy, body_y)

    def _draw_cat_head(self, hx, hy):
        f = self.facing
        st = self.state
        sleeping = st == "SLEEP"
        yawning = st == "YAWN"
        grooming = st == "GROOM"
        pet_sq = 1 if self.pet_timer > 0 else 0

        if grooming:
            hx += f * 1
            hy += 1

        # Ears — with inner colour, twitch and perk
        perk = 1 if self.ear_perk > 0.4 else 0
        for side in (-1, 1):
            ex = hx + (side * 5)
            tw = self.ear_twitch if side == 1 else self.ear_twitch * 0.3
            for i in range(5 + perk):
                self._px(ex - 2 + i, hy - 4 - i + tw, OUT, 2)
                self._px(ex - 1 + i, hy - 3 - i + tw, FUR, 2)
            for i in (1, 2):
                self._px(ex - 1 + i, hy - 2 - i + tw, INN, 1)

        self._ellipse(hx, hy + pet_sq, 8, 6, FUR, OUT)
        self._ellipse_masked(hx - 1 + f, hy + 2.5, 2.5, 1.8, LGT)      # muzzle patch

        # Whiskers
        if not sleeping:
            for side in (-1, 1):
                bx = hx + side * 6
                for k, tip_dy in enumerate((-1, 1, 3)):
                    self._line(bx, hy + 1 + k, bx + side * 3, hy + tip_dy, WHK)

        # Eyes — follow the look target, pupils dilate with excitement.
        # Pupil and gleam snap to whole pixels and stay inside the socket.
        pxi = max(-1, min(1, int(round(self.look[0]))))
        pyi = max(-1, min(1, int(round(self.look[1]))))
        sb = math.sin(math.pi * (1.0 - self.slow_blink / 1.2)) if self.slow_blink > 0 else 0.0
        for side in (-1, 1):
            ex, ey = hx + (side * 4) - 1, hy - 1
            if self.blinking or sleeping or yawning or sb > 0.6:
                self._line(ex - 1, ey + 1, ex + 2, ey + 1, OUT)
            elif self.pet_timer > 0 or grooming:                       # happy squint
                self._line(ex - 1, ey, ex + 1, ey - 1, OUT)
                self._line(ex - 1, ey, ex + 1, ey + 1, OUT)
            else:
                self._px(ex, ey, OUT, 3)                               # dark socket
                if self.pupil > 0.62:                                  # wide, playful pupil
                    bx0 = ex + (1 if pxi > 0 else 0)
                    by0 = ey + (1 if pyi > 0 else 0)
                    self._px(bx0, by0, EYE, 2)
                    self._px(bx0, by0, WHI, 1)
                else:                                                  # calm pupil
                    cxp, cyp = ex + 1 + pxi, ey + 1 + pyi
                    self._px(cxp, cyp, EYE, 1)
                    gy = cyp - 1 if cyp - 1 >= ey else cyp + 1
                    self._px(cxp, gy, WHI, 1)
                if self.energy < 0.25 or sb > 0.25:                    # heavy, drowsy lids
                    self._line(ex, ey, ex + 2, ey, FUR)
                    self._line(ex, ey - 1, ex + 2, ey - 1, OUT)

        self._px(hx - 1, hy + 2, NOSE, 2)

        if yawning:
            mo = 1.0 + 2.2 * math.sin(math.pi * min(1.0, self.state_t / 1.2))
            self._ellipse(hx - 0.5, hy + 4.5, 1.6, mo, SHD, OUT)

        if grooming:                                                   # licking a raised paw
            ph = self.state_t * 6
            pawx = hx + f * 4 + math.sin(ph) * 1.5
            pawy = hy + 4 + math.cos(ph) * 1.2
            self._px(pawx, pawy, OUT, 3)
            self._px(pawx + 0.5, pawy + 0.5, FUR, 2)
            if math.sin(ph) > 0.55:
                self._px(hx + f * 2, hy + 4, NOSE, 1)                  # tongue

    def _draw_markings(self, cx, body_y, hx, hy):
        if self.pattern == "none": return
        f = self.facing
        if self.pattern == "tabby":
            for off in (-5, -2, 1, 4):
                for k in range(4):
                    self._px_masked(cx + off, body_y - 7 + k, ACC)
            for off in (-2, 0, 2):
                for k in range(3):
                    self._px_masked(hx + off, hy - 6 + k, ACC)
        else:  # calico
            self._ellipse_masked(cx - 3 * f, body_y - 2, 3, 2.5, ACC)
            self._ellipse_masked(hx + 3 * f, hy - 2, 3, 2.5, ACC)
            self._ellipse_masked(cx + 4 * f, body_y + 3, 2.5, 2, SHD)

    def _draw_butterfly(self):
        bf = self.butterfly
        if bf is None: return
        bx = (bf["x"] - self.pos_x) / SCALE
        by = (bf["y"] - self.pos_y) / SCALE
        if not (-2 <= bx <= LG + 1 and -2 <= by <= LG + 1): return
        self._px(bx, by, OUT, 1)
        self._px(bx, by + 1, OUT, 1)
        if math.sin(bf["phase"] * 16) > 0:                             # wings open
            self._px(bx - 1, by, ACC, 1)
            self._px(bx + 1, by, ACC, 1)
            self._px(bx - 2, by - 1, ACC, 1)
            self._px(bx + 2, by - 1, ACC, 1)
            self._px(bx - 2, by - 2, WHI, 1)
            self._px(bx + 2, by - 2, WHI, 1)
        else:                                                          # wings closed
            self._px(bx - 1, by, ACC, 1)
            self._px(bx + 1, by, ACC, 1)

    def _draw_particles(self):
        for idx, p in enumerate(self.particles):
            k, x, y = p["kind"], p["x"], p["y"]
            life = p["ttl"] / p["ttl0"]
            if k == "heart":
                for dx, dy in HEART_PIX:
                    self._px(x + dx, y + dy, HEART)
            elif k == "zzz":
                xx = x + math.sin(self.t * 2 + idx) * 4
                self._px(xx, y, ZZZ, 2)
                self._px(xx + 2, y - 2, ZZZ, 1)
            elif k == "dust":
                self._px(x, y, DUST, 2 if life > 0.5 else 1)
            elif k == "sparkle":
                self._px(x, y, GLOW)
                if life > 0.55:
                    self._px(x + 1, y, GLOW)
                    self._px(x - 1, y, GLOW)
                    self._px(x, y + 1, GLOW)
                    self._px(x, y - 1, GLOW)
            elif k.startswith("emote_"):
                glyph = EMOTES[k[6:]]
                yy = y + math.sin(self.t * 3) * 0.6
                for dx, dy in glyph:
                    self._px(x + dx + 0.5, yy + dy + 0.5, OUT)
                for dx, dy in glyph:
                    self._px(x + dx, yy + dy, WHI)
            else:
                self._px(x, y, GLOW)

    def _render(self):
        blank = self._blank_row
        for row in self.buf:
            row[:] = blank

        self._draw_butterfly()

        # self.drop settles each pose's paws onto the FEET baseline (local y 49)
        bob = math.sin(self.t * 2) * (0.2 if self.state == "SLEEP" else 0.5)
        hx, hy, body_y = self._draw_cat_body(CX, CY + bob + self.drop)
        self._draw_cat_head(hx, hy)
        self._draw_markings(CX, body_y, hx, hy)
        self._draw_particles()
        self._flush()

    def _flush(self):
        if _PIL:
            data = [self.palette_rgb[v] for row in self.buf for v in row]
            self._pil_small.putdata(data)
            self._photo.paste(self._pil_small.resize((W, H), Image.NEAREST))

    # ── Main loop ──────────────────────────────────────────────────────────────
    def _anim(self):
        now = time.perf_counter()
        dt = min(now - self._last_ts, 0.1)
        self._last_ts = now
        self.t += dt
        self.state_t += dt

        # Rescan climbable windows periodically
        self.plat_scan_t -= dt
        if self.plat_scan_t <= 0:
            self.plat_scan_t = 0.75
            self.platforms = _enum_platforms(self.sw, self.sh) if self.climb_enabled else []

        # Supervisor: notice when the user switches to another app
        self.fg_scan_t -= dt
        if self.fg_scan_t <= 0 and _WIN32:
            self.fg_scan_t = 0.5
            h = int(_user32.GetForegroundWindow() or 0)
            if h and h != self._hwnd and h != self.fg_hwnd:
                self.fg_hwnd = h
                p = next((q for q in self.platforms if q["hwnd"] == h), None)
                if p and self.state in ("IDLE", "SIT", "WALK", "GROOM"):
                    self._emote("?")
                    self.attn = [(p["left"] + p["right"]) / 2.0, p["top"] + 60.0, 2.0]

        # Battery empathy
        self.batt_t -= dt
        if self.batt_t <= 0:
            self.batt_t = 30.0
            self._poll_battery()
        if self.batt_low and random.random() < 0.0008:
            self._emote("!")

        # Failsafe: never stay hidden behind a window outside PEEK
        if self._z_lowered and self.state != "PEEK":
            self._restore_topmost()

        # Track the window we stand on: ride it, fall if it vanishes or we step off
        if self.floor_hwnd is not None and not self.is_dragging:
            rect = _win_rect(self.floor_hwnd)
            if rect is None:
                self.floor_hwnd = None
            else:
                l, tp, rt = rect
                if self.floor_prev:
                    self.pos_x += l - self.floor_prev[0]
                self.floor_prev = rect
                if self.state != "FALL":
                    self.pos_y = tp - FEET
                cxs = self.pos_x + CX * SCALE
                if cxs < l + 6 or cxs > rt - 6:
                    self.floor_hwnd = None
        self.floor_y = (self.ground_y if self.floor_hwnd is None
                        else self.floor_prev[1] - FEET)

        self._update_cursor(dt)
        self._update_ai(dt)
        self._update_butterfly(dt)

        self.energy = min(1.0, max(0.0, self.energy + ENERGY_RATE.get(self.state, 0.0) * dt))

        pupil_target = 0.3 + 0.5 * self.energy
        if self.state in ("CHASE", "POUNCE", "CLIMB", "ZOOM") or self.watching_bf or self.cursor_speed > 900:
            pupil_target = 1.0
        self.pupil += (pupil_target - self.pupil) * min(1.0, dt * 5)

        self.squash *= 0.82
        target_drop = {"SLEEP": 7.0, "SIT": 3.0, "GROOM": 3.0, "STRETCH": 2.0}.get(self.state, 5.0)
        self.drop += (target_drop - self.drop) * min(1.0, dt * 8)

        # Slow blink: cursor resting on the cat = feline "I trust you"
        over = (0 <= self.mx - self.pos_x <= W and 0 <= self.my - self.pos_y <= H)
        if over and not self.is_dragging and self.pet_timer <= 0:
            self.hover_t += dt
        else:
            self.hover_t = 0.0
        self.slow_blink = max(0.0, self.slow_blink - dt)
        self.slow_blink_cd = max(0.0, self.slow_blink_cd - dt)
        if (self.hover_t > 2.0 and self.slow_blink_cd <= 0 and
                self.state not in ("SLEEP", "YAWN", "CIRCLE", "FALL")):
            self.slow_blink = 1.2
            self.slow_blink_cd = 8.0 + random.uniform(0, 4)
            if random.random() < 0.5:
                self._spawn(CX + 6 * self.facing, CY - 14, "heart", vy=-8, ttl=1.2)

        self.pet_timer = max(0.0, self.pet_timer - dt)
        self.emote_cd = max(0.0, self.emote_cd - dt)
        self.ear_twitch = (self.ear_twitch * 0.9) + (random.uniform(-0.5, 0.5) if random.random() < 0.1 else 0)

        alive = []
        for p in self.particles:
            p["ttl"] -= dt
            if p["ttl"] <= 0: continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if p["kind"] == "dust":
                p["vy"] += 40 * dt
                p["vx"] *= 0.98
            alive.append(p)
        self.particles = alive

        self.blink_t -= dt
        if self.blink_t <= 0:
            self.blinking = not self.blinking
            open_span = random.uniform(0.7, 2.5) if self.energy < 0.25 else random.uniform(1, 5)
            self.blink_t = 0.15 if self.blinking else open_span

        self._render()
        self.root.after(30, self._anim)

    # ── Interaction ────────────────────────────────────────────────────────────
    def _show_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0, bg="#2a222e", fg="#ffffff")
        color_menu = tk.Menu(menu, tearoff=0)
        for name in COLOR_SCHEMES.keys():
            color_menu.add_command(label=name, command=lambda n=name: self._set_theme(n))
        menu.add_cascade(label="Change Fur", menu=color_menu)
        menu.add_command(label="Toggle Sleep", command=self._toggle_sleepy)
        menu.add_command(label=f"Climbing: {'ON' if self.climb_enabled else 'OFF'}",
                         command=self._toggle_climb)
        menu.add_command(label=f"Mischief: {'ON' if self.mischief_enabled else 'OFF'}",
                         command=self._toggle_mischief)
        menu.add_separator()
        menu.add_command(label="Exit", command=self.root.destroy)
        menu.tk_popup(event.x_root, event.y_root)

    def _toggle_climb(self):
        self.climb_enabled = not self.climb_enabled
        if not self.climb_enabled and self.state == "CLIMB":
            self.climb = None
            self._change_state("IDLE")

    def _toggle_mischief(self):
        self.mischief_enabled = not self.mischief_enabled
        if not self.mischief_enabled and self.state == "PUSH":
            self.push = None
            self._change_state("IDLE")

    def _toggle_sleepy(self):
        self.sleepy = not self.sleepy
        if self.sleepy:
            if self.state not in ("SLEEP", "YAWN", "CIRCLE"):
                self._change_state("YAWN")
        else:
            if self.state in ("SLEEP", "YAWN", "CIRCLE"):
                self._change_state("STRETCH")

    def _pet(self, _e=None):
        if self.state in ("SLEEP", "YAWN", "CIRCLE"):
            self.sleepy = False
            self.energy = max(self.energy, 0.35)
            self._change_state("STRETCH")
        self.pet_timer = 1.5
        self._spawn(CX, CY - 10, "heart", vy=-10, ttl=1.5)
        self._emote("note")

    def _on_drag(self, e):
        self.is_dragging = True
        self.floor_hwnd = None
        if self.state in ("CLIMB", "PUSH", "PEEK"):
            self.climb = self.push = self.peek = None
            self._restore_topmost()
            self._change_state("IDLE")
        self.pos_x = self.root.winfo_x() + e.x - W // 2
        self.pos_y = self.root.winfo_y() + e.y - H // 2
        self.drag_hist.append((time.perf_counter(), self.pos_x, self.pos_y))
        self._move_window()
        self.target_x = self.pos_x
        self.vx = self.vy = 0.0

    def _on_release(self, e):
        if self.is_dragging and len(self.drag_hist) >= 2:
            t0, x0, y0 = self.drag_hist[0]
            t1, x1, y1 = self.drag_hist[-1]
            span = max(t1 - t0, 1e-3)
            self.vx = max(-60.0, min(60.0, (x1 - x0) / span * 0.045))
            self.vy = max(-50.0, min(50.0, (y1 - y0) / span * 0.045))
        self.is_dragging = False
        self.drag_hist.clear()

    def _bind_events(self):
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-1>", self._pet)
        self.canvas.bind("<Button-3>", self._show_menu)


if __name__ == "__main__":
    InteractiveShadowCat()
