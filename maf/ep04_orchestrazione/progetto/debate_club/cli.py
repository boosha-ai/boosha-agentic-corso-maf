"""Il Debate Club da terminale.

    uv run debate-club filmografia "M. Night Shyamalan"
    uv run debate-club dossier     "M. Night Shyamalan" --film 6
    uv run debate-club dibatti     "M. Night Shyamalan" --film 6 --round 4
    uv run debate-club devui

L'ultimo comando non vuole argomenti: apre DevUI e basta. Regista, film e motion si
scrivono nel form della UI, e il Ricercatore si cerca da solo filmografia e URL.

Negli altri comandi il dossier, una volta costruito, viene **riusato**: la ricerca costa
chiamate al modello, e rifarla a ogni ciak e' denaro buttato.
Con `--rifai` la si rifa' da capo.
"""

import argparse
import asyncio
import os
import secrets
import sys
from pathlib import Path

CARTELLA_DOSSIER = Path(__file__).resolve().parent.parent / "dossier"

MOTION_DEFAULT = "Capolavoro incompreso o semplicemente sopravvalutato?"


def _scegli_film(regista: str, indice: int):
    """Il film si sceglie con `--film`, cioe' PRIMA che il sistema parta.

    Niente `input()`, di proposito: chiedere il film da terminale sembrerebbe
    human-in-the-loop e non lo e'. Qui l'umano sta **fuori**, decide un parametro e poi
    lancia; il flusso agentico non e' ancora cominciato, ed e' quello che fa qualunque
    script. L'human-in-the-loop vero arriva in EP 5 (`ctx.request_info`): li' il workflow
    e' gia' in corsa, si **sospende** a meta' grafo, lo stato resta congelato in un
    checkpoint e riparte quando arriva la risposta - che puo' arrivare ore dopo, da un
    form web, e da una persona diversa da chi ha lanciato.
    """
    from debate_club.tools import filmografia

    print(f"\n== filmografia di {regista} (Wikipedia) ==")
    f = filmografia(regista)
    if not f.film:
        sys.exit(f"Nessuna filmografia trovata per '{regista}'.")
    for i, x in enumerate(f.film, 1):
        print(f"  {i:2d}. {x.anno}  {x.titolo}")
    scelto = f.film[max(0, min(indice - 1, len(f.film) - 1))]
    print(f"\n== scelto: {scelto.titolo} ({scelto.anno})  (con --film ne scegli un altro) ==")
    return scelto


async def _dossier(regista: str, indice: int, salva: bool = True, riusa: bool = False):
    from debate_club.dossier import costruisci_dossier, salva_dossier, trova_dossier

    scelto = _scegli_film(regista, indice)
    if riusa:
        gia = trova_dossier(CARTELLA_DOSSIER, scelto.titolo, scelto.anno)
        if gia is not None:
            print(f"\n== dossier gia' pronto, lo riuso: {gia.titolo} ({gia.anno}) ==")
            print("   (--rifai per ricostruirlo da zero)")
            return gia
    print("\n== il Ricercatore costruisce il dossier ==")
    d = await costruisci_dossier(scelto, regista, verboso=True)
    pos = sum(r.sentiment == "positiva" for r in d.recensioni)
    neg = sum(r.sentiment == "negativa" for r in d.recensioni)
    print(f"  {d.titolo} ({d.anno}) - incasso {d.incasso}, RT {d.rotten_tomatoes}")
    print(f"  Metacritic {d.metacritic}, CinemaScore {d.cinemascore}")
    print(f"  recensioni: {pos} positive / {neg} negative")
    if salva:
        j, m = salva_dossier(d, CARTELLA_DOSSIER)
        print(f"  salvato: {j.name} + {m.name} in {j.parent}")
    return d


async def cmd_filmografia(a):
    _scegli_film(a.regista, a.film)


async def cmd_dossier(a):
    await _dossier(a.regista, a.film)


async def cmd_dibatti(a):
    from debate_club.orchestrazione import dibatti
    from debate_club.tools import manda_push

    d = await _dossier(a.regista, a.film, riusa=not a.rifai)
    print(f"\n== il Debate Club discute (max {a.round} turni, il Moderatore decide) ==\n")
    t = await dibatti(d, max_rounds=a.round)
    for i in t.interventi:
        print(f"[round {i.round}] {i.oratore}:\n{i.testo}\n")
    print(f"== fine: {len(t.interventi)} interventi, "
          f"{len(t.per_oratore('Fan'))} del Fan, {len(t.per_oratore('Critico'))} del Critico ==")

    if a.push:
        # Nota: `manda_push`, la funzione pura, NON il tool. Qui non c'e' niente da
        # decidere: e' un fatto del programma, non un giudizio dell'agente. Un dibattito
        # dura minuti, quindi la push e' la **consegna** del risultato a chi si e'
        # allontanato, non un avviso di "processo terminato".
        esito = manda_push(t.per_notifica(), titolo=f"Debate Club: {d.titolo}")
        print(f"   push: {esito}")


def cmd_devui(a):
    """Apre DevUI e ti lascia fare tutto da li'.

    Nota: questa e' **sincrona**, a differenza degli altri comandi. `serve()` avvia un
    server uvicorn, che fa girare un event loop suo: chiamarla da dentro `asyncio.run()`
    esplode con "asyncio.run() cannot be called from a running event loop". Per questo
    `main()` la chiama direttamente invece di passare da `asyncio.run`.

    Qui **non si tocca nessun dossier salvato**: il riuso di `progetto/dossier/` vale solo
    per i comandi `dossier` e `dibatti` (vedi `_dossier(..., riusa=...)`). In DevUI il
    Ricercatore rifa' la ricerca ogni volta, perche' e' un partecipante della group chat e
    non un passo di codice.

    Il workflow servito e' quello **completo**: il Ricercatore e' al tavolo insieme a Fan e
    Critico, quindi da DevUI parte tutto, ricerca compresa. Il terminale serve solo a
    lanciare il server e a darti l'input da incollare.

    Nella sidebar ci sono anche i quattro agenti singoli, per interrogarne uno per conto
    suo e vedere come reagisce.
    """
    from agent_framework.devui import serve

    from debate_club.agenti import crea_critico, crea_fan, crea_moderatore, crea_ricercatore
    from debate_club.orchestrazione import debate_club_completo

    entita = [
        # Tetto ALTO di proposito: e' la rete di sicurezza anti-loop, non il modo di
        # decidere la durata. La durata la scrive chi lancia ("fate due round") e la
        # rispetta il Moderatore. Se scatta il tetto, vuol dire che non ha chiuso lui.
        debate_club_completo(max_rounds=a.round * 3),
        crea_ricercatore(),
        crea_fan(),
        crea_critico(),
        crea_moderatore(),
    ]

    # Nessun regista, nessun film, nessuna chiamata a Wikipedia prima di partire:
    # il film lo decidi nel form di DevUI e il Ricercatore si cerca da solo filmografia
    # e URL. Il terminale serve solo ad accendere il server.
    print(f"\n== DevUI su http://{a.host}:{a.porta} ==")
    print("   sidebar: 'Debate Club (ricerca + dibattito)' + i quattro agenti singoli")
    print("\n   Premi 'Configure & Run'. Il form che si apre ha SEI campi perche' DevUI lo")
    print("   genera dallo schema interno di Message: te ne servono DUE.")
    print("\n     role      ->  user")
    print("     contents  ->  la scheda della sessione (testo normale), per esempio:\n")
    print('                   Film: The Village (2004), regia di M. Night Shyamalan.')
    print(f"                   Motion: {MOTION_DEFAULT}")
    print("                   Durata: 2 round a testa.")
    print("\n   Scrivilo come una SCHEDA, non come un ordine. In una group chat il messaggio")
    print("   lo leggono tutti i partecipanti, e un imperativo al plurale ('dibattete su...,")
    print("   fate 2 round a testa') viene preso da ciascuno come il proprio compito: il")
    print("   Ricercatore si mette a scrivere un dibattito invece del dossier.")
    print("\n   Gli altri quattro (author_name, message_id, additional_properties,")
    print("   raw_representation) vanno lasciati VUOTI. In particolare author_name:")
    print("   la funzione che conta i round riconosce il tuo messaggio proprio dal fatto")
    print("   che non ha un autore, quindi se lo riempi il numero di round viene ignorato")
    print("   e si torna al default.")
    print("\n   UN DIBATTITO PER AVVIO. Finito un dibattito, 'Run Again' si chiude subito: la")
    print("   group chat non azzera la conversazione tra un run e l'altro (limite di")
    print("   agent-framework-orchestrations 1.3.0) e DevUI riusa lo stesso workflow. Per un altro")
    print("   dibattito: Ctrl+C e rilancia, ci vogliono due secondi.")
    print("\n   (il film cambialo scrivendone un altro: nessun argomento da passare qui)")
    print("   (il numero di round NON e' un'istruzione al Moderatore: una funzione")
    print("    lo legge dal messaggio e ferma il dibattito esattamente li')")

    # DevUI si rifiuta di esporsi in rete senza autenticazione ("DevUI authentication cannot
    # be disabled for non-loopback hosts"): su loopback niente token, altrimenti serve.
    loopback = a.host in ("127.0.0.1", "localhost", "::1")
    token = None
    if not loopback:
        token = os.environ.get("DEVUI_AUTH_TOKEN") or secrets.token_urlsafe(16)
        print(f"\n   host non-loopback: DevUI richiede autenticazione. Token: {token}")
        print("   (se lavori via SSH e' piu' semplice il tunnel, vedi sotto)")
    else:
        print(f"\n   se sei collegata via SSH, il browser sul tuo computer non vede il")
        print(f"   127.0.0.1 di QUESTA macchina. Apri un tunnel dal tuo computer:")
        print(f"     ssh -N -L {a.porta}:127.0.0.1:{a.porta} {os.environ.get('USER','utente')}@<questa-macchina>")
        print(f"   poi vai su http://127.0.0.1:{a.porta} dal tuo browser.")

    # auto_open apre il browser sulla macchina dove gira il server: inutile via SSH.
    serve(entities=entita, host=a.host, port=a.porta,
          auth_enabled=not loopback, auth_token=token,
          auto_open=loopback and not os.environ.get("SSH_CONNECTION"))


def main() -> None:
    p = argparse.ArgumentParser(prog="debate-club", description="Il Debate Club sui film.")
    sub = p.add_subparsers(dest="comando", required=True)
    for nome, aiuto, fn in (
        ("filmografia", "elenca i film di un regista", cmd_filmografia),
        ("dossier", "costruisci il dossier di un film", cmd_dossier),
        ("dibatti", "fai discutere Fan e Critico", cmd_dibatti),
        ("devui", "apri il grafo interattivo nel browser", cmd_devui),
    ):
        s = sub.add_parser(nome, help=aiuto)
        s.add_argument("regista", nargs="?", default="M. Night Shyamalan")
        s.add_argument("--film", type=int, default=1, help="quale film della filmografia (default: il primo)")
        s.add_argument("--round", type=int, default=6, help="tetto ai turni del dibattito")
        s.add_argument("--rifai", action="store_true", help="ricostruisci il dossier invece di riusare quello salvato")
        s.add_argument("--push", action="store_true", help="a fine dibattito manda l'ultima parola come notifica Pushover")
        s.add_argument("--porta", type=int, default=8080, help="porta di DevUI")
        s.add_argument("--host", default="127.0.0.1",
                       help="interfaccia su cui legare DevUI. Da remoto (SSH) usa 0.0.0.0, "
                            "altrimenti il server ascolta solo sul loopback della macchina remota")
        s.set_defaults(fn=fn)
    a = p.parse_args()
    # `devui` e' sincrona (avvia un server con il suo event loop), le altre sono async.
    if asyncio.iscoroutinefunction(a.fn):
        asyncio.run(a.fn(a))
    else:
        a.fn(a)


if __name__ == "__main__":
    main()
