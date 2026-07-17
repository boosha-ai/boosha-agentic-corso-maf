# Appendice · Come creare le chiavi API

> Modulo pratico da fare **una volta sola**, prima di eseguire i notebook.
> Le chiavi si procurano dai siti dei provider e finiscono tutte nello stesso posto:
> un file `.env` nella radice del progetto (mai su GitHub, vedi sotto).

## Quali chiavi servono

| Chiave | A cosa serve | Obbligatoria? | Dove entra |
|---|---|---|---|
| `OPENAI_API_KEY` | il modello che ragiona (provider cloud di default) | ✅ **Sì** | tutte le puntate |
| `PUSHOVER_TOKEN` + `PUSHOVER_USER` | la notifica push sul telefono | opzionale | EP 1 (side-effect), EP 2+ (tool) |
| `TAVILY_API_KEY` | la ricerca recensioni su domini fidati | opzionale | EP 2 in poi |
| Ollama | modello in locale, sul tuo computer | nessuna chiave | solo EP 1 |

> 💡 Le variabili opzionali non bloccano il notebook: se mancano, il tool relativo si limita a
> degradare con un messaggio ("Tavily non configurato...", "push saltata..."). Per iniziare basta
> `OPENAI_API_KEY`.

---

## Il file `.env` (dove incolli tutto)

Le chiavi non vanno nel codice: vanno in un file `.env` nella radice della repo. Nel progetto c'è
già un modello, `.env.example`, con tutti i nomi giusti. Copialo e riempi i valori:

```bash
cp .env.example .env
# ...poi apri .env e incolla dentro le chiavi vere...
```

Il file finito ha questo aspetto:

```
OPENAI_API_KEY=sk-...
PUSHOVER_TOKEN=...
PUSHOVER_USER=...
TAVILY_API_KEY=tvly-...
```

> 🔒 **Il `.env` non si committa mai.** È già nel `.gitignore`: le chiavi sono private e valgono
> soldi. Committiamo solo `.env.example` (senza valori), così chi clona sa *quali* variabili creare.
> Attenzione anche a registrazioni e screenshot: se mostri il `.env` in video, oscura le chiavi.

---

## 1. OpenAI (obbligatoria)

Il provider cloud di default della serie.

1. Vai su [platform.openai.com](https://platform.openai.com) e crea un account (o accedi).
2. Apri la sezione **API keys**: [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
3. Clicca **Create new secret key**, dai un nome (es. `boosha-agenti`) e crea.
4. **Copia subito** la chiave (`sk-...`): viene mostrata una sola volta, poi non è più recuperabile.
5. Incollala nel `.env` accanto a `OPENAI_API_KEY=`.

> ⚠️ **La trappola dei crediti.** Una chiave valida non basta: l'account deve avere credito.
> Vai in **Settings → Billing**, aggiungi un metodo di pagamento e un po' di credito (bastano pochi
> euro). Senza credito le chiamate falliscono con un errore di *quota*, anche se la chiave è giusta.

---

## 2. Pushover (opzionale, per la push)

Pushover manda notifiche push al tuo telefono. Servono **due** valori distinti: la tua *user key*
(chi riceve) e un *API token* dell'applicazione (chi manda).

**a. User key** (`PUSHOVER_USER`)

1. Crea un account su [pushover.net](https://pushover.net) e installa l'app Pushover sul telefono.
2. Fai login: nella pagina principale del sito trovi la tua **Your User Key**.
3. Copiala nel `.env` accanto a `PUSHOVER_USER=`.

**b. API token dell'app** (`PUSHOVER_TOKEN`)

1. Vai su [pushover.net/apps/build](https://pushover.net/apps/build), voce **Create an Application/API Token**.
2. Dai un nome (es. `Agente Boosha`) e crea l'applicazione.
3. Copia l'**API Token/Key** generato nel `.env` accanto a `PUSHOVER_TOKEN=`.

> 💡 Pushover offre una prova gratuita; dopo il periodo di prova l'app sul telefono richiede un
> acquisto una tantum. Per la serie è comodo ma sostituibile: se salti questa chiave, il codice
> semplicemente non manda la push.

---

## 3. Tavily (opzionale, per le recensioni · EP 2)

Tavily è un motore di ricerca pensato per gli agenti: in EP 2 lo usiamo per cercare recensioni
su domini fidati.

1. Crea un account su [tavily.com](https://tavily.com) (o [app.tavily.com](https://app.tavily.com)).
2. Nella dashboard trovi la tua **API key** (`tvly-...`), con un piano gratuito mensile.
3. Copiala nel `.env` accanto a `TAVILY_API_KEY=`.

> 💡 Se manca, in EP 2 il tool recensioni degrada da solo: l'agente costruisce il dossier con i soli
> dati di Wikipedia, senza recensioni.

---

## 4. Ollama (nessuna chiave · solo EP 1)

In EP 1 mostriamo lo stesso agente girare **in locale**, senza chiave e senza costo. Non serve
registrarsi da nessuna parte: si installa Ollama e si scarica un modello piccolo.

```bash
# installa Ollama da https://ollama.com, poi:
ollama serve            # avvia il server locale (default http://localhost:11434)
ollama pull llama3.2    # scarica un modello piccolo (3B: entra tutto in GPU)
```

> 💡 Scegli un modello piccolo che entra tutto nella GPU (es. `llama3.2` da 3B). Modelli grossi o
> "reasoning" rallentano parecchio (spill su CPU + ragionamento). Da EP 2 in poi si usa solo OpenAI:
> con tool-calling e judge i modelli locali piccoli danno risultati scarsi.

---

## In sintesi (checklist)

- [ ] `cp .env.example .env`
- [ ] `OPENAI_API_KEY` da platform.openai.com **+ credito attivo** (obbligatoria)
- [ ] `PUSHOVER_USER` + `PUSHOVER_TOKEN` da pushover.net (opzionali)
- [ ] `TAVILY_API_KEY` da tavily.com (opzionale, EP 2)
- [ ] Ollama installato + `llama3.2` scaricato (solo se vuoi la parte locale di EP 1)
- [ ] Il `.env` **non** è tracciato da Git (è nel `.gitignore`)

Fatto questo, i notebook e gli script (`agente.py`) trovano le chiavi da soli: ogni file chiama
`load_dotenv()`, perché MAF non carica il `.env` in automatico.

Per ricreare l'ambiente Python con le dipendenze giuste, vedi [`ambiente-python-uv.md`](ambiente-python-uv.md).
