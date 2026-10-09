"""I guasti trovati provando EP 4, fissati come test. Girano senza rete e senza modello.

    uv run pytest

Ogni test e' un difetto successo davvero: il caso e' raccontato nella sua docstring.
Servono a una cosa sola: se il codice si riscrive, dicono se la versione nuova regge.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from debate_club import dossier as modulo_dossier
from debate_club.dossier import _estrai_url, aggiungi_punteggi, verifica_fonti
from debate_club.modelli import DossierFilm, Recensione
from debate_club.orchestrazione import limite_round_da_messaggio
from debate_club.tools import wikipedia as wp

DATI = Path(__file__).parent / "dati"
PROGETTO = Path(__file__).resolve().parents[1]
RADICE = Path(__file__).resolve().parents[4]  # la radice del corso: tests -> progetto -> ep04 -> maf -> radice
VILLAGE = (DATI / "critica_the_village.txt").read_text(encoding="utf-8")
LADY_BIRD = (DATI / "critica_lady_bird.txt").read_text(encoding="utf-8")
SEZIONE = "https://en.wikipedia.org/wiki/The_Village_(2004_film)#Critical_response"
EBERT = "The Village is a colossal miscalculation, a movie based on a premise that cannot support it"


def _rec(estratto: str, url: str = SEZIONE, sentiment: str = "negativa") -> Recensione:
    return Recensione(fonte="qualcuno", url=url, sentiment=sentiment, estratto=estratto)


def _dossier(*rec: Recensione) -> DossierFilm:
    return DossierFilm(
        titolo="The Village", anno=2004, regista="M. Night Shyamalan", incasso="n/d",
        rotten_tomatoes="n/d", descrizione="n/d", recensioni=list(rec),
    )


@pytest.fixture(autouse=True)
def cache_pulita():
    """La sezione critica e' in cache: tra un test e l'altro non deve restare niente."""
    wp._sezione_critica.cache_clear()
    yield
    wp._sezione_critica.cache_clear()


# ------------------------------------------------- verifica_fonti: il contratto dice il vero
def test_citazione_vera_resta():
    assert EBERT in VILLAGE  # il dato del test e' quello giusto
    tenuto, scartate = verifica_fonti(_dossier(_rec(EBERT)), {SEZIONE}, VILLAGE)
    assert len(tenuto.recensioni) == 1 and scartate == []


def test_attribuzione_inventata_esce():
    """Caso vero: il Ricercatore ha attribuito a Ebert una frase che Ebert non ha scritto."""
    falsa = "Roger Ebert ha elogiato il film per la sua profonda riflessione su come le societa' costruiscano le loro paure."
    tenuto, scartate = verifica_fonti(_dossier(_rec(falsa)), {SEZIONE}, VILLAGE)
    assert tenuto.recensioni == [] and len(scartate) == 1


def test_parafrasi_esce():
    tenuto, _ = verifica_fonti(_dossier(_rec("Ebert thought the film was bad and gave it a low score.")), {SEZIONE}, VILLAGE)
    assert tenuto.recensioni == []


def test_url_inventato_esce_anche_con_citazione_vera():
    """Caso vero: `rottentomatoes.com/m/negative`, la parola presa dalla query di ricerca."""
    tenuto, _ = verifica_fonti(_dossier(_rec(EBERT, url="https://www.rottentomatoes.com/m/negative")), {SEZIONE}, VILLAGE)
    assert tenuto.recensioni == []


def test_virgolette_e_spazi_non_contano():
    """Una citazione copiata bene non deve cadere per un apostrofo curvo o uno spazio doppio."""
    copiata = "appropriately  creepy, but Shyamalan’s signature twist ending disappoints"
    tenuto, _ = verifica_fonti(_dossier(_rec(copiata)), {SEZIONE}, VILLAGE)
    assert len(tenuto.recensioni) == 1


def test_citazione_troppo_corta_esce():
    """'The Village' compare nel testo, ma non e' una citazione: e' un titolo."""
    tenuto, _ = verifica_fonti(_dossier(_rec("The Village")), {SEZIONE}, VILLAGE)
    assert tenuto.recensioni == []


def test_senza_testi_si_controlla_solo_url():
    tenuto, _ = verifica_fonti(_dossier(_rec("qualunque cosa")), {SEZIONE})
    assert len(tenuto.recensioni) == 1


# ------------------------------------------------- URL: le parentesi di Wikipedia
def test_url_con_parentesi_resta_intero():
    """Caso vero: la prima regex si fermava a `(` e troncava gli URL di Wikipedia."""
    assert _estrai_url(f"vedi {SEZIONE}.") == [SEZIONE]


def test_parentesi_della_frase_si_toglie():
    assert _estrai_url(f"(fonte: {SEZIONE})") == [SEZIONE]


# ------------------------------------------------- punteggi: li estrae il codice
def test_punteggi_the_village():
    rt, mc, cs, consenso = wp._punteggi(VILLAGE)
    assert rt == "43% (220 recensioni, media 5.4/10)"
    assert mc == "44/100 (40 critici)"
    assert cs == "C"
    assert consenso == "The Village is appropriately creepy, but Shyamalan's signature twist ending disappoints."


def test_punteggio_assente_resta_nd():
    """Lady Bird non ha il CinemaScore nella sezione: n/d, non un valore inventato."""
    rt, mc, cs, _ = wp._punteggi(LADY_BIRD)
    assert rt.startswith("99%") and mc.startswith("93/100") and cs == "n/d"


def test_pagina_senza_sezione_critica(monkeypatch):
    """Caso vero: Hospital (1970) non ha la sezione. Niente recensioni, invece di recensioni di altri film."""
    monkeypatch.setattr(wp, "_wiki", lambda params, **kw: {
        "parse": {"title": "Hospital (1970 film)", "sections": [{"line": "Synopsis", "index": "1"}]}
    })
    assert wp.critica_film("https://en.wikipedia.org/wiki/Hospital_(1970_film)") is None


def test_user_agent_secondo_la_policy_wikimedia():
    """Formato richiesto: `<nome>/<versione> (<contatto>) <libreria>/<versione>`."""
    import re
    ua = wp._UA["User-Agent"]
    assert re.fullmatch(r"\S+Bot/[\d.]+ \(https://\S+\) httpx/[\d.]+", ua), ua


# ------------------------------------------------- Wikipedia giu' (429): niente si perde
def _wikipedia_giu(params, **kw):
    raise wp.WikipediaNonRaggiungibile("simulato: 429 Too Many Requests")


def test_tool_con_wikipedia_giu_risponde_riprova(monkeypatch):
    monkeypatch.setattr(wp, "_wiki", _wikipedia_giu)
    assert wp.cerca_critica_film.func(SEZIONE).startswith("non sono riuscito a interrogare Wikipedia")


def test_funzione_pura_con_wikipedia_giu_segnala_il_guasto(monkeypatch):
    """Un guasto di rete non deve sembrare 'la sezione non c'e'' (None)."""
    monkeypatch.setattr(wp, "_wiki", _wikipedia_giu)
    with pytest.raises(wp.WikipediaNonRaggiungibile):
        wp.critica_film(SEZIONE)


def test_dossier_non_si_perde_se_wikipedia_cade_alla_fine(monkeypatch):
    """Il dossier l'ha gia' costruito (e pagato) il modello: con Wikipedia giu' si tiene."""
    def giu(url):
        raise wp.WikipediaNonRaggiungibile("simulato")
    monkeypatch.setattr(modulo_dossier, "critica_film", giu)
    d = aggiungi_punteggi(_dossier(_rec(EBERT)), SEZIONE)
    assert len(d.recensioni) == 1 and d.metacritic == "n/d"


# ------------------------------------------------- il contratto
def test_sentiment_al_maschile_rifiutato():
    """Caso vero: il modello ha scritto 'positivo' e i conteggi sono tornati zero."""
    with pytest.raises(ValidationError):
        _rec(EBERT, sentiment="positivo")


@pytest.mark.parametrize("percorso", sorted(
    p for cartella in (PROGETTO / "dossier", RADICE / "maf/ep03_memoria_stato/dossier",
                       RADICE / "maf/ep06_valutazione/prove")
    for p in cartella.glob("*.json")
), ids=lambda p: p.name)
def test_dossier_salvati_si_caricano_ancora(percorso):
    """I campi nuovi hanno un default: un dossier vecchio (anche di EP 3) si carica ancora."""
    DossierFilm(**json.loads(percorso.read_text(encoding="utf-8")))


# ------------------------------------------------- il limite dei round letto dal messaggio
class _M:
    def __init__(self, text, author_name=None):
        self.text, self.author_name = text, author_name


def _conversazione(iniziale, turni, autore_iniziale=None):
    return [_M(iniziale, autore_iniziale)] + [_M("x", "Fan" if i % 2 == 0 else "Critico") for i in range(turni)]


def test_round_dalla_scheda():
    scheda = "Film: The Village (2004).\nDurata: 2 round a testa."
    assert not limite_round_da_messaggio(_conversazione(scheda, 3))
    assert limite_round_da_messaggio(_conversazione(scheda, 4))


def test_senza_numero_vale_il_default():
    assert not limite_round_da_messaggio(_conversazione("Film: The Village.", 5))
    assert limite_round_da_messaggio(_conversazione("Film: The Village.", 6))


def test_author_name_riempito_fa_ignorare_il_numero():
    """La trappola del form di DevUI: con un autore il messaggio non e' piu' 'quello umano'."""
    conv = _conversazione("Durata: 2 round a testa.", 4, autore_iniziale="Veronica")
    assert not limite_round_da_messaggio(conv)  # ignorato il 2: si torna al default di 3


# ------------------------------------------------- i prompt non si contraddicono
def test_il_carattere_del_moderatore_non_decide_l_apertura():
    """Caso vero: `moderatore.md` diceva "apri col Fan" e un'aggiunta per il tavolo col
    Ricercatore lo smentiva; il modello ha seguito la prima e il Ricercatore non ha mai
    parlato. Ora il carattere non dice chi apre: lo dice solo l'apertura."""
    from debate_club.istruzioni import carica
    assert "apri" not in carica("moderatore").lower()
    assert "Ricercatore" in carica("apertura_con_ricerca")
    assert "Ricercatore" not in carica("apertura_dibattito")


# ------------------------------------------------- il doppio turno di MAF
def test_turno_di_fila_inietta_il_promemoria_solo_a_zero_messaggi():
    """Caso vero: con lo stesso oratore due volte di fila MAF gli passa zero messaggi e
    OpenAI rifiuta la richiesta ("Messages are required"). Riprodotto forzando l'ordine."""
    import asyncio
    from types import SimpleNamespace

    from agent_framework import Message
    from debate_club.middleware import PROMEMORIA_TURNO, turno_di_fila

    async def prova(messaggi):
        chiamato = []
        ctx = SimpleNamespace(messages=list(messaggi))
        async def avanti():
            chiamato.append(True)
        await turno_di_fila(ctx, avanti)
        return ctx.messages, chiamato

    vuoto, chiamato = asyncio.run(prova([]))
    assert chiamato and len(vuoto) == 1 and PROMEMORIA_TURNO in vuoto[0].text
    pieno = [Message(role="user", contents=["ciao"])]
    risultato, chiamato = asyncio.run(prova(pieno))
    assert chiamato and [m.text for m in risultato] == ["ciao"]  # niente da aggiungere


def test_ogni_partecipante_ha_la_protezione(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-finta-per-il-test")
    from debate_club.agenti import crea_critico, crea_fan, crea_ricercatore
    from debate_club.middleware import turno_di_fila
    for agente in (crea_fan(), crea_critico(), crea_ricercatore(), crea_ricercatore(verboso=True)):
        assert turno_di_fila in (agente.middleware or []), agente.name


# ------------------------------------------------- tetto alle chiamate
def test_tetto_alle_chiamate_solo_sul_ricercatore(monkeypatch):
    """Caso vero: ~40 chiamate identiche a uno strumento. Il tetto e' per istanza."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-finta-per-il-test")
    from debate_club.agenti import crea_fan, crea_ricercatore
    assert crea_ricercatore().client.function_invocation_configuration["max_function_calls"] == 4
    assert crea_fan().client.function_invocation_configuration.get("max_function_calls") is None
