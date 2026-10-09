"""EP 4 - il Debate Club come orchestrazione: il percorso lo decide l'LLM.

`GroupChatBuilder` mette Fan e Critico attorno a un tavolo e da' al Moderatore il compito
di dare la parola. Nessuno qui dentro scrive "prima parla il Fan, poi il Critico": la
sequenza e' una decisione presa a runtime dal modello. Spesso esce uguale a quella che
scriveresti tu (alternare e' quello che fa un buon moderatore), ma non l'hai decisa tu.

E' il contrario di quello che faremo in EP 5, dove il percorso lo disegni tu.

Nota: le orchestrazioni sono workflow pre-costruiti. `build()` torna un `Workflow` vero,
quindi ci si puo' puntare `WorkflowViz` e DevUI esattamente come sul grafo di EP 5.
"""

import re

from agent_framework import Workflow
from agent_framework.orchestrations import GroupChatBuilder

from debate_club.agenti import crea_critico, crea_fan, crea_moderatore, crea_ricercatore
from debate_club.modelli import DossierFilm, Trascrizione

MOTION_DEFAULT = "Questo film e' un capolavoro incompreso, o e' semplicemente sopravvalutato?"

# I ruoli che argomentano. Il Moderatore da' la parola, il Ricercatore porta i dati:
# nessuno dei due e' parte del dibattito, quindi i loro turni non contano come round e
# non finiscono nella trascrizione che valutera' il Giudice.
ORATORI = ("Fan", "Critico")

ROUND_DEFAULT = 3


def limite_round_da_messaggio(messaggi) -> bool:
    """Termination condition: ferma il dibattito quando i debater hanno fatto i round
    chiesti **nel messaggio iniziale** ("Durata: 2 round a testa").

    `max_rounds` si fissa quando costruisci l'orchestrazione e da DevUI non si tocca; una
    `termination_condition` invece riceve tutti i messaggi, quindi legge il numero che hai
    scritto tu e conta i turni. **Chi parla lo decide l'LLM, quando si smette lo decide una
    funzione tua.**

    Cosa garantisce: puo' solo *fermare*, non *far continuare*. Il **tetto** e' garantito;
    il **minimo** no, perche' il Moderatore puo' chiudere prima. In un grafo (EP 5) il numero
    di giri e' una proprieta' della topologia, e li' sono garantiti entrambi.

    Il messaggio iniziale si riconosce perche' non ha un autore: se lo si riempie (il campo
    `author_name` nel form di DevUI) il numero viene ignorato e vale `ROUND_DEFAULT`.
    """
    testo = ""
    for m in messaggi:
        if not getattr(m, "author_name", None):  # il messaggio iniziale, quello umano
            testo = str(getattr(m, "text", "") or "")
            break
    trovato = re.search(r"(\d+)\s*(?:round|giri|turni)", testo, re.IGNORECASE)
    voluti = int(trovato.group(1)) if trovato else ROUND_DEFAULT
    turni = sum(1 for m in messaggi if str(getattr(m, "author_name", "")) in ORATORI)
    return turni >= voluti * len(ORATORI)


def debate_club_completo(*, max_rounds: int = 30, nome: str = "Debate Club (ricerca + dibattito)") -> Workflow:
    """Il Debate Club che fa **tutto**, ricerca compresa: un'entity sola da lanciare in DevUI.

    Il Ricercatore e' un **partecipante** della group chat, non un nodo di un grafo: e' il
    Moderatore a dargli la parola per primo. Resta tutto dentro EP 4 (il percorso lo decide
    l'LLM), senza anticipare il `WorkflowBuilder` di EP 5.

    Fan e Critico qui non hanno il dossier nelle istruzioni: lo leggono dalla conversazione,
    dove l'ha messo il Ricercatore. E in una stella tutti vedono tutto, anche gli ordini
    rivolti al gruppo: per questo le loro istruzioni difendono il ruolo.
    """
    return GroupChatBuilder(
        name=nome,
        participants=[crea_ricercatore(), crea_fan(), crea_critico()],
        orchestrator_agent=crea_moderatore("con_ricerca"),
        termination_condition=limite_round_da_messaggio,  # il limite vero, scritto nel messaggio
        # La rete di sicurezza: senza nessuno dei due freni "the conversation will continue
        # indefinitely" (docstring del framework).
        max_rounds=max_rounds,
        # Fa uscire i turni come eventi `output`, cioe' in `get_outputs()`: altrimenti l'output
        # finale contiene solo la chiusura del Moderatore (verificato sul sorgente).
        output_from="all",
    ).build()


def costruisci_debate_club(
    dossier: DossierFilm,
    *,
    max_rounds: int = 6,
    nome: str = "Debate Club",
) -> Workflow:
    """Il Debate Club pronto a girare.

    `max_rounds` non e' un dettaglio: e' l'antidoto ai loop. Un'orchestrazione dove il
    modello decide quando smettere e' un'orchestrazione che puo' non smettere, e ogni
    turno e' una chiamata che paghi.

    `nome` finisce nella sidebar di DevUI: senza, si legge "GroupChat".
    """
    return GroupChatBuilder(
        name=nome,
        participants=[crea_fan(dossier), crea_critico(dossier)],
        orchestrator_agent=crea_moderatore("dibattito"),
        termination_condition=limite_round_da_messaggio,
        max_rounds=max_rounds,
        output_from="all",  # i turni in `get_outputs()`: vedi `debate_club_completo`
    ).build()


async def dibatti(
    dossier: DossierFilm,
    *,
    motion: str = MOTION_DEFAULT,
    max_rounds: int = 6,
) -> Trascrizione:
    """Fa girare il dibattito e restituisce la trascrizione tipizzata.

    La trascrizione non e' un log: e' il contratto verso EP 5 (stato condiviso del grafo)
    e verso EP 6 (cio' che il Giudice legge per dare il verdetto).
    """
    wf = costruisci_debate_club(dossier, max_rounds=max_rounds)
    risultato = await wf.run(f"{motion}\n\nIl film in discussione e': {dossier.titolo} ({dossier.anno}).")
    return trascrizione_da_risultato(risultato, dossier, motion)


def trascrizione_da_risultato(risultato, dossier: DossierFilm, motion: str) -> Trascrizione:
    """Ricostruisce chi ha parlato e quando, dall'esito della group chat.

    Qui c'e' il punto didattico di EP 4: il percorso non lo sapevi in anticipo, lo leggi
    **dopo**. In EP 5 e' l'opposto, il percorso e' il grafo che hai disegnato tu.
    """
    t = Trascrizione(film=f"{dossier.titolo} ({dossier.anno})", motion=motion)
    round_corrente, gia_parlato = 1, set()
    for oratore, testo in _messaggi(risultato):
        if oratore in gia_parlato:  # ha gia' parlato in questo giro: si apre il round dopo
            round_corrente += 1
            gia_parlato = set()
        gia_parlato.add(oratore)
        t.aggiungi(round=round_corrente, oratore=oratore, testo=testo)
    return t


def _messaggi(risultato) -> list[tuple[str, str]]:
    """Estrae (oratore, testo) dagli output della group chat.

    Forma verificata sul package: `get_outputs()` torna una lista di `AgentResponse`,
    e il messaggio sta dentro `.messages`, con l'autore in `.author_name`.
    """
    fuori: list[tuple[str, str]] = []
    for out in risultato.get_outputs():
        for m in getattr(out, "messages", None) or []:
            nome = str(getattr(m, "author_name", "") or "")
            testo = str(getattr(m, "text", "") or "").strip()
            if testo and nome in ORATORI:
                fuori.append((nome, testo))
    return fuori
