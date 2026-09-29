import json
g=json.load(open('in.json')); o=json.load(open('out.json')); m=json.load(open('meta.json'))['meta']
OUT={c['id']:c for c in o['children']}
for c in g['children']:
    if c['id'].startswith('R_'): continue
    mm=m[c['id']]; oc=OUT[c['id']]
    py={p['id']:p['y'] for p in oc['ports']}
    for side in ("WEST","EAST"):
        ps=sorted([p for p in c['ports'] if p['layoutOptions']['elk.port.side']==side], key=lambda p:py[p['id']])
        n=len(ps)
        for i,p in enumerate(ps):
            p['x']=0 if side=="WEST" else mm['boxW']-1
            p['y']=mm['attrH']+ (i+1)*mm['boxH']/(n+1)
    c['layoutOptions']={"elk.portConstraints":"FIXED_POS"}
json.dump(g,open('in.json','w'))
