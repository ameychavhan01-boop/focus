"""Builds the vertical promo videos for the Daily Planner & Habit Tracker Notion template.

Usage:
  python3 build.py A                 -> renders final-videos/version-A.mp4
  python3 build.py A --stills 1,4,11 -> only saves still frames (seconds) for a preview
"""
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MEDIA = os.path.join(ROOT, "template-media")
OUT_DIR = os.path.join(ROOT, "final-videos")
WORK = os.environ.get("WORK_DIR", os.path.join(HERE, ".work"))

W, H, FPS = 1080, 1920, 30
GREEN = (110, 231, 168)
# Screenshot coordinates below are written in a 2000x1500 grid; real files are 2752x2064.
SRC_SCALE = 2752 / 2000

# Layout (pixels in the 1080x1920 video). Kept inside the Reels/Shorts safe zone.
CARD_W, CARD_H = 1000, 760
CARD_X, CARD_Y = (W - CARD_W) // 2, 385
CHIP_CY = 305          # centre of the small label above the screen
CAP_CY = 1335          # centre of the caption (middle of the screen, above the app buttons)

# ---------------------------------------------------------------- versions
VERSIONS = {
    "A": {"hook": "Your day<br>feels messy? <span class='emoji'>😩</span>",
          "hook_sub": "Here's the fix <span class='emoji'>👇</span>",
          "hook_bg": "03-tasks-dailylog.png"},
    "B": {"hook": "I built<br><span class='g'>6 habits</span><br>with this <span class='emoji'>🌱</span>",
          "hook_sub": "My Notion setup <span class='emoji'>👇</span>",
          "hook_bg": "02-dashboard-tasks.png"},
    "C": {"hook": "The only<br><span class='g'>Notion template</span><br>you need <span class='emoji'>✨</span>",
          "hook_sub": "Plan · Track · Grow <span class='emoji'>👇</span>",
          "hook_bg": "01-home.png"},
}

# ---------------------------------------------------------------- feature scenes
# start/end: crop rectangle (x, y, width) in the 2000x1500 grid; height follows the card shape.
# hl: highlight box (x0, y0, x1, y1) in the same grid.
FEATURES = [
    dict(img="02-dashboard-tasks.png", dur=3.5, label="Today &amp; Overdue",
         start=(140, 150, 1730), end=(180, 118, 860), hl=(150, 356, 1032, 452),
         cap="<span class='g'>Today</span> <span class='emoji'>⏰</span> + <span class='g'>Overdue</span> <span class='emoji'>⚠️</span><br>tasks in one place"),
    dict(img="03-tasks-dailylog.png", dur=3.5, label="Task Board",
         start=(150, 150, 1000), end=(850, 150, 1000), hl=(852, 335, 1137, 818),
         cap="Move every task<br><span class='g'>To Do → Doing → Done</span> <span class='emoji'>✅</span>"),
    dict(img="03-tasks-dailylog.png", dur=4.0, label="Daily Log &amp; 6 Habits",
         start=(150, 634, 1140), end=(540, 900, 760), hl=(850, 1240, 1137, 1400),
         cap="Tick 6 daily habits →<br>auto <span class='g'>Habit Score</span>"
             "<span class='sub'><span class='emoji'>🟩🟩🟩🟩⬜⬜</span> 4/6</span>"),
    dict(img="04-goals-weekly.png", dur=3.5, label="Goals",
         start=(150, 360, 1140), end=(150, 350, 900), hl=(556, 666, 848, 882),
         cap="Watch your <span class='g'>goals</span><br>fill up <span class='emoji'>🎯</span>"),
    dict(img="04-goals-weekly.png", dur=3.5, label="Weekly Review",
         start=(150, 634, 1140), end=(430, 664, 1100), hl=(560, 1230, 1515, 1290),
         cap="Sunday review with<br><span class='g'>automatic averages</span> <span class='emoji'>📊</span>"),
]
HOOK_DUR, PLUS_DUR, CTA_DUR = 2.5, 2.0, 3.5
PLUS_ITEMS = [("📈", "Habit progress chart"), ("😊", "Mood chart"),
              ("📅", "Calendar view"), ("📖", "Step-by-step guide")]
TRANS = 0.25  # seconds the outgoing scene keeps animating out after a cut


# ---------------------------------------------------------------- helpers
def ease_io(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)

def ease_out(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3

def ease_back(t):
    t = max(0.0, min(1.0, t)); c = 1.6
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

def lerp(a, b, t): return a + (b - a) * t

def rounded_mask(size, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], r, fill=255)
    return m

def with_alpha(img, a):
    if a >= 0.999: return img
    img = img.copy(); img.putalpha(img.getchannel("A").point(lambda v: int(v * a))); return img

def paste_center(canvas, img, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.01: return
    if abs(scale - 1) > 0.003:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BICUBIC)
    img = with_alpha(img, alpha)
    canvas.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


# ---------------------------------------------------------------- overlays (drawn by the browser)
def build_overlays(ver):
    v = VERSIONS[ver]
    items = [{"name": "hook", "html": f"<div class='hook'><h1>{v['hook']}</h1></div>"},
             {"name": "hook_sub", "html": f"<div class='hook-sub'>{v['hook_sub']}</div>"},
             {"name": "plus_title", "html": "<div class='plus-title'>Plus<span class='g'>…</span></div>"},
             {"name": "cta_price", "html": "<div class='cta'><div class='price'>Get it for<br><span class='g'>₹299</span> / $5</div></div>"},
             {"name": "cta_btn", "html": "<div class='cta'><div class='btn'>Link in bio <span class='emoji'>🔗</span></div></div>"},
             {"name": "brand", "html": "<div class='brand'><span class='emoji'>🌿</span> JSR Enterprises</div>"}]
    for i, f in enumerate(FEATURES):
        items.append({"name": f"cap{i}", "html": f"<div class='cap'>{f['cap']}</div>"})
        items.append({"name": f"chip{i}", "html": f"<div class='chip'><span class='num'>{i + 1}</span>{f['label']}</div>"})
    for i, (ic, txt) in enumerate(PLUS_ITEMS):
        items.append({"name": f"plus{i}", "html": f"<div class='fchip'><span class='ic emoji'>{ic}</span>{txt}</div>"})
    odir = os.path.join(WORK, f"overlays-{ver}")
    os.makedirs(WORK, exist_ok=True)
    jp = os.path.join(WORK, f"overlays-{ver}.json")
    json.dump(items, open(jp, "w"))
    subprocess.run(["node", os.path.join(HERE, "render_overlays.js"), jp, odir], check=True)
    return {it["name"]: Image.open(os.path.join(odir, it["name"] + ".png")).convert("RGBA") for it in items}


# ---------------------------------------------------------------- static assets
def make_background():
    """Dark green-black gradient with two soft green glows."""
    bg = Image.new("RGB", (W, H), (13, 17, 15))
    top, bot = (17, 24, 20), (9, 12, 11)
    grad = Image.linear_gradient("L").resize((W, H))
    bg = Image.composite(Image.new("RGB", (W, H), bot), Image.new("RGB", (W, H), top), grad)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse([-300, 80, 700, 1000], fill=GREEN + (46,))
    d.ellipse([480, 1150, 1500, 2100], fill=GREEN + (34,))
    glow = glow.filter(ImageFilter.GaussianBlur(170))
    out = bg.convert("RGBA"); out.alpha_composite(glow); return out

def make_card_shadow():
    pad = 80
    s = Image.new("RGBA", (CARD_W + pad * 2, CARD_H + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(s).rounded_rectangle([pad, pad + 24, pad + CARD_W, pad + CARD_H + 24], 40, fill=(0, 0, 0, 170))
    return s.filter(ImageFilter.GaussianBlur(34)), pad

def load_media():
    return {f: Image.open(os.path.join(MEDIA, f)).convert("RGB") for f in sorted(os.listdir(MEDIA)) if f.endswith(".png")}

def blurred_bg(img):
    """Full-screen, darkened, blurred version of a screenshot (for hook / CTA backgrounds)."""
    sc = H / img.height
    big = img.resize((int(img.width * sc), H), Image.BICUBIC)
    x0 = (big.width - W) // 2
    big = big.crop((x0, 0, x0 + W, H)).filter(ImageFilter.GaussianBlur(26))
    dark = Image.new("RGB", (W, H), (6, 10, 8))
    return Image.blend(big, dark, 0.62).convert("RGBA")


# ---------------------------------------------------------------- card rendering
CARD_MASK = None
def render_card(src, rect, hl=None, hl_amt=0.0, t_glow=0.0):
    """Crops the screenshot to rect=(x,y,w) [2000-grid], draws spotlight + highlight box."""
    x, y, w = rect; h = w * CARD_H / CARD_W
    gw, gh = src.width / SRC_SCALE, src.height / SRC_SCALE   # keep the camera inside the screenshot
    x = max(0.0, min(x, gw - w)); y = max(0.0, min(y, gh - h))
    box = tuple(v * SRC_SCALE for v in (x, y, x + w, y + h))
    card = src.resize((CARD_W, CARD_H), Image.LANCZOS, box=box).convert("RGBA")
    if hl is not None and hl_amt > 0.01:
        k = CARD_W / w
        hx0, hy0, hx1, hy1 = ((hl[0] - x) * k, (hl[1] - y) * k, (hl[2] - x) * k, (hl[3] - y) * k)
        pad = 10
        # box grows in from 6% bigger
        s = lerp(1.06, 1.0, ease_out(hl_amt))
        cx, cy = (hx0 + hx1) / 2, (hy0 + hy1) / 2
        hw, hh = (hx1 - hx0) / 2 * s + pad, (hy1 - hy0) / 2 * s + pad
        r = [cx - hw, cy - hh, cx + hw, cy + hh]
        a = ease_out(hl_amt)
        dim = Image.new("RGBA", card.size, (0, 0, 0, int(120 * a)))
        hole = Image.new("L", card.size, 0)
        ImageDraw.Draw(hole).rounded_rectangle(r, 22, fill=255)
        dim.putalpha(Image.composite(Image.new("L", card.size, 0), dim.getchannel("A"), hole))
        card.alpha_composite(dim)
        pulse = 0.75 + 0.25 * math.sin(t_glow * 2 * math.pi * 1.0)
        glow = Image.new("RGBA", card.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle(r, 22, outline=GREEN + (int(210 * a * pulse),), width=16)
        card.alpha_composite(glow.filter(ImageFilter.GaussianBlur(12)))
        line = Image.new("RGBA", card.size, (0, 0, 0, 0))
        ImageDraw.Draw(line).rounded_rectangle(r, 22, outline=GREEN + (int(255 * a),), width=7)
        card.alpha_composite(line)
    # rounded corners + thin border
    ImageDraw.Draw(card).rounded_rectangle([0, 0, CARD_W - 1, CARD_H - 1], 40, outline=(255, 255, 255, 40), width=2)
    card.putalpha(CARD_MASK)
    return card


# ---------------------------------------------------------------- timeline
def build_timeline():
    scenes, t = [], 0.0
    scenes.append(dict(kind="hook", start=t, dur=HOOK_DUR)); t += HOOK_DUR
    for i, f in enumerate(FEATURES):
        scenes.append(dict(kind="feature", idx=i, start=t, dur=f["dur"])); t += f["dur"]
    scenes.append(dict(kind="plus", start=t, dur=PLUS_DUR)); t += PLUS_DUR
    scenes.append(dict(kind="cta", start=t, dur=CTA_DUR)); t += CTA_DUR
    return scenes, t


class Renderer:
    def __init__(self, ver):
        global CARD_MASK
        CARD_MASK = rounded_mask((CARD_W, CARD_H), 40)
        self.ver = ver
        self.ov = build_overlays(ver)
        self.media = load_media()
        self.bg = make_background()
        self.shadow, self.spad = make_card_shadow()
        self.hook_bg = blurred_bg(self.media[VERSIONS[ver]["hook_bg"]])
        self.cta_bg = blurred_bg(self.media["01-home.png"])
        self.scenes, self.total = build_timeline()

    def draw_card(self, canvas, card, dy=0.0, scale=1.0, alpha=1.0):
        if alpha <= 0.01: return
        cx, cy = W / 2, CARD_Y + CARD_H / 2 + dy
        paste_center(canvas, self.shadow, cx, cy, scale, alpha * 0.9)
        paste_center(canvas, card, cx, cy, scale, alpha)

    def scene_env(self, lt, dur):
        """Returns (in-progress 0..1, out-progress 0..1) for a scene at local time lt."""
        return ease_out(lt / 0.35), ease_io((lt - dur) / TRANS) if lt > dur else 0.0

    def frame(self, t):
        canvas = self.bg.copy()
        active = [s for s in self.scenes if s["start"] <= t < s["start"] + s["dur"] + TRANS]
        # draw full-screen backgrounds first (hook / cta)
        for s in active:
            lt = t - s["start"]
            if s["kind"] == "hook":
                _, out = self.scene_env(lt, s["dur"])
                canvas = Image.blend(canvas, self.hook_bg, 1 - out) if out > 0 else self.hook_bg.copy()
            if s["kind"] == "cta":
                canvas = Image.blend(canvas, self.cta_bg, ease_io(lt / 0.4))
        for s in active:
            getattr(self, "draw_" + s["kind"])(canvas, s, t - s["start"])
        return canvas.convert("RGB")

    # ----- scenes
    def draw_hook(self, c, s, lt):
        _, out = self.scene_env(lt, s["dur"])
        a = 1 - out
        sc = lerp(0.9, 1.0, ease_back(lt / 0.3)) * lerp(1, 1.06, out)
        # slight continuous push-in keeps it alive
        sc *= 1 + 0.02 * min(lt, s["dur"]) / s["dur"]
        paste_center(c, self.ov["hook"], W / 2, 830, sc, a)
        sub_in = (lt - 0.6) / 0.3
        if sub_in > 0:
            paste_center(c, self.ov["hook_sub"], W / 2, 1230 + 40 * (1 - ease_out(sub_in)),
                         lerp(0.85, 1, ease_back(sub_in)), min(1, ease_out(sub_in)) * a)

    def draw_feature(self, c, s, lt):
        f = FEATURES[s["idx"]]; src = self.media[f["img"]]
        inn, out = self.scene_env(lt, s["dur"])
        # camera: move start->end in the first 1.3s, then keep drifting slowly
        mv = ease_io((lt - 0.1) / 1.3)
        x = lerp(f["start"][0], f["end"][0], mv); y = lerp(f["start"][1], f["end"][1], mv)
        w = lerp(f["start"][2], f["end"][2], mv)
        drift = 0.025 * ease_io((lt - 1.4) / (s["dur"] - 1.4))
        cxs, cys = x + w / 2, y + w * CARD_H / CARD_W / 2
        w2 = w * (1 - drift)
        rect = (cxs - w2 / 2, cys - w2 * CARD_H / CARD_W / 2, w2)
        hl_amt = (lt - 1.35) / 0.35
        card = render_card(src, rect, f["hl"], hl_amt, lt)
        dy = lerp(140, 0, inn) - 90 * out
        self.draw_card(c, card, dy, lerp(0.94, 1, inn) * lerp(1, 0.96, out), inn * (1 - out))
        # label chip
        ci = ease_out((lt - 0.1) / 0.35)
        paste_center(c, self.ov[f"chip{s['idx']}"], W / 2 - 30 * (1 - ci), CHIP_CY - 60 * out, 1, ci * (1 - out))
        # caption pops in
        ca = (lt - 0.25) / 0.35
        if ca > 0:
            paste_center(c, self.ov[f"cap{s['idx']}"], W / 2, CAP_CY + 30 * (1 - ease_out(ca)) - 90 * out,
                         lerp(0.82, 1, ease_back(ca)) * lerp(1, 0.96, out), min(1, ease_out(ca)) * (1 - out))

    def draw_plus(self, c, s, lt):
        _, out = self.scene_env(lt, s["dur"])
        ti = (lt) / 0.3
        paste_center(c, self.ov["plus_title"], W / 2, 520 - 80 * out, lerp(0.85, 1, ease_back(ti)), min(1, ease_out(ti)) * (1 - out))
        for i in range(len(PLUS_ITEMS)):
            p = (lt - 0.2 - i * 0.12) / 0.3
            if p <= 0: continue
            paste_center(c, self.ov[f"plus{i}"], W / 2 + 120 * (1 - ease_out(p)), 760 + i * 175 - 80 * out,
                         1, min(1, ease_out(p)) * (1 - out))

    def draw_cta(self, c, s, lt):
        # template preview card at the top
        cin = ease_out(lt / 0.45)
        rect_start, rect_end = (40, 120, 1920), (150, 400, 1700)
        mv = ease_io(lt / s["dur"])
        rect = tuple(lerp(a, b, mv) for a, b in zip(rect_start, rect_end))
        card = render_card(self.media["01-home.png"], rect)
        small = card.resize((int(CARD_W * 0.8), int(CARD_H * 0.8)), Image.LANCZOS)
        sh = self.shadow.resize((int(self.shadow.width * 0.8), int(self.shadow.height * 0.8)))
        cy = 600 + 120 * (1 - cin)
        paste_center(c, sh, W / 2, cy, 1, cin * 0.9); paste_center(c, small, W / 2, cy, 1, cin)
        p = (lt - 0.2) / 0.35
        if p > 0:
            paste_center(c, self.ov["cta_price"], W / 2, 1135, lerp(0.8, 1, ease_back(p)), min(1, ease_out(p)))
        b = (lt - 0.45) / 0.35
        if b > 0:
            pulse = 1 + 0.035 * math.sin(max(0, lt - 0.8) * 2 * math.pi * 2.0)   # 2 beats/second (120 BPM)
            paste_center(c, self.ov["cta_btn"], W / 2, 1385, lerp(0.7, 1, ease_back(b)) * pulse, min(1, ease_out(b)))
        br = (lt - 0.7) / 0.35
        if br > 0:
            paste_center(c, self.ov["brand"], W / 2, 1560, 1, min(1, ease_out(br)))


# ---------------------------------------------------------------- main
def main():
    ver = sys.argv[1].upper() if len(sys.argv) > 1 else "A"
    r = Renderer(ver)
    if "--stills" in sys.argv:
        times = [float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")]
        odir = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(WORK, f"stills-{ver}")
        os.makedirs(odir, exist_ok=True)
        for tt in times:
            r.frame(tt).save(os.path.join(odir, f"still-{ver}-{tt:05.2f}s.png"))
        print("stills saved to", odir); return
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"version-{ver}.mp4")
    n = int(round(r.total * FPS))
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           # silent audio track: some apps handle videos with an audio stream more reliably
                           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                           "-shortest", "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "17",
                           "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "128k",
                           "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(r.frame(i / FPS).tobytes())
        if i % 60 == 0: print(f"  frame {i}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
