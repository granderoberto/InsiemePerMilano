import json, subprocess
exec(open('gen.py').read().split("IDENT =")[0])   # E, WEAK, R
RANK = {"UTENTE":0,"SEGNALAZIONE":1,"VERIFICA_IDENTITA":1,"SOSPENSIONE":1,"DOCUMENTO_NORMATIVO":1,
        "NOTIFICA":1,"PREFERENZA_NOTIFICA":1,"LOG_ATTIVITA":1,"QUARTIERE":2,"COMMENTO":2,"CAMBIO_STATO":2,
        "MEDIA":2,"CATEGORIA":2,"CANDIDATO":2,"RICHIESTA_REVISIONE":3,"STATO":3}
IDENT={"IMPOSTA"}
CW=6.4; DX=11; DY=14
def tw(s,c=CW): return len(s)*c
# ordine attributi: PK prima, poi per lunghezza decrescente
def ordina(n,a):
    pk=[x for x in a if x=="id" or (n in WEAK and x=="tipo")]
    rest=sorted([x for x in a if x not in pk], key=len, reverse=True)
    return pk+rest
edges=[]; ports={n:{"WEST":[], "EAST":[]} for n in E}
for rn,parts,attrs in R:
    rid="R_"+rn
    ents=[e for e,_ in parts]
    if len(set(ents))==1:  # ricorsiva
        (e,c1),(_,c2)=parts
        edges.append((e,rid,c1,"TAIL")); edges.append((rid,e,c2,"HEAD"))
    else:
        srt=sorted(parts,key=lambda p:RANK[p[0]])
        for i,(e,c) in enumerate(srt):
            if i==len(srt)-1: edges.append((rid,e,c,"HEAD"))
            else: edges.append((e,rid,c,"TAIL"))
children=[]; meta={}
for i,(s,t,c,pl) in enumerate(edges):
    if pl=="TAIL": ports[s]["EAST"].append(f"p{i}")
    else: ports[t]["WEST"].append(f"p{i}")
for n,a in E.items():
    a=ordina(n,a); k=len(a)
    attrH=k*DY+10
    boxW=max(tw(n,10.4)+36, max(12+i*DX+8+tw(x) for i,x in enumerate(a))+10)
    np_=max(len(ports[n]["WEST"]),len(ports[n]["EAST"]))
    boxH=max(50, np_*22+16)
    meta[n]=dict(attrs=a,attrH=attrH,boxW=boxW,boxH=boxH)
    pl=[{"id":p,"width":1,"height":1,"layoutOptions":{"elk.port.side":side}} for side in ("WEST","EAST") for p in ports[n][side]]
    children.append({"id":n,"width":boxW,"height":attrH+boxH,"ports":pl,
        "layoutOptions":{"elk.portConstraints":"FIXED_SIDE",
                         "elk.spacing.portsSurrounding":f"[top={attrH+10},left=0,bottom=10,right=0]",
                         "elk.spacing.portPort":"18"}})
for rn,parts,attrs in R:
    lab="NASCONDE" if rn.startswith("NASCONDE") else rn
    w=max(84,tw(lab,7.2)+44); h=46
    aH=len(attrs)*DY+8 if attrs else 0
    aW=max([30+tw(x) for x in attrs]+[0])
    meta["R_"+rn]=dict(lab=lab,attrs=attrs,attrH=aH,dw=w,dh=h)
    children.append({"id":"R_"+rn,"width":max(w,w/2+aW),"height":h+aH,
       "layoutOptions":{"elk.spacing.portsSurrounding":f"[top={aH+12},left=0,bottom=12,right=0]"}})
elk_edges=[]
for i,(s,t,c,pl) in enumerate(edges):
    ed={"id":f"e{i}","labels":[{"text":c,"width":tw(c,6.2)+4,"height":13,
         "layoutOptions":{"elk.edgeLabels.placement":pl}}]}
    if pl=="TAIL": ed["sources"]=[f"p{i}"]; ed["targets"]=[t]
    else: ed["sources"]=[s]; ed["targets"]=[f"p{i}"]
    elk_edges.append(ed)
g={"id":"root","layoutOptions":{
  "elk.algorithm":"layered","elk.direction":"RIGHT","elk.edgeRouting":"ORTHOGONAL",
  "elk.layered.spacing.nodeNodeBetweenLayers":"70","elk.spacing.nodeNode":"45",
  "elk.layered.spacing.edgeNodeBetweenLayers":"25","elk.spacing.edgeEdge":"14","elk.spacing.edgeNode":"22",
  "elk.layered.nodePlacement.strategy":"NETWORK_SIMPLEX","elk.layered.considerModelOrder.strategy":"NODES_AND_EDGES",
  "elk.layered.crossingMinimization.thoroughness":"40","elk.padding":"[top=40,left=40,bottom=40,right=40]"},
  "children":children,"edges":elk_edges}
json.dump(g,open("in.json","w")); json.dump({"meta":meta,"edges":edges},open("meta.json","w"))
