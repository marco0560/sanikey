# ADR: Fogli illustrativi locali con verifica AIFA

## Stato

Accettata.

## Contesto

La chiavetta viene generata su Linux con accesso a Internet, ma viene
consultata su PC Windows, macOS o Linux che possono essere offline. Il paziente
non deve conoscere AIC, URL AIFA o altri identificativi tecnici.

## Decisione

SaniKey ricerca i medicinali nella banca dati pubblica AIFA a partire dai dati
gia' curati. Una corrispondenza univoca e compatibile puo' essere confermata;
ogni caso ambiguo richiede la conferma dell'operatore prima di diventare un
riferimento curato. Alle esecuzioni successive, SaniKey verifica i riferimenti
gia' salvati e li conserva automaticamente se il catalogo AIFA li riconosce.

Dopo la conferma, ogni build scarica nuovamente FI e RCP in una copia locale
dell'export USB. Questo aggiorna la copia anche quando il codice AIC resta
invariato ma il documento AIFA viene revisionato.
La scheda Terapia mostra il collegamento locale, la data di download e un
collegamento esterno ad AIFA per verificare una versione piu' recente.

L'associazione salvata usa gli identificativi AIFA verificati, ma questi non
sono campi da compilare dal paziente. Ogni farmaco presente in una terapia deve
avere un riferimento confermato oppure uno stato esplicito `non_aifa`.
L'export USB viene bloccato se FI o RCP locali non sono disponibili per un
riferimento AIFA confermato.

## Conseguenze

La consultazione resta possibile offline e non puo' essere distribuita con
terapie AIFA prive dei due PDF locali. Il PDF locale e' una fotografia datata,
non una garanzia di aggiornamento corrente; l'interfaccia deve renderlo
esplicito.
