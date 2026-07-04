# 🐾 DesktopPet #FableCat #python

![Python](https://img.shields.io/badge/python-3.8+-blue) ![Platform](https://img.shields.io/badge/platform-Windows-informational) ![GUI](https://img.shields.io/badge/gui-tkinter-lightgrey)

*A tiny, living pixel-cat who has quietly claimed your entire desktop as her territory.*

FableCat is a borderless, always-on-top desktop companion written in pure Python and Tkinter. No app window, no taskbar clutter — just a hand-drawn pixel cat who sits on top of everything else, watches what you're doing, and develops strong opinions about your open windows.

<img width="847" height="495" alt="image" src="https://github.com/user-attachments/assets/ca626245-2a76-486b-b70d-e6f0a5a7647d" />

<img width="249" height="223" alt="image" src="https://github.com/user-attachments/assets/f63d1a5e-3e18-45ff-b915-0da6289eca6d" /> <img width="174" height="183" alt="image" src="https://github.com/user-attachments/assets/db5701c4-744b-4382-ad91-fbe3b2416a3e" /> <img width="299" height="260" alt="image" src="https://github.com/user-attachments/assets/b21de5e5-462e-4ccf-a9d0-7d9d0fc7ebdb" />


## 🐾 What Can FableCat Do?

### 👀 She notices you
- Her eyes, head, and ears track your mouse cursor as it moves around the screen.
- Her pupils dilate when she's excited — mid-chase, mid-pounce, or when the cursor whips around fast.
- Leave the cursor still for a while and her gaze wanders off on its own, glancing around like she's got somewhere better to be.
- Hover the cursor over her for a couple of seconds and she gives you a slow, trusting blink — sometimes followed by a little heart.

### 🪟 She lives *on* your windows, not just next to them
- Real, open windows are climbable terrain — she scrambles up the edge and struts along the title bar.
- Drag a window she's standing on and she rides along with it.
- Close it out from under her and she tumbles off — no window, no floor.
- Maximized and fullscreen windows are automatically off-limits.
- Switch to a different app and she'll glance over, curious, if it's somewhere she can climb.

### 🐈 Moods, energy, and daily rituals
- A running energy meter decides whether she's playful, lazy, or overdue for a nap.
- Full sleep ritual: yawns, circles the spot a couple of times, curls up, and sleeps it off — then wakes with a stretch (sometimes straight into a zoomie).
- Idle behaviors: sitting, grooming a paw, ear twitches, tail flicks.
- A rough day/night rhythm — a burst of zoomies in the early morning, calmer and sleep-seeking late at night.

### 🦋 A visitor drops by
- A butterfly flutters through every so often, and she can't resist chasing and pouncing on it.
- Catch her calm — sitting, grooming, or asleep — at the right moment, and it may land right on her head.

### 🤸 Physics, tossing, and play
- Pick her up and fling her: she arcs through the air, stretches mid-flight, and lands with a squash and a puff of dust.
- Carry her around and her legs dangle.
- Toss her along the ground and she skids to a stop, kicking up dust behind her.

### 😼 A bit of mischief *(toggleable)*
- Every now and then she'll brace herself against a real window and shove it across the screen.
- She plays peekaboo — ducking behind a window, bobbing up a few times, then popping up over the top.
- Mid-pounce on your cursor, she might land one small, deliberate swat on the real mouse pointer — never while you're actually clicking.

### 💬 She talks back
- Emote bubbles for surprise (!), confusion (?), and contentment (a music note).
- A little purring wobble and drifting "Zzz"s while she sleeps.
- Hearts float up whenever you pet her.

### 🔋 She's aware of the real world
- On a laptop, she notices when the battery runs low and settles down to conserve energy right alongside you — and gives a relieved little chirp when you plug back in.

### 🎨 Six coats to choose from
- Right-click for a menu to change her fur on the fly — see **Customization** below for all six.

## 🖱️ Controls

| Action | Effect |
|---|---|
| **Left-click** | Pet her — she perks up and hearts appear |
| **Left-click + drag** | Pick her up and carry her around |
| **Release while dragging** | Toss her — she'll fly, tumble, and land |
| **Right-click** | Open her menu: change fur, toggle sleep/climbing/mischief, exit |

## 🚀 Getting Started

**Requirements**
- Windows 10/11 — FableCat leans on the Win32 API for window-climbing, mischief, peekaboo, and battery awareness, and on Windows' transparent-window support to render without a background box.
- Python 3.8+
- `tkinter` (bundled with the standard Windows Python installer)
- *Optional:* [Pillow](https://pypi.org/project/Pillow/) for smoother image scaling — she still runs fine without it.

She's a single self-contained script, so there's nothing else to set up.

**Run her**
```bash
pip install pillow   # optional, but recommended
python fablecat.py
```

She'll appear at the bottom-right of your screen and start living her life — no install wizard, no window chrome. To close her, right-click → **Exit**.

## 🎨 Customization

Every coat comes with its own fur, eyes, whiskers, inner ears, and chest patch — a few also carry tabby stripes or calico patches.

| Theme | Fur | Eyes | Markings |
|---|---|---|---|
| **Shadow** *(default)* | Plum-grey | Sky blue | Solid |
| **Ginger** | Warm orange | Seafoam | Tabby |
| **Grey** | Cool grey | Sky blue | Tabby |
| **Snow** | Soft white | Blue | Solid |
| **Midnight** | Near-black | Mint green | Solid |
| **Fable** | Warm cream | Seafoam green | Calico |

Switch anytime from the right-click menu — no restart needed.

## 🦋 A Small Dedication

This version gives DesktopPet a new **Fable** coat and a butterfly companion, both added as a little thank-you to **Claude**, the Anthropic AI who helped bring her to life.

The Fable coat trades her usual palette for warm cream-and-calico fur (`#EEE8DA`), soft rust-amber accents (`#DA7025`), and seafoam-green eyes (`#60D796`). The butterfly always borrows its wing color from whichever theme is active, so under Fable, she's chasing something in matching cream, amber, and seafoam too.

## 🐛 Known Limitations

- Windows-only for now — the transparent window and desktop-awareness features depend on Win32 APIs and Windows-specific Tk behavior.
- Built around a single primary display; multi-monitor and taskbar edge cases aren't specifically handled.
- Mischief mode nudges real windows around your screen — turn it off from the right-click menu if you'd rather she keep her paws to herself.

## 📄 License

No license has been set yet — consider adding one (MIT is a common, permissive choice) before sharing this repo widely.

