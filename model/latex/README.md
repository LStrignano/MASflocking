# ORGANIZZAZIONE DEL CODICE LATEX

I file principali da modificare sono esclusivamente:

* `main.tex`
* `articolo.tex`
* `spiegazione_codice_teoria.tex`

Tutti gli altri file presenti nella cartella vengono generati automaticamente durante la compilazione e non devono essere modificati manualmente. Il file di output principale della compilazione è `main.pdf`.

## Struttura dei file

Il file `main.tex` contiene tutta la parte tecnica e le impostazioni del documento, come i pacchetti utilizzati, la formattazione e le varie configurazioni LaTeX. All'interno dello stesso file, dopo il comando `\begin{document}`, viene definita la struttura del contenuto.

Per mantenere il codice più ordinato e rendere più semplici eventuali modifiche, il contenuto vero e proprio del documento è stato suddiviso in due file separati:

* `articolo.tex`, che contiene il testo dell'articolo;
* `spiegazione_codice_teoria.tex`, che contiene la spiegazione teorica e del codice.

Questi file vengono inclusi all'interno di `main.tex` tramite il comando `\input`.

## Generazione dei diversi PDF

È possibile utilizzare la stessa struttura per generare due versioni differenti del documento.

### PDF dell'articolo

Per generare il PDF contenente esclusivamente l'articolo:

1. commentare il comando `\input` relativo a `spiegazione_codice_teoria.tex`;
2. decommentare le righe dalla 151 alla 159 di `main.tex`.

### PDF con la spiegazione teorica

Per generare il PDF contenente la spiegazione della teoria e del codice:

1. decommentare il comando `\input` relativo a `spiegazione_codice_teoria.tex`;
2. commentare le righe dalla 151 alla 159 di `main.tex`.

In questo modo è possibile passare rapidamente da una versione all'altra senza dover modificare direttamente il contenuto dei singoli documenti.

## Inclusione del codice

Per inserire blocchi di codice all'interno del documento viene utilizzato l'ambiente `lstlisting`, fornito dal pacchetto `listings`.

Questo permette di riportare il codice sorgente nel PDF mantenendo una formattazione adatta alla lettura e, se configurato opportunamente, con evidenziazione della sintassi.
