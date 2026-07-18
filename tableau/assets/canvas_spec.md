# Canvas + zone spec — both cards (locked, shared geometry)

Dashboard size: FIXED 1300 x 3200 px. One dashboard per card:
"The MTG reading" (frame_mtg) and "The Pokemon reading" (frame_pokemon).
Background image floats at x=0, y=0, w=1300, h=3200. All zones below are
transparent windows drawn on the frame - float sheets/text inside them.

| zone                | x   | y    | w    | h    | contents                          |
|---------------------|-----|------|------|------|-----------------------------------|
| nameplate           | 110 | 110  | 1080 | 96   | title text + orb images (right)   |
| subtitle strip      | 110 | 220  | 1080 | 50   | pov line + flip navigation button |
| art window          | 110 | 290  | 1080 | 1210 | hero: 30-set return dumbbell      |
| type line           | 110 | 1530 | 1080 | 56   | "Infographic - market analytics"  |
| rules panel         | 110 | 1616 | 1080 | 980  | act 1 (concentration) + act 3 (age)|
| flavor zone         | 110 | 2630 | 1080 | 90   | italic serif flavor line          |
| feature zone        | 110 | 2750 | 1080 | 150  | MTG: P/T plate at x940 w250 h80   |
|                     |     |      |      |      | PKM: weakness/resistance/retreat  |
| collector strip     | 110 | 2980 | 1080 | 80   | legal-line methodology text       |

Inner safe margin: keep all live content >= x110 / <= x1190.
Fonts: Raleway (display: title, attack names, P/T) / Lato (body, notes);
flavor text: Lato Italic serif-styled fallback per build steps.
Palette: "PMA Chase Card" (see palette_block.tps.txt).
Emphasis rule: active game = its accent family; other game = #3A4058 dim.
Facts identical on both cards - only emphasis, callouts, and copy change.
