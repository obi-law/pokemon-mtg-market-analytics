"""Generate the T0 asset pack: two card-frame backgrounds (1300x3200) and
two orb accents (256px), drawn at 2x and downscaled for clean edges.

Shared geometry between frames (perspective invariance); only the accent
family changes. No text is baked in - all text stays live in Tableau.
"""

from PIL import Image, ImageDraw, ImageFilter

S = 2  # supersample factor
W, H = 1300 * S, 3200 * S

INK = (16, 20, 31, 255)         # #10141F canvas
PANEL = (22, 28, 43, 255)       # #161C2B plates
PANEL_DEEP = (12, 16, 26, 255)  # #0C101A art window
PANEL_RULES = (15, 20, 32, 255) # #0F1420 rules box
HAIR = (42, 50, 71, 255)        # #2A3247 hairlines
SLATE = (90, 100, 120, 255)     # #5A6478

GOLD_HI, GOLD_LO = (245, 200, 76), (184, 122, 16)
VIO_HI, VIO_LO = (157, 140, 255), (74, 62, 153)


def vgrad(size, top, bot):
    w, h = size
    img = Image.new("RGBA", size)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,)
        for x in range(w):
            px[x, y] = c
    return img


def rounded_mask(size, box, radius, width=0):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    if width:
        d.rounded_rectangle(box, radius=radius, outline=255, width=width)
    else:
        d.rounded_rectangle(box, radius=radius, fill=255)
    return m


def hatch_layer(size, alpha=16, gap=26):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w, h = size
    for c in range(-h, w, gap * S):
        d.line([(c, 0), (c + h, h)], fill=(255, 255, 255, alpha), width=S)
    return img


def corner_ornaments(d, accent):
    r1, r2 = 34 * S, 22 * S
    pts = [(96 * S, 96 * S, 0), (1204 * S, 96 * S, 90),
           (96 * S, 3104 * S, 270), (1204 * S, 3104 * S, 180)]
    for cx, cy, rot in pts:
        start = {0: 180, 90: 270, 270: 90, 180: 0}[rot]
        d.arc([cx - r1, cy - r1, cx + r1, cy + r1], start, start + 90,
              fill=accent + (140,), width=2 * S)
        d.arc([cx - r2, cy - r2, cx + r2, cy + r2], start, start + 90,
              fill=accent + (90,), width=2 * S)
        d.ellipse([cx - 3 * S, cy - 3 * S, cx + 3 * S, cy + 3 * S],
                  fill=accent + (200,))


def build_frame(path, hi, lo, thread, variant):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # gradient border ring (outer radius 36, band 8px) + fill
    outer_box = [60 * S, 60 * S, 1240 * S, 3140 * S]
    grad = vgrad((W, H), hi, lo)
    ring = rounded_mask((W, H), outer_box, 36 * S)
    img.paste(grad, (0, 0), ring)
    # subtle foil hatch on the border zone only
    img.paste(hatch_layer((W, H)), (0, 0), ring)

    inner_box = [68 * S, 68 * S, 1232 * S, 3132 * S]
    ink_mask = rounded_mask((W, H), inner_box, 30 * S)
    ink_img = Image.new("RGBA", (W, H), INK)
    img.paste(ink_img, (0, 0), ink_mask)

    d = ImageDraw.Draw(img)
    # accent thread hairline just inside the ink edge (duality nod)
    d.rounded_rectangle([76 * S, 76 * S, 1224 * S, 3124 * S], radius=26 * S,
                        outline=thread + (70,), width=S)

    # nameplate
    d.rounded_rectangle([110 * S, 110 * S, 1190 * S, 206 * S], radius=16 * S,
                        fill=PANEL, outline=HAIR, width=S)
    # art window
    d.rounded_rectangle([110 * S, 290 * S, 1190 * S, 1500 * S], radius=16 * S,
                        fill=PANEL_DEEP, outline=HAIR, width=S)
    # type line bar
    d.rounded_rectangle([110 * S, 1530 * S, 1190 * S, 1586 * S], radius=12 * S,
                        fill=PANEL)
    # rules panel
    d.rounded_rectangle([110 * S, 1616 * S, 1190 * S, 2596 * S], radius=16 * S,
                        fill=PANEL_RULES, outline=HAIR, width=S)

    if variant == "mtg":
        # P/T plate bottom-right
        d.rounded_rectangle([940 * S, 2750 * S, 1190 * S, 2830 * S],
                            radius=16 * S, fill=PANEL, outline=SLATE, width=S)
    else:
        # weakness / resistance / retreat strip rules
        d.line([110 * S, 2750 * S, 1190 * S, 2750 * S], fill=HAIR, width=S)
        d.line([110 * S, 2900 * S, 1190 * S, 2900 * S], fill=HAIR, width=S)

    # collector strip rule
    d.line([110 * S, 2960 * S, 1190 * S, 2960 * S], fill=HAIR, width=S)

    corner_ornaments(d, hi)

    out = img.resize((1300, 3200), Image.LANCZOS)
    out.save(path)
    print(f"{path} {out.size}")


def build_orb(path, hi, lo):
    s = 256 * S
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    grad = vgrad((s, s), hi, lo)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).ellipse([8 * S, 8 * S, 248 * S, 248 * S], fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.ellipse([8 * S, 8 * S, 248 * S, 248 * S], outline=(16, 20, 31, 255),
              width=6 * S)
    # specular crescent
    hl = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse([50 * S, 34 * S, 200 * S, 120 * S],
                               fill=(255, 255, 255, 60))
    hl = hl.filter(ImageFilter.GaussianBlur(10 * S))
    img.alpha_composite(hl)
    img.resize((256, 256), Image.LANCZOS).save(path)
    print(path)


if __name__ == "__main__":
    base = "tableau/assets"
    build_frame(f"{base}/frame_mtg_1300x3200.png", VIO_HI, VIO_LO, GOLD_HI, "mtg")
    build_frame(f"{base}/frame_pokemon_1300x3200.png", GOLD_HI, GOLD_LO, VIO_HI, "pokemon")
    build_orb(f"{base}/orb_violet_256.png", VIO_HI, VIO_LO)
    build_orb(f"{base}/orb_gold_256.png", GOLD_HI, GOLD_LO)
