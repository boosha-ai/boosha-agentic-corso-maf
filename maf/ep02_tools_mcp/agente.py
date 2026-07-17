"""EP 2 - Il Ricercatore da terminale: l'esercizio finale completo.

Mette insieme TUTTO cio' che la puntata ha introdotto:
- le classi / risposte strutturate: Film, Filmografia, Recensione, DossierFilm (Pydantic);
- tutte le funzioni-tool: cerca_filmografia, cerca_dati_film, cerca_recensioni;
- un agente (Ricercatore) che, con output strutturato, produce il DossierFilm;
- una function middleware che stampa OGNI step (quale tool, con quali argomenti, cosa torna).

Salva il dossier nella cartella dell'episodio: output_dossier.json (il contratto per EP 4)
e output_dossier.md (leggibile).

Uso:
    uv run python maf/ep02_tools_mcp/agente.py                       # regista di default
    uv run python maf/ep02_tools_mcp/agente.py "Christopher Nolan"   # scegli il regista
    uv run python maf/ep02_tools_mcp/agente.py "Christopher Nolan" 5 # e anche il film (numero)

Chiavi nel .env: OPENAI_API_KEY (obbligatoria), TAVILY_API_KEY (opzionale, per le recensioni).
"""
import os, re, sys, asyncio, pathlib
from typing import Annotated
from urllib.parse import unquote

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel
from dotenv import load_dotenv
from agent_framework import Agent, tool, function_middleware
from agent_framework.openai import OpenAIChatClient
from tavily import TavilyClient

load_dotenv()  # MAF non carica .env da solo
MODEL = "gpt-4o-mini"


# ============================================================ le classi (risposte strutturate)
class Film(BaseModel):            # una voce di filmografia
    titolo: str
    anno: int
    url: str

class Filmografia(BaseModel):     # output della discovery (la lista da cui si sceglie)
    regista: str
    film: list[Film]

class Recensione(BaseModel):      # un estratto di recensione, classificato dal Ricercatore
    fonte: str
    url: str
    sentiment: str                # "positiva" | "negativa"
    estratto: str

class DossierFilm(BaseModel):     # il dossier del film: contratto Ricercatore -> Fan/Critico (EP 4)
    titolo: str
    anno: int
    regista: str
    incasso: str
    rotten_tomatoes: str
    descrizione: str
    recensioni: list[Recensione]


# ============================================================ helper Wikipedia
_WIKI_API = "https://en.wikipedia.org/w/api.php"
_UA = {"User-Agent": "boosha-demo/0.1 (didattica)"}


def _wiki(params):
    for _ in range(2):
        try:
            r = httpx.get(_WIKI_API, params={**params, "format": "json"}, headers=_UA, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception:
            continue
    return {}


def _parse_tabella(tab):
    """(anno, titolo, url) dalle righe di una wikitable che hanno anno + link a un film."""
    out = []
    for tr in tab.select("tr"):
        celle = tr.find_all(["td", "th"])
        ym = re.search(r"\b(19|20)\d{2}\b", " ".join(c.get_text(" ", strip=True) for c in celle)) if celle else None
        if not ym:
            continue
        for c in celle:
            a = c.find("a", href=re.compile(r"^/wiki/"))
            if a and ":" not in a["href"].split("/wiki/", 1)[1]:
                out.append((int(ym.group()), a.get("title") or a.get_text(strip=True), "https://en.wikipedia.org" + a["href"]))
                break
    return out


def _film_da_sezione(html):
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
    raw = []
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
                    raw.append((int(ym.group()), a.get("title") or a.get_text(strip=True), "https://en.wikipedia.org" + a["href"]))
    return raw


def _dedup(coppie):
    film, seen = [], set()
    for anno, titolo, url in coppie:
        if titolo and titolo not in seen:
            seen.add(titolo)
            film.append(Film(titolo=titolo, anno=anno, url=url))
    return film


def _estrai_film(regista):
    """Filmografia del regista: prima la sezione della sua pagina (con sottosezioni), poi
    l'articolo dedicato '<regista> filmography' (registi prolifici come Nolan)."""
    d = _wiki({"action": "parse", "page": regista, "prop": "text", "redirects": 1})
    if "parse" not in d:
        return []
    titolo_pagina = d["parse"]["title"]
    film = _dedup(_film_da_sezione(d["parse"]["text"]["*"]))
    if film:
        return film
    d2 = _wiki({"action": "parse", "page": f"{titolo_pagina} filmography", "prop": "text", "redirects": 1})
    if "parse" in d2:
        tabs = BeautifulSoup(d2["parse"]["text"]["*"], "html.parser").select("table.wikitable")
        if tabs:
            return _dedup(_parse_tabella(tabs[0]))
    return []


# ============================================================ tutte le funzioni-tool
@tool
def cerca_filmografia(
    regista: Annotated[str, "nome del regista, es. 'M. Night Shyamalan'"],
) -> str:
    """Trova la filmografia di un regista dalla sua pagina Wikipedia (sezione Filmography).
    Restituisce, per ogni film, anno, titolo e URL (uno per riga)."""
    film = _estrai_film(regista)
    return "\n".join(f"{f.anno} | {f.titolo} | {f.url}" for f in film) or f"{regista}: nessun film trovato"


@tool
def cerca_dati_film(
    url_o_titolo: Annotated[str, "URL Wikipedia del film (dalla filmografia) o titolo esatto"],
) -> str:
    """Legge la pagina Wikipedia di un film: incasso, Rotten Tomatoes e descrizione."""
    page = unquote(url_o_titolo.rsplit("/wiki/", 1)[1]) if str(url_o_titolo).startswith("http") else url_o_titolo
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
    m = (re.search(r"Rotten Tomatoes[^.]{0,180}?(\d{1,3})%", testo)
         or re.search(r"(\d{1,3})%[^.]{0,50}Rotten Tomatoes", testo))
    rotten = f"{m.group(1)}%" if m else "n/d"

    desc = "n/d"
    for p in soup.select("p"):
        t = re.sub(r"\[\d+\]", "", p.get_text(" ", strip=True))
        if len(t) > 60:
            desc = t[:280]
            break
    return f"{data['parse'].get('title', page)}: incasso {incasso}; Rotten Tomatoes {rotten}. {desc}"


DOMINI_RECENSIONI = ["rottentomatoes.com", "metacritic.com", "rogerebert.com"]


@tool
def cerca_recensioni(
    film: Annotated[str, "titolo del film con anno, es. 'The Village 2004'"],
) -> str:
    """Recensioni da fonti di critica FIDATE (non tutto il web); il Ricercatore le classifica pos/neg."""
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return "Tavily non configurato: recensioni non cercate (aggiungi TAVILY_API_KEY al .env)."
    try:
        resp = TavilyClient(api_key=key).search(
            query=f"{film} film review", include_domains=DOMINI_RECENSIONI, max_results=6,
        )
    except Exception as e:
        return f"ricerca recensioni non riuscita: {e}"
    righe = []
    for r in resp.get("results", []):
        estratto = re.sub(r"\s+", " ", r.get("content", "") or "")[:280]
        righe.append(f"- fonte: {r.get('url', '')}\n  {estratto}")
    return "\n".join(righe) if righe else f"nessuna recensione sui domini fidati {DOMINI_RECENSIONI}"


# ============================================================ middleware: log di ogni step
def _testo_result(res):
    """Il risultato di un tool arriva come Content (o lista di Content), non come str:
    ne estraiamo il testo (text/result/output)."""
    if res is None:
        return ""
    if isinstance(res, str):
        return res
    parti = []
    for it in (res if isinstance(res, (list, tuple)) else [res]):
        for attr in ("text", "result", "output"):
            v = getattr(it, attr, None)
            if isinstance(v, str) and v:
                parti.append(v)
                break
        else:
            parti.append(str(it))
    return " ".join(parti)


@function_middleware
async def log_step(context, call_next):
    """Intercetta ogni chiamata a tool: nome + argomenti prima, risultato (troncato) dopo."""
    args = context.arguments
    if hasattr(args, "model_dump"):
        args = args.model_dump()
    print(f"  -> {context.function.name}({args})", flush=True)
    await call_next()
    res = _testo_result(context.result)
    print(f"  <- {context.function.name}: {res[:140]}{'...' if len(res) > 140 else ''}\n", flush=True)


# ============================================================ salvataggio
def dossier_to_md(d: DossierFilm) -> str:
    righe = [f"# {d.titolo} ({d.anno})", f"*Regia di {d.regista}*", "",
             f"- **Incasso**: {d.incasso}", f"- **Rotten Tomatoes**: {d.rotten_tomatoes}", "",
             "## Trama", d.descrizione, "", "## Recensioni"]
    for r in d.recensioni:
        righe.append(f"- **[{r.sentiment}]** {r.fonte}: {r.estratto}  \n  <{r.url}>")
    return "\n".join(righe) + "\n"


# ============================================================ main
async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("Manca OPENAI_API_KEY nel .env. Aggiungila e riprova.")

    regista = sys.argv[1] if len(sys.argv) > 1 else "M. Night Shyamalan"

    # 1) discovery deterministica -> un oggetto Filmografia tipizzato (le classi in azione)
    print(f"\n== 1) discovery: filmografia di {regista} (Wikipedia) ==")
    film = _estrai_film(regista)
    if not film:
        sys.exit(f"Nessuna filmografia trovata per '{regista}'.")
    filmografia = Filmografia(regista=regista, film=film)
    print(f"   ({type(filmografia).__name__} tipizzata, {len(filmografia.film)} film)")
    for i, f in enumerate(filmografia.film, 1):
        print(f"  {i:2d}. {f.anno}  {f.titolo}")

    # 2) scelta del film (mini-HITL: in EP 5 diventa un vero human-in-the-loop nel workflow)
    if len(sys.argv) > 2 and sys.argv[2].isdigit():
        idx = int(sys.argv[2]) - 1
    else:
        try:
            s = input(f"\nScegli un film (1-{len(filmografia.film)}), invio per il primo: ").strip()
            idx = int(s) - 1 if s.isdigit() else 0
        except EOFError:
            idx = 0
    idx = max(0, min(idx, len(filmografia.film) - 1))
    scelto = filmografia.film[idx]
    print(f"\n== 2) scelto: {scelto.titolo} ({scelto.anno}) ==")

    # 3) il Ricercatore costruisce il DossierFilm (output strutturato), loggando ogni step
    print("\n== 3) il Ricercatore costruisce il dossier (step in tempo reale) ==")
    ricercatore = Agent(
        client=OpenAIChatClient(model=MODEL),
        name="Ricercatore",
        instructions=(
            "Costruisci il dossier di un film per un dibattito. Usa cerca_dati_film (passa l'URL) per "
            "incasso, Rotten Tomatoes e descrizione; usa cerca_recensioni per gli estratti di critica, "
            "che classifichi in 'positiva' o 'negativa'. Non inventare dati: se mancano, scrivi 'n/d'."
        ),
        tools=[cerca_dati_film, cerca_recensioni],
        middleware=[log_step],   # <- il log di ogni tool call passa da qui
    )
    risposta = await ricercatore.run(
        f"Costruisci il dossier del film '{scelto.titolo}' (regista {regista}). URL Wikipedia: {scelto.url}.",
        options={"response_format": DossierFilm},
    )
    dossier: DossierFilm = risposta.value

    # 4) salvataggio nella cartella dell'episodio: JSON (contratto) + MD (leggibile)
    out = pathlib.Path(__file__).parent
    (out / "output_dossier.json").write_text(dossier.model_dump_json(indent=2), encoding="utf-8")
    (out / "output_dossier.md").write_text(dossier_to_md(dossier), encoding="utf-8")

    pos = sum(r.sentiment == "positiva" for r in dossier.recensioni)
    neg = sum(r.sentiment == "negativa" for r in dossier.recensioni)
    print("== 4) dossier pronto ==")
    print(f"  {dossier.titolo} ({dossier.anno}) - incasso {dossier.incasso}, RT {dossier.rotten_tomatoes}")
    print(f"  recensioni: {pos} positive / {neg} negative")
    print("  salvato in ep02: output_dossier.json (contratto) + output_dossier.md (leggibile)")


if __name__ == "__main__":
    asyncio.run(main())
