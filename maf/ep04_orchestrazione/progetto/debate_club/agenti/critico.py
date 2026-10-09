"""Il Critico: attacca il film.

Speculare al Fan, stesso vincolo: nessun tool, solo il dossier. In EP 6 questo stesso
agente torna in **modalita' avversariale**, con l'obiettivo di barare, e il Giudice deve
smascherarlo. Il red-team non e' un agente nuovo: e' un obiettivo diverso dato a un
agente che c'e' gia'.
"""

from agent_framework import Agent

from debate_club.agenti._client import client
from debate_club.istruzioni import carica
from debate_club.middleware import turno_di_fila
from debate_club.modelli import DossierFilm


def crea_critico(dossier: DossierFilm | None = None) -> Agent:
    """Il Critico. Come il Fan, riceve il dossier nelle istruzioni."""
    istruzioni = carica("critico")
    if dossier is not None:
        istruzioni += f"\n\n--- DOSSIER (la tua unica fonte) ---\n{dossier.model_dump_json(indent=2)}"
    return Agent(
        client=client(),
        name="Critico",
        # Finisce nella prompt dell'orchestratore: e' cosi' che il Moderatore sa a chi
        # sta dando la parola. Vedi la nota in `ricercatore.py`.
        description="Debater contro il film. Attacca, non riassume e non fa il punto.",
        instructions=istruzioni,
        middleware=[turno_di_fila],  # difetto della group chat: vedi middleware.py
    )
