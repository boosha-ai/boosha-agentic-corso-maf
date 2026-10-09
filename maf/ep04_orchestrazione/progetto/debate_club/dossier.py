"""Dalla scelta di un film al dossier: il lavoro del Ricercatore, in una funzione.

E' il ponte tra EP 2 e EP 4. La discovery della filmografia resta deterministica (la fa
`tools.filmografia`, non il modello); qui invece serve un agente, perche' classificare
una recensione come positiva o negativa e' un giudizio, non un parsing.
"""

import json
import re
from pathlib import Path

from agent_framework import function_middleware

from debate_club.agenti import crea_ricercatore
from debate_club.middleware import _testo_result
from debate_club.modelli import DossierFilm, Film, Recensione
from debate_club.tools import critica_film
from debate_club.tools.wikipedia import WikipediaNonRaggiungibile


def _estrai_url(testo: str) -> list[str]:
    """Gli URL in un testo. Le parentesi vanno tenute: gli indirizzi di Wikipedia ne sono
    pieni (`The_Village_(2004_film)`), e tagliarle scarterebbe a torto la fonte. Si toglie
    solo una parentesi di chiusura che non ha la sua apertura, cioe' quella della frase."""
    fuori = []
    for u in re.findall(r"https?://[^\s<>\"']+", testo):
        u = u.rstrip(".,;:")
        while u.endswith(")") and u.count(")") > u.count("("):
            u = u[:-1]
        fuori.append(u)
    return fuori


def _norma(url: str) -> str:
    """Due scritture dello stesso indirizzo devono combaciare (http/https, slash finale)."""
    u = url.strip().rstrip(".,;:").rstrip("/")
    return "https://" + u[len("http://"):] if u.startswith("http://") else u


def _solo_lettere(t: str) -> str:
    """Il testo ridotto a lettere e cifre: virgolette dritte o curve, trattini, spazi e
    maiuscole non devono far fallire il confronto di una citazione copiata bene."""
    return re.sub(r"[^a-z0-9]", "", t.lower())


def verifica_fonti(
    dossier: DossierFilm,
    url_visti: set[str],
    testi_visti: str | None = None,
) -> tuple[DossierFilm, list[Recensione]]:
    """Tiene solo le recensioni che i tool hanno davvero restituito. Funzione pura.

    Perche' esiste. `response_format=DossierFilm` garantisce la **forma** del contratto,
    non la sua **verita'**: Pydantic accetta qualunque stringa nei campi, e un modello a
    volte non copia, compone (un URL che non esiste, una frase attribuita a un critico che
    non l'ha scritta). I casi veri sono in `progetto/tests/`.

    Il controllo non chiede niente al modello, confronta e basta:
    - l'**URL** deve essere uscito da un tool in quel run;
    - se si passa `testi_visti`, anche la **citazione** deve comparire, parola per parola,
      nel testo che i tool hanno restituito. Una citazione inventata o parafrasata esce.

    Cosa NON garantisce: che il Ricercatore abbia scelto bene, ne' che il sentiment sia
    giusto. Quelli sono giudizi, e se ne occupa EP 6.
    """
    visti = {_norma(u) for u in url_visti}
    corpus = _solo_lettere(testi_visti) if testi_visti is not None else None

    def regge(r: Recensione) -> bool:
        if _norma(r.url) not in visti:
            return False
        if corpus is None:
            return True
        citazione = _solo_lettere(r.estratto)
        return len(citazione) >= 20 and citazione in corpus

    tenute = [r for r in dossier.recensioni if regge(r)]
    scartate = [r for r in dossier.recensioni if not regge(r)]
    return dossier.model_copy(update={"recensioni": tenute}), scartate


async def costruisci_dossier(film: Film, regista: str, *, verboso: bool = False) -> DossierFilm:
    """Il dossier del film, prodotto dal Ricercatore con output strutturato e **verificato**.

    `response_format` non e' un vezzo: e' cio' che trasforma una risposta in un contratto.
    Senza, il turno successivo dovrebbe interpretare del testo libero. Ma la forma non
    basta: dopo il run, `verifica_fonti` toglie le recensioni con un URL che nessun tool
    ha restituito.

    Quello che i tool restituiscono si raccoglie con un middleware passato **a questo run
    soltanto** (`run()` lo somma a quello dell'agente, quindi `log_step` continua a
    stampare): niente stato globale, e due dossier costruiti uno dopo l'altro non si
    mescolano.

    E i punteggi aggregati (Rotten Tomatoes, Metacritic, CinemaScore, consenso) li scrive
    il **codice**, alla fine, dalla stessa sezione Wikipedia: sono dati, e un dato che si
    estrae col codice non si fa ricopiare a un LLM.
    """
    url_visti: set[str] = {film.url}
    testi: list[str] = []

    @function_middleware
    async def raccogli(context, call_next):
        await call_next()
        testo = _testo_result(context.result)
        testi.append(testo)
        url_visti.update(_estrai_url(testo))

    # Senza `cerca_filmografia`: il film l'ha gia' scelto il codice, e l'URL arriva nel
    # messaggio. Con lo strumento in mano il Ricercatore lo richiamava comunque (quattro
    # volte in un run), e ogni chiamata e' una richiesta a Wikipedia in piu'.
    ricercatore = crea_ricercatore(verboso=verboso, con_filmografia=False)
    risposta = await ricercatore.run(
        f"Costruisci il dossier del film '{film.titolo}' ({film.anno}, regista {regista}). "
        f"URL Wikipedia: {film.url}.",
        options={"response_format": DossierFilm},
        middleware=[raccogli],
    )
    dossier, scartate = verifica_fonti(risposta.value, url_visti, "\n".join(testi))
    for r in scartate:
        print(f"  !! fonte scartata, non restituita da nessun tool: {r.fonte}: {r.estratto[:70]!r}", flush=True)

    return aggiungi_punteggi(dossier, film.url)


def aggiungi_punteggi(dossier: DossierFilm, url: str) -> DossierFilm:
    """Scrive nel dossier i punteggi aggregati della critica, estratti dal codice.

    Se Wikipedia non risponde (429 dopo una raffica, rete giu') il dossier **non si perde**:
    il modello l'ha gia' costruito e pagato, quindi si tiene com'e', con i punteggi a `n/d`,
    e lo si dice. Di solito la pagina e' gia' in cache, perche' l'ha letta il Ricercatore;
    ma se era fallita anche quella lettura, qui si riproverebbe e si fallirebbe di nuovo.
    """
    try:
        c = critica_film(url)
    except WikipediaNonRaggiungibile as e:
        print(f"  !! punteggi della critica non letti, restano n/d: {e}", flush=True)
        return dossier
    if c is None:
        return dossier
    return dossier.model_copy(update={
        "rotten_tomatoes": c.rotten_tomatoes if c.rotten_tomatoes != "n/d" else dossier.rotten_tomatoes,
        "metacritic": c.metacritic,
        "cinemascore": c.cinemascore,
        "consenso_critica": c.consenso,
    })


def salva_dossier(dossier: DossierFilm, cartella: Path | str) -> tuple[Path, Path]:
    """Salva il dossier in JSON (il contratto, da rileggere) e in Markdown (da leggere).
    Torna i due percorsi."""
    cartella = Path(cartella)
    cartella.mkdir(parents=True, exist_ok=True)
    nome = "".join(c if c.isalnum() or c in " -_" else "_" for c in dossier.titolo).strip().replace(" ", "_")
    j = cartella / f"{nome}.json"
    m = cartella / f"{nome}.md"
    j.write_text(dossier.model_dump_json(indent=2), encoding="utf-8")
    m.write_text(dossier_to_md(dossier), encoding="utf-8")
    return j, m


def carica_dossier(percorso: Path | str) -> DossierFilm:
    """Rilegge un dossier salvato. Utile per dibattere senza rifare la ricerca:
    il dossier e' un contratto, e un contratto si puo' mettere via."""
    return DossierFilm(**json.loads(Path(percorso).read_text(encoding="utf-8")))


def _normalizza(t: str) -> str:
    return "".join(c for c in t.lower() if c.isalnum())


def trova_dossier(cartella: Path | str, titolo: str, anno: int) -> DossierFilm | None:
    """Cerca tra i dossier gia' salvati uno che corrisponda a questo film.

    Serve piu' di quanto sembri: rifare la ricerca a ogni giro costa una manciata di
    chiamate al modello, e se stai registrando la stessa scena tre
    volte le paghi tre volte. Il titolo salvato viene dall'LLM ("The Village") e non
    coincide col titolo di Wikipedia ("The Village (2004 film)"), quindi confrontiamo
    sull'anno piu' il titolo normalizzato, in un verso o nell'altro.
    """
    cartella = Path(cartella)
    if not cartella.is_dir():
        return None
    cercato = _normalizza(titolo)
    for f in sorted(cartella.glob("*.json")):
        try:
            d = carica_dossier(f)
        except Exception:
            continue
        salvato = _normalizza(d.titolo)
        if d.anno == anno and (salvato in cercato or cercato in salvato):
            return d
    return None


def dossier_to_md(d: DossierFilm) -> str:
    righe = [
        f"# {d.titolo} ({d.anno})",
        f"*Regia di {d.regista}*",
        "",
        f"- **Incasso**: {d.incasso}",
        f"- **Rotten Tomatoes**: {d.rotten_tomatoes}",
        f"- **Metacritic**: {d.metacritic}",
        f"- **CinemaScore**: {d.cinemascore}",
        f"- **Consenso della critica**: {d.consenso_critica}",
        "",
        "## Trama",
        d.descrizione,
        "",
        "## Recensioni",
    ]
    for r in d.recensioni:
        righe.append(f"- **[{r.sentiment}]** {r.fonte}: {r.estratto}  \n  <{r.url}>")
    return "\n".join(righe) + "\n"
