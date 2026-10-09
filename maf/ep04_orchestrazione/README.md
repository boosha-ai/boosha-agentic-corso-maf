# ep04_orchestrazione

[![Apri in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/boosha-ai/boosha-agentic-corso-maf/blob/main/maf/ep04_orchestrazione/pratica.ipynb)

> Prima di iniziare: [creare le chiavi API](../Extra/chiavi-api.md) · [ambiente Python con uv](../Extra/ambiente-python-uv.md)

Un agente da solo non discute. In questa puntata nasce il **Debate Club**: Fan e Critico si affrontano su un film partendo dal dossier del Ricercatore, e un Moderatore decide chi ha la parola. La domanda è di regia: **quando ci sono più agenti, chi decide chi parla?** Oggi la risposta è un LLM, e vediamo cosa si guadagna e cosa si paga.

Nel notebook lo costruiamo passo passo:

- **il materiale**: il dossier di *The Village*, con i punteggi della critica estratti dal codice e le citazioni verificate parola per parola contro la fonte;
- **i due debater**: Fan e Critico, senza tool, con il dossier cucito nelle istruzioni - argomentano solo da quello;
- **la versione ovvia**: un `for` che li fa parlare a turno, e le tre decisioni che ci sono nascoste dentro;
- **la group chat** (`GroupChatBuilder`, con un Moderatore che è un agente vero): il percorso lo decide l'LLM, turno per turno;
- **il prezzo**: senza un freno non finisce, e `max_rounds` conta i turni singoli, non i botta e risposta;
- **il limite scritto nel messaggio** (`termination_condition`): "2 round a testa" lo fa rispettare una funzione, non la buona volontà del Moderatore;
- **il percorso lo leggi dopo**: la sequenza non la scrivi, la scopri a cose fatte;
- **la stella**: in una group chat nessuno parla con nessuno, e tutti vedono tutto.

Da questa puntata il Debate Club esce dal notebook e diventa un **progetto**, nella cartella [`progetto/`](progetto/README.md): lo stesso codice delle celle, con i prompt in file `.md`, i contratti in un posto solo e un comando da terminale. Dalla radice del corso:

```bash
uv run debate-club dibatti "M. Night Shyamalan" --film 6 --push
```

Fan e Critico discutono *The Village* da terminale, e con `--push` l'ultima parola del dibattito ti arriva come notifica sul telefono.

```bash
uv run debate-club devui
```

Apre DevUI nel browser con il Debate Club completo, Ricercatore compreso: lo guardi lavorare in diretta. Nel form compili due campi soli, `role` = `user` e `contents` = la scheda:

```
Film: The Village (2004), regia di M. Night Shyamalan.
Motion: capolavoro incompreso o semplicemente sopravvalutato?
Durata: 2 round a testa.
```

Un dibattito per ogni avvio: per il successivo, Ctrl+C e rilancia. Tutti i dettagli sono nel [README del progetto](progetto/README.md).

Serve `OPENAI_API_KEY` nel `.env` (vedi `SETUP.md`); Pushover è opzionale. Dati e critica arrivano da Wikipedia, che non chiede chiavi.

**Il tuo turno**: cambia la motion. *"Il finale è un colpo di genio o un imbroglio?"* porta il dibattito da un'altra parte, con lo stesso dossier e lo stesso cast.

Contenuto della puntata:

- `pratica.ipynb` - notebook eseguibile (Colab o Jupyter in locale)
