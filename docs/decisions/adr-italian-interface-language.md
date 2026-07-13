# ADR: Lingua italiana per errori e interfaccia

## Stato

Accettata.

## Contesto

SaniKey e' un progetto destinato a operatori e manutentori che lavorano in
italiano. La documentazione principale, le specifiche e le decisioni sono gia'
redatte in italiano, ma alcune superfici operative esponevano messaggi in
inglese.

Questa incoerenza rendeva meno immediata la lettura di errori, avvisi, help CLI
e testi del frontend durante build, validazione e consultazione offline.

## Decisione

La lingua predefinita per errori, avvisi, help CLI, testi del frontend e output
procedurali leggibili da persone e' l'italiano.

Restano in inglese solo le superfici tecniche che sono contratti macchina o
interfacce esterne:

- nomi di comandi, opzioni, campi TOML, chiavi JSON e colonne CSV;
- valori macchina gia' parte del contratto dati, per esempio `status=ok`;
- nomi propri di strumenti, formati, librerie e protocolli;
- messaggi provenienti da programmi esterni riportati come dettaglio diagnostico.

## Conseguenze

Nuove funzionalita' e correzioni devono mantenere in italiano i messaggi
visibili agli utenti. Quando un test verifica un messaggio leggibile da una
persona, il testo atteso deve usare l'italiano e preservare le chiavi macchina
necessarie per parsing o compatibilita'.
