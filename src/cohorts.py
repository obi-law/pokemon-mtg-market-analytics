"""Locked analysis cohorts - single source of truth for all scripts.

Window: 2024-02-01 .. 2026-06-30, matched across games.
Locked 2026-07-15 from live API/MTGJSON output (not from memory).
"""

POKEMON_COHORT = [
    "sv5",       # Temporal Forces        2024-03-22  main
    "sv6",       # Twilight Masquerade    2024-05-24  main
    "sv6pt5",    # Shrouded Fable         2024-08-02  special
    "sv7",       # Stellar Crown          2024-09-13  main
    "sv8",       # Surging Sparks         2024-11-08  main
    "sv8pt5",    # Prismatic Evolutions   2025-01-17  special
    "sv9",       # Journey Together       2025-03-28  main
    "sv10",      # Destined Rivals        2025-05-30  main
    "zsv10pt5",  # Black Bolt             2025-07-18  special (paired w/ White Flare)
    "rsv10pt5",  # White Flare            2025-07-18  special (paired w/ Black Bolt)
    "me1",       # Mega Evolution         2025-09-26  main
    "me2",       # Phantasmal Flames      2025-11-14  main
    "me2pt5",    # Ascended Heroes        2026-01-30  special
    "me3",       # Perfect Order          2026-03-27  main
    "me4",       # Chaos Rising           2026-05-22  main
]

MTG_COHORT = [
    "MKM",  # Murders at Karlov Manor        2024-02-09  standard
    "OTJ",  # Outlaws of Thunder Junction    2024-04-19  standard
    "BLB",  # Bloomburrow                    2024-08-02  standard
    "DSK",  # Duskmourn: House of Horror     2024-09-27  standard
    "FDN",  # Foundations                    2024-11-15  standard
    "DFT",  # Aetherdrift                    2025-02-14  standard
    "TDM",  # Tarkir: Dragonstorm            2025-04-11  standard
    "FIN",  # Final Fantasy                  2025-06-13  universes_beyond
    "EOE",  # Edge of Eternities             2025-08-01  standard
    "SPM",  # Marvel's Spider-Man            2025-09-26  universes_beyond
    "TLA",  # Avatar: The Last Airbender     2025-11-21  universes_beyond
    "ECL",  # Lorwyn Eclipsed                2026-01-23  standard
    "TMT",  # Teenage Mutant Ninja Turtles   2026-03-06  universes_beyond
    "SOS",  # Secrets of Strixhaven          2026-04-24  standard
    "MSH",  # Marvel Super Heroes            2026-06-26  universes_beyond
]