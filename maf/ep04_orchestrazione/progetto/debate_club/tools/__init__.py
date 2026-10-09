"""I tool del Debate Club, raccolti in un posto solo.

Ogni tool ha UN ruolo, nessuno e' forzato:
- `cerca_filmografia`  -> la lista dei film di un regista, con gli URL
- `cerca_dati_film`    -> i numeri di un film: incasso, Rotten Tomatoes, descrizione
- `cerca_critica_film` -> la critica di un film, dalla sua pagina Wikipedia
- `manda_notifica`     -> la push sul telefono

Accanto a ogni tool c'e' la funzione pura corrispondente (`filmografia`, `dati_film`,
`critica_film`, `manda_push`): stessa logica, ma la chiami tu invece di
lasciarla decidere al modello. Serve quando un passo deve essere deterministico, come la
discovery.
"""

from debate_club.tools.notifiche import manda_notifica, manda_push
from debate_club.tools.wikipedia import (
    CriticaFilm,
    cerca_critica_film,
    cerca_dati_film,
    cerca_filmografia,
    critica_film,
    dati_film,
    filmografia,
)

__all__ = [
    "CriticaFilm",
    "cerca_critica_film",
    "cerca_dati_film",
    "cerca_filmografia",
    "critica_film",
    "dati_film",
    "filmografia",
    "manda_notifica",
    "manda_push",
]
