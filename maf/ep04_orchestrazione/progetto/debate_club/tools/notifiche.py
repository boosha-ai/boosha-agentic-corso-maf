"""Tool notifica push (Pushover).

In EP 1 la push era un side-effect del codice: la mandavamo noi, sempre. Da EP 2 e' un
tool, e la differenza e' tutta li': ora e' l'agente a decidere se serve.

**In EP 4 si usa `manda_push`, la funzione pura, e NON il tool.** Non e' una svista: a
fine dibattito la notifica e' la **consegna** del risultato di un lavoro lungo (lanci,
te ne vai, la battuta finale ti raggiunge), e li' non c'e' niente da decidere. E' un
fatto del programma, non un giudizio dell'agente.

La domanda da farsi ogni volta e' quella: **c'e' qualcosa da decidere?** Se si', tool.
Se no, funzione. Un tool che l'agente chiama sempre e comunque e' decorativo.
"""

import os
from typing import Annotated

import httpx
from agent_framework import tool


def manda_push(messaggio: str, titolo: str = "Debate Club") -> str:
    """Manda la notifica. Funzione pura: la chiami tu, senza passare da un agente."""
    token, user = os.environ.get("PUSHOVER_TOKEN"), os.environ.get("PUSHOVER_USER")
    if not (token and user):
        return "Pushover non configurato: notifica non inviata (aggiungi PUSHOVER_TOKEN e PUSHOVER_USER al .env)."
    try:
        r = httpx.post(
            "https://api.pushover.net/1/messages.json",
            data={"token": token, "user": user, "message": messaggio[:1024], "title": titolo},
            timeout=10,
        )
        return "notifica inviata" if r.json().get("status") == 1 else f"errore Pushover: {r.text}"
    except Exception as e:
        # rete lenta o timeout: restituiamo un messaggio, NON solleviamo.
        # Un tool che esplode fa fallire il turno dell'agente per una cosa accessoria.
        return f"notifica non inviata (problema di rete): {e}"


@tool
def manda_notifica(
    messaggio: Annotated[str, "il testo della notifica da inviare"],
    titolo: Annotated[str, "il titolo della notifica"] = "Debate Club",
) -> str:
    """Manda una notifica push sul telefono dell'utente."""
    return manda_push(messaggio, titolo)
