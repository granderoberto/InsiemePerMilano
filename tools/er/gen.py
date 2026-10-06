E = {
 "UTENTE": ["id","nome","cognome","email","password_hash","codice_fiscale_hash","data_nascita","metodo_registrazione","ruolo","stato_account","profilo_pubblico","mfa_attiva","mfa_segreto","tentativi_falliti","bloccato_fino","email_verificata_il","creato_il","eliminato_il"],
 "QUARTIERE": ["id","nome","municipio","confine"],
 "VERIFICA_IDENTITA": ["id","tentativo","tipo_documento","ok_lettura_ocr","ok_corrispondenza_dati","ok_validita","ok_autenticita","ok_confronto_volto","punteggio","esito_ia","motivo","esito_finale","motivo_revisione","revisionata_il","creata_il"],
 "SOSPENSIONE": ["id","motivo","inizio","fine","revocata_il"],
 "DOCUMENTO_NORMATIVO": ["id","tipo","versione","testo","pubblicato_il"],
 "SEGNALAZIONE": ["id","tipo","titolo","descrizione","latitudine","longitudine","indirizzo","esito_moderazione","punteggio_moderazione","punteggio_coerenza","nascosta","motivo_nascosta","creata_il","aggiornata_il","eliminata_il"],
 "MEDIA": ["id","tipo","percorso","mime_type","dimensione_byte","durata_sec","ordine","copertina","exif_lat","exif_lon","esito_visione","punteggio_sessuale","punteggio_violenza","testo_ocr","esito_testo_ocr","caricato_il"],
 "STATO": ["id","nome","finale","pubblico"],
 "CAMBIO_STATO": ["id","nota","avvenuto_il"],
 "CATEGORIA": ["id","nome","descrizione","attiva"],
 "COMMENTO": ["id","testo","esito_moderazione","punteggio_moderazione","nascosto","motivo_nascosto","creato_il","modificato_il","eliminato_il"],
 "CANDIDATO": ["id","nome","cognome","lista","email"],
 "RICHIESTA_REVISIONE": ["id","motivo","stato","risposta","creata_il","chiusa_il"],
 "NOTIFICA": ["id","tipo","messaggio","link","letta","creata_il"],
 "PREFERENZA_NOTIFICA": ["tipo","in_app","email"],
 "LOG_ATTIVITA": ["id","avvenuto_il","attore","operazione","tabella","id_oggetto","dati_precedenti","dati_nuovi"],
}
WEAK = {"PREFERENZA_NOTIFICA"}
# (nome, [(entità, cardinalità)], attributi)
R = [
 ("RISIEDE",[("UTENTE","(0,1)"),("QUARTIERE","(0,N)")],[]),
 ("SI_TROVA",[("SEGNALAZIONE","(1,1)"),("QUARTIERE","(0,N)")],[]),
 ("CREA",[("UTENTE","(0,N)"),("SEGNALAZIONE","(1,1)")],[]),
 ("EFFETTUA",[("UTENTE","(0,3)"),("VERIFICA_IDENTITA","(1,1)")],[]),
 ("REVISIONA",[("UTENTE","(0,N)"),("VERIFICA_IDENTITA","(0,1)")],[]),
 ("SUBISCE",[("UTENTE","(0,N)"),("SOSPENSIONE","(1,1)")],[]),
 ("APPLICA",[("UTENTE","(0,N)"),("SOSPENSIONE","(1,1)")],[]),
 ("REVOCA",[("UTENTE","(0,N)"),("SOSPENSIONE","(0,1)")],[]),
 ("PUBBLICA",[("UTENTE","(0,N)"),("DOCUMENTO_NORMATIVO","(1,1)")],[]),
 ("ACCETTA",[("UTENTE","(0,N)"),("DOCUMENTO_NORMATIVO","(0,N)")],["accettato_il"]),
 ("CONTIENE",[("SEGNALAZIONE","(1,10)"),("MEDIA","(1,1)")],[]),
 ("CLASSIFICATA",[("SEGNALAZIONE","(1,N)"),("CATEGORIA","(0,N)")],["origine","confidenza"]),
 ("HA_STATO",[("SEGNALAZIONE","(1,1)"),("STATO","(0,N)")],[]),
 ("STORICO",[("SEGNALAZIONE","(0,N)"),("CAMBIO_STATO","(1,1)")],[]),
 ("DA",[("CAMBIO_STATO","(1,1)"),("STATO","(0,N)")],[]),
 ("A",[("CAMBIO_STATO","(1,1)"),("STATO","(0,N)")],[]),
 ("ESEGUE",[("UTENTE","(0,N)"),("CAMBIO_STATO","(0,1)")],[]),
 ("PRECEDE",[("STATO","(0,N) da"),("STATO","(0,N) a")],[]),
 ("SOSTIENE",[("UTENTE","(0,N)"),("SEGNALAZIONE","(0,N)")],["creato_il"]),
 ("NASCONDE_S",[("UTENTE","(0,N)"),("SEGNALAZIONE","(0,1)")],[]),
 ("SCRIVE",[("UTENTE","(0,N)"),("COMMENTO","(1,1)")],[]),
 ("RIGUARDA",[("SEGNALAZIONE","(0,N)"),("COMMENTO","(1,1)")],[]),
 ("RISPONDE",[("COMMENTO","(0,N) padre"),("COMMENTO","(0,1) figlio")],[]),
 ("NASCONDE_C",[("UTENTE","(0,N)"),("COMMENTO","(0,1)")],[]),
 ("INVIA",[("UTENTE","(0,N)"),("SEGNALAZIONE","(0,N)"),("CANDIDATO","(0,N)")],["inviato_il"]),
 ("RICHIEDE",[("UTENTE","(0,N)"),("RICHIESTA_REVISIONE","(1,1)")],[]),
 ("GESTISCE",[("UTENTE","(0,N)"),("RICHIESTA_REVISIONE","(0,1)")],[]),
 ("SU_SEGNALAZIONE",[("RICHIESTA_REVISIONE","(0,1)"),("SEGNALAZIONE","(0,N)")],[]),
 ("SU_COMMENTO",[("RICHIESTA_REVISIONE","(0,1)"),("COMMENTO","(0,N)")],[]),
 ("SU_VERIFICA",[("RICHIESTA_REVISIONE","(0,1)"),("VERIFICA_IDENTITA","(0,N)")],[]),
 ("RICEVE",[("UTENTE","(0,N)"),("NOTIFICA","(1,1)")],[]),
 ("IMPOSTA",[("UTENTE","(0,N)"),("PREFERENZA_NOTIFICA","(1,1)")],[]),
 ("REGISTRA",[("UTENTE","(0,N)"),("LOG_ATTIVITA","(0,1)")],[]),
]
IDENT = {"IMPOSTA"}
COL = {"UTENTE":"#E6F1FB","SEGNALAZIONE":"#FAEEDA"}
def ent(n,a):
    rows=""
    for x in a:
        if (x=="id") or (n in WEAK and x=="tipo"):
            dash = ' (chiave parziale)' if n in WEAK else ''
            rows+=f'<TR><TD ALIGN="LEFT">&#9679; <U><B>{x}</B></U>{dash}</TD></TR>'
        else:
            rows+=f'<TR><TD ALIGN="LEFT">&#9675; {x}</TD></TR>'
    bg = COL.get(n,"#F1EFE8")
    border = 'BORDER="3"' if n in WEAK else 'BORDER="1"'
    return f'"{n}" [shape=plaintext label=<<TABLE {border} CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" BGCOLOR="{bg}"><TR><TD BGCOLOR="#444441"><FONT COLOR="white"><B>{n}</B></FONT></TD></TR>{rows}</TABLE>>];'
out=['graph ER {','graph [layout=neato overlap=false splines=true sep="+28" fontname="DejaVu Sans" pad=0.4 outputorder=edgesfirst];',
     'node [fontname="DejaVu Sans" fontsize=10]; edge [fontname="DejaVu Sans" fontsize=10 color="#5F5E5A"];']
for n,a in E.items(): out.append(ent(n,a))
for i,(n,parts,attrs) in enumerate(R):
    rid=f"R_{n}"
    lab=n.replace("_S","").replace("_C","") if n in ("NASCONDE_S","NASCONDE_C") else n
    if attrs: lab+="\\n"+"\\n".join("○ "+x for x in attrs)
    per = 3 if n in IDENT else 1
    out.append(f'"{rid}" [shape=diamond style=filled fillcolor="#EEEDFE" color="#534AB7" peripheries={per} label="{lab}" fontsize=9 margin=0.02];')
    for e,c in parts:
        mid = (n in ("PRECEDE","RISPONDE")) or (e=="SOSPENSIONE")
        lab = f'label="{c}"' if mid else f'taillabel="{c}" labeldistance=2.6 labelangle=18'
        out.append(f'"{e}" -- "{rid}" [{lab} fontcolor="#993C1D" len=2.1];')
out.append('}')
open("er.dot","w").write("\n".join(out))
