"""Tool su Wikipedia: la filmografia di un regista, i dati di un film e la sua critica.

Due livelli, di proposito:
- le funzioni pure (`filmografia`, `dati_film`) tornano dati tipizzati e le chiami tu;
- i @tool (`cerca_filmografia`, `cerca_dati_film`) sono le stesse cose in una forma che
  l'LLM sa usare, cioe' con una docstring che le descrive e stringhe in uscita.

La discovery e' deterministica: la fa il codice, non il modello. Il modello sceglie
*quando* servirsene, non *come* leggere una tabella HTML.
"""

import re
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated
from urllib.parse import unquote

import httpx
from agent_framework import tool
from bs4 import BeautifulSoup

from debate_club.modelli import Film, Filmografia

_WIKI_API = "https://en.wikipedia.org/w/api.php"
# Il formato che chiede la User-Agent Policy di Wikimedia: nome/versione, un contatto, la
# libreria. Senza contatto "may be blocked without notice", e con le raffiche si prende
# prima il 429. Il contatto e' la repo pubblica del corso, non un indirizzo personale.
_UA = {
    "User-Agent": (
        "BooshaDebateClubBot/0.1 (https://github.com/boosha-ai/boosha-agentic-corso-maf) "
        f"httpx/{httpx.__version__}"
    )
}


class WikipediaNonRaggiungibile(RuntimeError):
    """La richiesta a Wikipedia non e' riuscita (rete, timeout, throttling).

    Esiste per NON confondere due cose diverse: "questo regista non ha una filmografia
    leggibile" e "non sono riuscito a chiedere". Prima il codice restituiva una lista
    vuota in entrambi i casi, e un intoppo di rete sembrava un regista non supportato.
    Succede davvero: con una raffica di richieste ravvicinate Wikipedia rallenta, e i
    registi che un attimo prima funzionavano tornano zero film.
    """


def _wiki(params: dict, *, tentativi: int = 3) -> dict:
    ultimo = None
    for n in range(tentativi):
        try:
            r = httpx.get(_WIKI_API, params={**params, "format": "json"}, headers=_UA, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # rete, timeout, 429...
            ultimo = e
            if n < tentativi - 1:
                time.sleep(0.6 * (n + 1))  # un attimo di respiro, poi riprova
    raise WikipediaNonRaggiungibile(
        f"Wikipedia non risponde dopo {tentativi} tentativi ({type(ultimo).__name__}: {ultimo})"
    )


def _parse_tabella(tab) -> list[tuple[int, str, str]]:
    """(anno, titolo, url) dalle righe di una wikitable che hanno anno + link a un film."""
    out = []
    for tr in tab.select("tr"):
        celle = tr.find_all(["td", "th"])
        ym = (
            re.search(r"\b(19|20)\d{2}\b", " ".join(c.get_text(" ", strip=True) for c in celle))
            if celle
            else None
        )
        if not ym:
            continue
        for c in celle:
            a = c.find("a", href=re.compile(r"^/wiki/"))
            if a and ":" not in a["href"].split("/wiki/", 1)[1]:
                out.append(
                    (
                        int(ym.group()),
                        a.get("title") or a.get_text(strip=True),
                        "https://en.wikipedia.org" + a["href"],
                    )
                )
                break
    return out


def _film_da_sezione(html: str) -> list[tuple[int, str, str]]:
    """Dall'intestazione Filmography raccoglie i film fino alla successiva h2 (prende anche le
    sottosezioni, es. Film/Television). Prima le wikitable; in mancanza, le liste (<li>)."""
    soup = BeautifulSoup(html, "html.parser")
    heading = None
    for h in soup.find_all(["h2", "h3"]):
        span = h.find("span", class_="mw-headline")
        hid = ((span.get("id") if span else h.get("id")) or "").lower()
        txt = h.get_text(" ", strip=True).lower()
        if "filmograph" in txt or "feature film" in txt or hid in ("filmography", "feature_films"):
            heading = h
            break
    if not heading:
        return []
    raw: list[tuple[int, str, str]] = []
    for el in heading.find_all_next():
        if el.name == "h2":
            break
        if el.name == "table" and "wikitable" in (el.get("class") or []):
            raw += _parse_tabella(el)
    if not raw:  # filmografia in lista invece che in tabella
        for el in heading.find_all_next():
            if el.name == "h2":
                break
            if el.name == "li":
                ym = re.search(r"\b(19|20)\d{2}\b", el.get_text(" ", strip=True))
                a = el.find("a", href=re.compile(r"^/wiki/"))
                if ym and a and ":" not in a["href"].split("/wiki/", 1)[1]:
                    raw.append(
                        (
                            int(ym.group()),
                            a.get("title") or a.get_text(strip=True),
                            "https://en.wikipedia.org" + a["href"],
                        )
                    )
    return raw


def _dedup(coppie: list[tuple[int, str, str]]) -> list[Film]:
    film, visti = [], set()
    for anno, titolo, url in coppie:
        if titolo and titolo not in visti:
            visti.add(titolo)
            film.append(Film(titolo=titolo, anno=anno, url=url))
    return film


# ---------------------------------------------------------------- funzioni pure
def filmografia(regista: str) -> Filmografia:
    """La filmografia del regista, tipizzata. Prima prova la sezione della sua pagina
    (sottosezioni comprese), poi l'articolo dedicato '<regista> filmography', che esiste
    per i registi prolifici come Nolan.

    E' la funzione che chiami tu quando ti serve la lista da cui scegliere: in EP 5 e'
    l'input della scelta umana.
    """
    d = _wiki({"action": "parse", "page": regista, "prop": "text", "redirects": 1})
    if "parse" not in d:
        return Filmografia(regista=regista, film=[])
    titolo_pagina = d["parse"]["title"]
    film = _dedup(_film_da_sezione(d["parse"]["text"]["*"]))
    if not film:
        d2 = _wiki(
            {"action": "parse", "page": f"{titolo_pagina} filmography", "prop": "text", "redirects": 1}
        )
        if "parse" in d2:
            tabs = BeautifulSoup(d2["parse"]["text"]["*"], "html.parser").select("table.wikitable")
            if tabs:
                film = _dedup(_parse_tabella(tabs[0]))
    return Filmografia(regista=regista, film=film)


def dati_film(url_o_titolo: str) -> str:
    """Incasso, Rotten Tomatoes e descrizione dalla pagina Wikipedia di un film.

    Accetta l'URL, non il titolo: e' l'URL che arriva dalla filmografia, e passarlo evita
    una ricerca per nome che sugli omonimi sbaglia film.
    """
    page = (
        unquote(url_o_titolo.rsplit("/wiki/", 1)[1])
        if str(url_o_titolo).startswith("http")
        else url_o_titolo
    )
    data = _wiki({"action": "parse", "page": page, "prop": "text", "redirects": 1})
    if "parse" not in data:
        return f"{page}: pagina non leggibile"
    soup = BeautifulSoup(data["parse"]["text"]["*"], "html.parser")

    incasso = "n/d"
    for th in soup.select("table.infobox th"):
        if "box office" in th.get_text(strip=True).lower():
            td = th.find_next("td")
            if td:
                incasso = re.sub(r"\s+", " ", td.get_text(" ", strip=True)).split("[")[0].strip()
            break

    testo = soup.get_text(" ", strip=True)
    m = re.search(r"Rotten Tomatoes[^.]{0,180}?(\d{1,3})%", testo) or re.search(
        r"(\d{1,3})%[^.]{0,50}Rotten Tomatoes", testo
    )
    rotten = f"{m.group(1)}%" if m else "n/d"

    desc = "n/d"
    for p in soup.select("p"):
        t = re.sub(r"\[\d+\]", "", p.get_text(" ", strip=True))
        if len(t) > 60:
            desc = t[:280]
            break
    return f"{data['parse'].get('title', page)}: incasso {incasso}; Rotten Tomatoes {rotten}. {desc}"


@dataclass(frozen=True)
class CriticaFilm:
    """La sezione sulla critica di un film, gia' smontata: i dati da una parte, il testo
    dall'altra. I dati li estrae il codice; il testo e' quello da cui il Ricercatore sceglie
    le citazioni, e contro cui `verifica_fonti` controlla che le abbia copiate davvero."""

    url_sezione: str
    rotten_tomatoes: str
    metacritic: str
    cinemascore: str
    consenso: str
    testo: str


_SEZIONE_CRITICA = re.compile(r"critical (response|reception)", re.IGNORECASE)
_LIMITE_TESTO = 6000  # la sezione di Get Out supera i 9000 caratteri: al modello ne bastano meno


def _pagina(url_o_titolo: str) -> str:
    return (
        unquote(url_o_titolo.rsplit("/wiki/", 1)[1].split("#", 1)[0])
        if str(url_o_titolo).startswith("http")
        else url_o_titolo
    )


@lru_cache(maxsize=64)
def _sezione_critica(pagina: str) -> tuple[str, str, str] | None:
    """(titolo della pagina, ancora della sezione, testo) o None se la sezione non c'e'.

    In cache perche' la stessa pagina la leggono due volte in un dossier: il Ricercatore
    tramite il tool, e il codice per i punteggi. Due richieste in meno a Wikipedia, che
    con le raffiche risponde 429 (vedi `WikipediaNonRaggiungibile`).
    """
    d = _wiki({"action": "parse", "page": pagina, "prop": "sections", "redirects": 1})
    if "parse" not in d:
        return None
    sezioni = d["parse"]["sections"]
    s = next((s for s in sezioni if _SEZIONE_CRITICA.search(s["line"])), None) or next(
        (s for s in sezioni if s["line"].strip().lower() == "reception"), None
    )
    if s is None:
        return None
    d2 = _wiki({"action": "parse", "page": pagina, "prop": "text", "section": s["index"], "redirects": 1})
    soup = BeautifulSoup(d2["parse"]["text"]["*"], "html.parser")
    # get_text() SENZA separatore: con " " i tag in linea (il titolo in corsivo) si
    # staccano dal resto ("Split 's") e la citazione nel testo non e' piu' quella vera.
    paragrafi = [re.sub(r"\[\s*(?:\d+|[a-z])\s*\]", "", p.get_text()).strip() for p in soup.select("p")]
    testo = re.sub(r"[ \t]+", " ", "\n".join(p for p in paragrafi if p))
    return d["parse"]["title"], s.get("anchor") or s["line"].replace(" ", "_"), testo


def _da(testo: str, chiave: str, frasi: int = 1) -> str:
    """La frase che nomina `chiave`, piu' le successive: i dati di Rotten Tomatoes a volte
    stanno su due frasi ("...43% of 220 reviews. The average rating is 5.4/10.")."""
    parti = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", testo)
    for i, f in enumerate(parti):
        if chiave.lower() in f.lower():
            return " ".join(parti[i : i + frasi])
    return ""


def _punteggi(testo: str) -> tuple[str, str, str, str]:
    """Rotten Tomatoes, Metacritic, CinemaScore, consenso: tutto `n/d` dove non si trova."""
    s = _da(testo, "Rotten Tomatoes", 2)
    pct = re.search(r"(\d{1,3})\s?%", s)
    n = re.search(r"(\d[\d,]*)\s+(?:critics'?\s+)?reviews", s)
    media = re.search(r"average (?:rating|score) (?:of|is) ([\d.]+)(?:/| out of )10", s)
    rt = "n/d"
    if pct:
        extra = ", ".join(x for x in (f"{n.group(1)} recensioni" if n else "", f"media {media.group(1)}/10" if media else "") if x)
        rt = f"{pct.group(1)}%" + (f" ({extra})" if extra else "")

    s = _da(testo, "Metacritic")
    voto = re.search(r"(\d{1,3}) out of 100", s) or re.search(r"score of (\d{1,3})", s)
    n = re.search(r"(\d+) (?:critics|reviews)", s)
    mc = f"{voto.group(1)}/100" + (f" ({n.group(1)} critici)" if n else "") if voto else "n/d"

    s = _da(testo, "CinemaScore")
    g = re.search(r"grade of\s*[\"“]?\s*([A-F][+\-−–]?)", s)
    cs = g.group(1).replace("−", "-").replace("–", "-") if g else "n/d"

    c = re.search(r"consensus (?:reads|states|says)[:,]?\s*[\"“]\s*(.+?)\s*[\"”]", testo)
    return rt, mc, cs, (c.group(1) if c else "n/d")


def critica_film(url_o_titolo: str) -> CriticaFilm | None:
    """La critica di un film dalla sua pagina Wikipedia, sezione "Critical response".

    Si entra **per URL**, come in `dati_film`: il film e' quello giusto per costruzione, e
    la sezione riporta giudizi di critici con nome e testata. Una ricerca web per nome
    invece prende gli omonimi, e il suo estratto e' spesso la trama o il menu del sito.

    None se la pagina non ha una sezione sulla critica (succede sui film poco noti, per
    esempio *Hospital* di Wiseman): in quel caso il dossier resta senza recensioni.
    """
    trovata = _sezione_critica(_pagina(url_o_titolo))
    if trovata is None:
        return None
    titolo, ancora, testo = trovata
    rt, mc, cs, consenso = _punteggi(testo)
    return CriticaFilm(
        url_sezione=f"https://en.wikipedia.org/wiki/{titolo.replace(' ', '_')}#{ancora}",
        rotten_tomatoes=rt,
        metacritic=mc,
        cinemascore=cs,
        consenso=consenso,
        testo=testo[:_LIMITE_TESTO],
    )


# ---------------------------------------------------------------- gli stessi, come tool
@tool
def cerca_filmografia(
    regista: Annotated[str, "nome del regista, es. 'M. Night Shyamalan'"],
) -> str:
    """Trova la filmografia di un regista dalla sua pagina Wikipedia (sezione Filmography).
    Restituisce, per ogni film, anno, titolo e URL (uno per riga)."""
    try:
        f = filmografia(regista)
    except WikipediaNonRaggiungibile as e:
        # Distinzione importante per l'agente: non e' "non esiste", e' "non ho potuto
        # chiedere". Cosi' puo' riprovare invece di dare per buono un buco.
        return f"non sono riuscito a interrogare Wikipedia: {e}. Riprova."
    return "\n".join(f"{x.anno} | {x.titolo} | {x.url}" for x in f.film) or (
        f"{regista}: nessun film trovato nella sezione Filmography della sua pagina"
    )


@tool
def cerca_dati_film(
    url_o_titolo: Annotated[str, "URL Wikipedia del film (dalla filmografia) o titolo esatto"],
) -> str:
    """Legge la pagina Wikipedia di un film: incasso, Rotten Tomatoes e descrizione."""
    try:
        return dati_film(url_o_titolo)
    except WikipediaNonRaggiungibile as e:
        return f"non sono riuscito a interrogare Wikipedia: {e}. Riprova."


@tool
def cerca_critica_film(
    url: Annotated[str, "URL Wikipedia del film, lo stesso passato a cerca_dati_film"],
) -> str:
    """La critica di un film: la sezione "Critical response" della sua pagina Wikipedia.

    Restituisce i punteggi aggregati e il testo della sezione, con le citazioni dei critici
    per nome e testata. Le citazioni vanno copiate da questo testo, identiche e in lingua
    originale: una citazione che non compare qui viene tolta dal dossier."""
    try:
        c = critica_film(url)
    except WikipediaNonRaggiungibile as e:
        return f"non sono riuscito a interrogare Wikipedia: {e}. Riprova."
    if c is None:
        return (
            f"{_pagina(url)}: la pagina non ha una sezione sulla critica. "
            "Lascia le recensioni vuote: non cercarne altrove e non inventarle."
        )
    return (
        f"Critica dalla sezione Wikipedia: {c.url_sezione}\n"
        f"- Rotten Tomatoes: {c.rotten_tomatoes}\n"
        f"- Metacritic: {c.metacritic}\n"
        f"- CinemaScore: {c.cinemascore}\n"
        f"- consenso della critica: {c.consenso}\n\n"
        "Testo della sezione (le citazioni dei critici vanno copiate da qui, identiche):\n"
        f"{c.testo}"
    )
