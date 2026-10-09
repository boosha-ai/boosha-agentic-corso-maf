"""I contratti del Debate Club: cosa passa da un agente all'altro.

Sta tutto qui di proposito. Quando piu' agenti si scambiano dati, la cosa piu' facile
da sbagliare e' che ognuno abbia la sua idea della forma: un dizionario con le chiavi
un po' diverse, una stringa da interpretare. Dichiarare la forma una volta sola, in un
posto solo, e' quello che rende componibili gli agenti.

Nati in EP 2: Film, Filmografia, Recensione, DossierFilm.
Nati in EP 4: Intervento, Trascrizione; e `DossierFilm` acquisisce i punteggi aggregati
della critica (Metacritic, CinemaScore, consenso), per aggiunta.
Forma preparata per EP 6: Verdetto.
"""

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- EP 2: la ricerca
class Film(BaseModel):
    """Una voce di filmografia. L'URL e' la chiave: e' cosi' che il dossier evita
    di ricercare per titolo e di prendere l'omonimo sbagliato."""

    titolo: str
    anno: int
    url: str


class Filmografia(BaseModel):
    """L'esito della discovery: la lista da cui si sceglie il film del dibattito.
    In EP 5 diventa l'input della scelta umana (human-in-the-loop)."""

    regista: str
    film: list[Film]


class Recensione(BaseModel):
    """Un estratto di critica, classificato dal Ricercatore. La fonte e l'URL non sono
    decorazione: in EP 6 sono cio' che permette al Giudice di verificare."""

    fonte: str
    url: str
    # `Literal` e non un commento accanto a `str`: un vincolo in un commento non vincola
    # niente, cosi' invece e' l'output strutturato a non ammettere altri valori.
    sentiment: Literal["positiva", "negativa"]
    estratto: str


class DossierFilm(BaseModel):
    """Il dossier del film: il contratto Ricercatore -> Fan/Critico.

    E' la ground truth del dibattito. Fan e Critico argomentano SOLO da qui, senza tool
    propri, ed e' questo vincolo che in EP 6 permette al Giudice di beccare un dato
    inventato: se un numero non e' nel dossier, l'agente se l'e' inventato.
    """

    titolo: str
    anno: int
    regista: str
    incasso: str
    rotten_tomatoes: str
    descrizione: str
    recensioni: list[Recensione]

    # Nati in EP 4, per aggiunta (con un default, cosi' i dossier gia' salvati si caricano
    # ancora). Sono la voce **collettiva** della critica, e li scrive il **codice**, non il
    # modello: si leggono dalla sezione "Critical response" della pagina Wikipedia del film.
    # Un dato che si puo' estrarre col codice non si fa interpretare a un LLM.
    metacritic: str = "n/d"
    cinemascore: str = "n/d"
    consenso_critica: str = "n/d"


# ---------------------------------------------------------------- EP 4: il dibattito
class Intervento(BaseModel):
    """Una battuta del dibattito: chi ha parlato, in che round, cosa ha detto."""

    round: int
    oratore: str  # "Fan" | "Critico" | "Moderatore"
    testo: str


class Trascrizione(BaseModel):
    """Il verbale del dibattito. E' il pezzo che serve tre volte:
    al Moderatore in EP 4, come stato condiviso nel grafo in EP 5, al Giudice in EP 6.
    Per questo e' tipizzata da subito, invece di essere una lista di stringhe."""

    film: str
    motion: str
    interventi: list[Intervento] = Field(default_factory=list)

    def aggiungi(self, round: int, oratore: str, testo: str) -> None:
        self.interventi.append(Intervento(round=round, oratore=oratore, testo=testo))

    def per_oratore(self, oratore: str) -> list[Intervento]:
        return [i for i in self.interventi if i.oratore == oratore]

    def testo_piatto(self) -> str:
        """La trascrizione come testo, per darla in pasto a un agente (il Giudice, in EP 6)."""
        return "\n\n".join(f"[round {i.round}] {i.oratore}: {i.testo}" for i in self.interventi)

    def per_notifica(self, limite: int = 1024) -> str:
        """Il dibattito ridotto a un messaggio che sta in una notifica push.

        Un dibattito vero misura oltre 2000 caratteri e ogni intervento sta sui 500-600:
        anche solo l'ultimo scambio (due interventi) sfora i 1024 di Pushover. Quindi qui
        si manda l'**ultima parola**, che in un dibattito e' la battuta piu' affilata,
        preceduta da un'intestazione che dice su cosa e quanto si e' discusso.

        Il taglio e' fatto a mano e in modo prevedibile: niente riassunto generato, che
        sarebbe un'altra chiamata al modello e somiglierebbe a un verdetto - e il verdetto
        e' compito del Giudice, in EP 6.
        """
        testa = f"{self.film}\n{self.motion}\n{len(self.interventi)} interventi in {self.round_totali()} round."
        if not self.interventi:
            return testa
        ultimo = self.interventi[-1]
        spazio = limite - len(testa) - len(ultimo.oratore) - 20
        coda = ultimo.testo if len(ultimo.testo) <= spazio else ultimo.testo[: max(spazio - 3, 0)] + "..."
        return f"{testa}\n\nUltima parola ({ultimo.oratore}):\n{coda}"

    def round_totali(self) -> int:
        return max((i.round for i in self.interventi), default=0)


# ---------------------------------------------------------------- EP 6: la valutazione
class Verdetto(BaseModel):
    """Solo la forma, per non doverla cambiare in EP 6. Il Giudice arriva li'."""

    vincitore: str
    motivazione: str
    punteggi: dict[str, int] = Field(default_factory=dict)
    dati_non_nel_dossier: list[str] = Field(default_factory=list)
