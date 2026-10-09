# Debate Club

Il progetto della serie: tre agenti discutono un film, partendo da un dossier costruito
da un quarto agente. Nasce in EP 4 e cresce fino a EP 6: questa cartella e' il progetto
com'era alla fine di EP 4.

Nei notebook si impara un pezzo per volta. Qui c'e' lo stesso codice messo come si mette
in un progetto vero: i contratti da una parte, gli strumenti dall'altra, i prompt in file
di testo, un comando da terminale. **Colab per imparare, VS Code per lavorare.**

## Provalo

```bash
uv sync --all-groups

uv run debate-club filmografia "M. Night Shyamalan"           # la lista dei film
uv run debate-club dossier     "M. Night Shyamalan" --film 6  # il dossier di uno
uv run debate-club dibatti     "M. Night Shyamalan" --film 6  # il dibattito, a terminale
uv run debate-club devui       "M. Night Shyamalan" --film 6  # ...oppure dal browser
```

**Il modo migliore per guardarlo e' `devui`.** Apre una pagina locale dove nella sidebar
trovi il Debate Club e i quattro agenti: premi Run sul Debate Club e guardi il dibattito
mentre si svolge, con il testo in streaming, gli eventi, la timeline e le tracce. Il
disegno del grafo invece resta fermo: ad animarsi e' il **run**, non il grafo. Puoi anche
interrogare un singolo agente per conto suo, per capire come reagisce.

Il form che si apre ha **sei campi**, perche' DevUI lo genera dallo schema interno di
`Message`. Te ne servono due: `role` = `user`, e `contents` = la scheda della sessione,
in testo normale:

```
Film: The Village (2004), regia di M. Night Shyamalan.
Motion: capolavoro incompreso o semplicemente sopravvalutato?
Durata: 2 round a testa.
```

**Scrivilo come una scheda, non come un ordine.** In una group chat il messaggio iniziale
lo leggono *tutti* i partecipanti, non solo il Moderatore: un imperativo al plurale
("dibattete su..., fate 2 round a testa") viene preso da ciascuno come il proprio
compito, e il Ricercatore si mette a scrivere un dibattito invece del dossier. E' lo
stesso "tutti vedono tutto" che altrove e' solo un costo in token: qui ti sfuma i ruoli.

**Un dibattito per ogni avvio di DevUI.** Finito un dibattito, "Run Again" si chiude subito
con *"The group chat has reached its termination condition"*. Non e' il nostro codice: in
`agent-framework-orchestrations` 1.3.0 (e su `main` alla data del 2026-10-02) l'orchestratore
della group chat **non azzera la conversazione** quando arriva un messaggio nuovo
(`_clear_conversation()` esiste ma nessuno la chiama), e DevUI costruisce il workflow una
volta e lo riusa. Il run dopo vede i turni del dibattito precedente e chiude. Riprodotto anche
senza DevUI. Per un altro dibattito: Ctrl+C e rilancia `devui`, che all'avvio non fa nessuna
chiamata. Aprire una sessione nuova col `+` non basta, perche' il workflow resta lo stesso.

Una cosa diversa, ma da sapere: se dal menu del pulsante scegli **"Resume from checkpoint"**,
DevUI riprende quel run salvato e **ignora il messaggio** che scrivi (il ramo di ripresa chiama
`workflow.run(checkpoint_id=...)` senza input). I checkpoint sono il tema di EP 5.

Gli altri quattro campi si lasciano vuoti, e **`author_name` in particolare**: la funzione
che conta i round riconosce il tuo messaggio dal fatto che non ha un autore, quindi
riempirlo fa ignorare il numero di round che hai chiesto.

Lancialo due volte di fila e confronta. La **sequenza** puo' benissimo restare la stessa,
perche' alternare e' quello che un buon moderatore fa: a cambiare sono gli argomenti
scelti, la lunghezza e il punto in cui si chiude. Il punto di EP 4 non e' che l'ordine sia
imprevedibile, e' che **non l'hai deciso tu**.

Il dossier, una volta costruito, viene riusato da `dibatti`: la ricerca costa chiamate al
modello, e rifarla a ogni giro e' denaro buttato. Con `--rifai` la si rifa' da capo. In
DevUI invece il Ricercatore e' al tavolo e la ricerca la rifa' ogni volta.

Serve solo `OPENAI_API_KEY` nel `.env` alla radice: dati e critica arrivano da Wikipedia,
che non chiede chiavi. Vedi [le guide di setup](../../Extra/chiavi-api.md).

## Com'e' fatto

```
debate_club/
├── modelli.py        i contratti: cosa passa da un agente all'altro
├── tools/            gli strumenti, uno per ruolo
│   ├── wikipedia.py    filmografia (con gli URL), dati e critica di un film
│   └── notifiche.py    la push sul telefono
├── istruzioni/       i prompt, come file .md fuori dal codice
├── agenti/           il cast: una factory per agente
├── dossier.py        dal film scelto al dossier
├── orchestrazione.py EP 4: il dibattito dove il percorso lo decide l'LLM
├── middleware.py     la presa tra agente e strumenti
└── cli.py            il punto d'ingresso da terminale
```

Quattro scelte che vale la pena spiegare, perche' non sono ovvie.

**I contratti stanno in un posto solo.** Quando piu' agenti si scambiano dati, la cosa
piu' facile da sbagliare e' che ognuno abbia la sua idea della forma. `DossierFilm` e
`Trascrizione` sono dichiarati una volta, in `modelli.py`, e tutti li usano.

**Fan e Critico non hanno strumenti.** Argomentano solo da quello che c'e' nel dossier.
Sembra una limitazione, ed e' invece il vincolo che tiene in piedi il resto: in EP 6 il
Giudice puo' dire se un numero e' inventato solo perche' esiste una ground truth con cui
confrontarlo.

**Accanto a ogni tool c'e' la funzione pura.** `cerca_filmografia` e' il tool che usa il
modello; `filmografia()` e' la stessa cosa che chiami tu. Serve quando un passo deve
essere deterministico: la discovery della filmografia non e' una decisione, e' un
parsing, e non ha senso pagarla al modello.

**Il dossier e' verificato, non solo tipizzato.** L'output strutturato garantisce la
*forma* del contratto, non la sua *verita'*: Pydantic accetta qualunque stringa. Quindi il
dossier si costruisce in due parti. Cio' che e' un dato (incasso, Rotten Tomatoes,
Metacritic, CinemaScore, il consenso della critica) lo estrae il **codice** dalla pagina
Wikipedia del film, raggiunta per URL. Cio' che e' un giudizio (quali citazioni scegliere,
se sono a favore o contro) lo fa il Ricercatore, e poi `verifica_fonti` controlla che ogni
citazione compaia **parola per parola** nel testo che lo strumento ha restituito: una
citazione inventata o parafrasata esce dal dossier. Al modello resta solo quello che e'
davvero una scelta.

## Da dove arriva, e dove va

| Puntata | Cosa aggiunge |
| --- | --- |
| EP 2 | i tool, i contratti, il Ricercatore che produce il dossier |
| EP 3 | la memoria (sessioni e context provider) |
| **EP 4** | **Fan, Critico, Moderatore: il dibattito, con il percorso deciso dall'LLM** |
| EP 5 | lo stesso dibattito come grafo che disegni tu, con la scelta umana del film |
| EP 6 | il Giudice, il Critico in modalita' avversariale, le tracce |

Ogni puntata ha **la sua copia** del progetto, nella propria cartella, congelata com'era nel
video: EP 5 parte da una copia di questa e ci aggiunge il grafo. Il notebook di EP 4 importa
da qui, e qui niente cambia. Il comando `uv run debate-club` invece ne usa una sola, quella
dell'ultima puntata uscita.
