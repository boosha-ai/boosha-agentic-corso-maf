"""Il Ricercatore: l'unico agente del Debate Club che ha strumenti.

Nato in EP 2. Il suo lavoro e' produrre il DossierFilm, che e' il contratto verso tutti
gli altri. Da qui in poi nessun altro agente tocca il web: e' questo che rende il
dibattito verificabile.
"""

from agent_framework import Agent

from debate_club.agenti._client import client
from debate_club.istruzioni import carica
from debate_club.middleware import log_step, turno_di_fila
from debate_club.tools import cerca_critica_film, cerca_dati_film, cerca_filmografia


def crea_ricercatore(*, verboso: bool = False, con_filmografia: bool = True) -> Agent:
    """Il Ricercatore, con i suoi tool.

    `verboso=True` attacca la middleware che stampa ogni chiamata a tool: comoda a
    schermo, perche' rende visibile che l'agente sta davvero usando gli strumenti.

    `con_filmografia` gli da' anche `cerca_filmografia`, cioe' la capacita' di **trovarsi
    da solo l'URL** del film a partire dal nome del regista. Serve quando gli si parla in
    linguaggio naturale ("dibattete su The Village di Shyamalan") invece di passargli un
    URL gia' pronto. Mettilo a False per riprodurre il flusso di EP 2, dove la filmografia
    la calcolava il codice in modo deterministico e all'agente arrivava solo l'URL: e' una
    differenza che vale la pena mostrare, perche' e' la scelta tra un passo prevedibile e
    uno lasciato al modello.
    """
    # La critica arriva dalla pagina Wikipedia del film, raggiunta per URL come i dati:
    # cosi' e' del film giusto per costruzione.
    tools = [cerca_dati_film, cerca_critica_film]
    if con_filmografia:
        tools.insert(0, cerca_filmografia)

    # Il tetto alle chiamate a tool, per richiesta. Il default di MAF lascia fino a 40 giri
    # (`max_iterations`), e ogni giro e' una chiamata al modello. `max_function_calls` e' il
    # limite che la doc indica per questo ("the primary knob for controlling cost"): raggiunto
    # il tetto, il modello deve rispondere col testo. Il lavoro vero sono 2 chiamate (3 in
    # DevUI, con la filmografia), e il modello le lancia a coppie in parallelo: il tetto si
    # controlla dopo ogni gruppo, quindi 4 vuol dire al massimo due giri, uno di margine.
    # Non `max_invocations` sul tool: e' un contatore a vita che non si azzera, e i nostri
    # tool sono condivisi fra tutti i run. Il client e' nuovo a ogni `client()`, quindi il
    # tetto vale solo per il Ricercatore.
    cli = client()
    cli.function_invocation_configuration["max_function_calls"] = 4

    return Agent(
        client=cli,
        name="Ricercatore",
        # `description` non e' decorazione: in una group chat finisce dritta nella prompt
        # dell'orchestratore ("here are the valid participant names and their descriptions"),
        # ed e' con quella che il Moderatore decide a chi dare la parola. Senza, legge
        # "<no description, use name to identify the purpose of this participant>" e tira
        # a indovinare dal nome.
        description=(
            "Costruisce il dossier del film con i suoi strumenti: incasso, Rotten Tomatoes, "
            "trama e recensioni con le fonti. Va interpellato PER PRIMO, prima di aprire il "
            "dibattito, perche' senza il suo dossier gli altri non hanno dati su cui "
            "argomentare. Una volta sola."
        ),
        instructions=carica("ricercatore"),
        tools=tools,
        # turno_di_fila: difetto della group chat, vedi middleware.py
        middleware=[log_step, turno_di_fila] if verboso else [turno_di_fila],
    )
