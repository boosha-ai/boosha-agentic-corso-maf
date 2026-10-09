"""Il Moderatore: decide chi parla.

E' l'agente che rende EP 4 quello che e'. Non esegue un giro prestabilito: a ogni turno
sceglie lui il prossimo oratore, e decide lui quando il dibattito ha detto abbastanza.
Il percorso non e' nel codice, e' una decisione del modello presa a runtime.

In EP 5 gran parte di questo lavoro passa al grafo, e il confronto tra le due versioni
e' la tesi della puntata.
"""

from typing import Literal

from agent_framework import Agent

from debate_club.agenti._client import client
from debate_club.istruzioni import carica


def crea_moderatore(apertura: Literal["dibattito", "con_ricerca"] = "dibattito") -> Agent:
    """Il Moderatore. Nessun tool: il suo strumento e' dare la parola.

    Le istruzioni sono due pezzi: il **carattere** (`moderatore.md`, uguale sempre) e
    l'**apertura**, che dipende da chi siede al tavolo (`apertura_<nome>.md`). Separati,
    nessuno dei due smentisce l'altro.
    """
    return Agent(
        client=client(),
        name="Moderatore",
        instructions=f"{carica('moderatore')}\n\n{carica(f'apertura_{apertura}')}",
    )
