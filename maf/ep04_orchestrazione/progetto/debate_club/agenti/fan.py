"""Il Fan: difende il film.

Nessun tool, di proposito. Non e' una semplificazione: e' il vincolo che tiene in piedi
tutto il resto. Se il Fan potesse cercarsi i dati per conto suo, in EP 6 il Giudice non
avrebbe piu' un metro per dire se un numero e' inventato.
"""

from agent_framework import Agent

from debate_club.agenti._client import client
from debate_club.istruzioni import carica
from debate_club.middleware import turno_di_fila
from debate_club.modelli import DossierFilm


def crea_fan(dossier: DossierFilm | None = None) -> Agent:
    """Il Fan. Se gli passi il dossier, glielo cuciamo nelle istruzioni: cosi' ce l'ha
    davanti a ogni turno, invece di doverselo ricordare da un messaggio di dieci turni fa."""
    istruzioni = carica("fan")
    if dossier is not None:
        istruzioni += f"\n\n--- DOSSIER (la tua unica fonte) ---\n{dossier.model_dump_json(indent=2)}"
    return Agent(
        client=client(),
        name="Fan",
        # Finisce nella prompt dell'orchestratore: e' cosi' che il Moderatore sa a chi
        # sta dando la parola. Vedi la nota in `ricercatore.py`.
        description="Debater a favore del film. Difende, non riassume e non fa il punto.",
        instructions=istruzioni,
        middleware=[turno_di_fila],  # difetto della group chat: vedi middleware.py
    )
