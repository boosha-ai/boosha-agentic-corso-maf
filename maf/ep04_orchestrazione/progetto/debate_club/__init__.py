"""Debate Club - il progetto della serie agentic di Boosha.

Tre agenti discutono un film partendo da un dossier costruito da un quarto agente.
Cresce lungo le puntate: nato in EP 4 come orchestrazione decisa dall'LLM, in EP 5
diventa un workflow deterministico con human-in-the-loop, in EP 6 arriva il Giudice.

Come si legge questa cartella:

    modelli.py        i contratti - cosa passa da un agente all'altro
    tools/            gli strumenti - uno per ruolo, mai un tool finto
    istruzioni/       i prompt, come file .md fuori dal codice
    agenti/           il cast - una factory per agente
    dossier.py        dal film scelto al dossier (il lavoro del Ricercatore)
    orchestrazione.py EP 4 - il dibattito dove il percorso lo decide l'LLM
    middleware.py     la presa tra agente e strumenti: log oggi, guardrail domani
    cli.py            il punto d'ingresso da terminale

Il notebook di ogni puntata importa da qui solo cio' che la puntata ha gia' insegnato;
quello che sta imparando lo riscrive in cella. Cosi' non si ricopia tre volte lo stesso
codice, e resta visibile a schermo la parte che conta.
"""

__version__ = "0.4.0"  # la minor segue la puntata: 0.4 = EP 4
