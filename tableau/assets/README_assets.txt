PMA "Chase Card" — T0 Asset Pack (Foil A-Pokemon / Foil B-MTG, locked 2026-07-18)
==================================================================================

Ship this folder's contents to:  tableau/assets/   (committed to the repo)
All assets are original ornamentation — no card art, logos, set symbols, or
trade dress from either company.

ASSETS
------
frame_pokemon_1300x3800.png   Foil A. Full-spectrum cosmos gradient border,
                              star scatter baked into the band, gold inner
                              stroke. Transparent exterior corners + interior
                              window. Place as a floating Image object at
                              x=0, y=0, w=1300, h=3800 (fit: Fit Image OFF,
                              use exact size).
frame_mtg_1300x3800.png       Foil B. Violet metal border, single diagonal
                              rainbow sheen band, violet inner stroke. Same
                              placement as above.
orb_pokemon_gold.png          160px nameplate orb, Raleway Bold "P".
orb_mtg_violet.png            160px nameplate orb, Raleway Bold "M".
                              Place at ~72px rendered size in the nameplate,
                              active game's orb full opacity; the other orb
                              is placed by a second Image object — Tableau
                              can't dim an image, so the "inactive" state is
                              handled by which container is visible (see
                              toggle note).
divider_pokemon.png           1100x34 type-line divider, center diamond.
divider_mtg.png               Repeats between acts; also the type-line bar.
sparkle_*.png                 48px free-placement glints (pink/teal/blue/
                              gold/violet). Pokemon layout may use several;
                              MTG layout uses at most violet + gold, sparsely.
preview_frames.png            Reference montage only — do not place.

CANVAS SPEC (both templates share identical geometry)
-----------------------------------------------------
Dashboard size:      Fixed 1300 x 3800
Dashboard bg:        #0B0E16  (dark mat behind the rounded frame corners)
Card interior:       #10141F  (floating Blank object or bg zone under the
                              frame window)
Border band:         44 px    (baked into frame PNGs)
Content safe area:   x 100..1200  (1100 wide — matches divider width)

Zone map (y-ranges, both templates):
  120-260    Nameplate: card name + orb
  260-320    Perspective subline
  360-1500   Art window (hero: 15-set sealed lollipops vs launch line)
  1540-1580  Type line (divider PNG)
  1620-2500  Rules box Act 1: concentration bar + singles stats
  2540-3200  Rules box Act 2: rarity ladder / callouts
  3240-3360  Flavor text (italic)
  3380-3480  P/T box (right-aligned; sealed multiple)
  3560-3720  Collector strip (methodology fine print)

TEMPLATE TOGGLE
---------------
Dynamic Zone Visibility (Tableau 2022.3+): one parameter [Card View]
(Pokemon | MTG), two boolean calcs ([Show Pokemon] / [Show MTG]), two
floating containers each holding its frame image + game-specific objects.
Shared worksheets swap accent colors via parameter-driven calcs.
Details arrive in T1.

PALETTE — paste into Preferences.tps (BACK UP Preferences.tps AND
Preferences.txt FIRST; restart Tableau to load)
------------------------------------------------------------------
<color-palette name="PMA Chase Card" type="regular">
  <color>#F5C84C</color>  <!-- frame gold      : Pokemon accent / positive return -->
  <color>#9D8CFF</color>  <!-- frame violet    : MTG accent                       -->
  <color>#EDEAE2</color>  <!-- text primary    : headline text                    -->
  <color>#9AA3B5</color>  <!-- text secondary  : captions, sublabels              -->
  <color>#5A6478</color>  <!-- reference slate : axis, reference lines            -->
  <color>#7A8298</color>  <!-- negative return : below-launch marks               -->
  <color>#161C2B</color>  <!-- panel ink       : matte data windows               -->
  <color>#10141F</color>  <!-- canvas ink      : card interior background         -->
</color-palette>

Mirror the same block (with comments) into Preferences.txt per convention.

FONTS
-----
Raleway (headers/display) + Lato (body). Install the /static weight files
in Windows (not the variable font file), then restart Tableau. Both are
Tableau-Safe for Public rendering.
