import json, html
o=json.load(open('out.json')); M=json.load(open('meta.json')); m=M['meta']
WEAK={"PREFERENZA_NOTIFICA"}; IDENT={"IMPOSTA"}
N={c['id']:c for c in o['children']}
DX=11; DY=14
W,H=o['width'],o['height']
S=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H+60:.0f}" viewBox="0 0 {W:.0f} {H+60:.0f}" font-family="DejaVu Sans, Arial, sans-serif">',
   f'<rect width="100%" height="100%" fill="white"/>',
   '<g stroke="#222" stroke-width="1.3" fill="none">']
T=[]  # testi e forme sopra le linee
def esc(s): return html.escape(s)
# linee
for e in o['edges']:
    sec=e['sections'][0]
    pts=[sec['startPoint']]+sec.get('bendPoints',[])+[sec['endPoint']]
    pts=[dict(p) for p in pts]
    for idx,nid in ((0,e['sources'][0]),(-1,e['targets'][0])):
        if not nid.startswith('R_'): continue
        n=N[nid];mm=m[nid];p=pts[idx];q=pts[1] if idx==0 else pts[-2]
        cx=n['x']+mm['dw']/2; cy=n['y']+mm['attrH']+mm['dh']/2
        if abs(p['y']-q['y'])<0.5:   # segmento orizzontale
            dy=min(abs(p['y']-cy),mm['dh']/2-1); half=mm['dw']/2*(1-dy/(mm['dh']/2))
            p['x']=cx-half if p['x']<cx else cx+half
        else:                         # segmento verticale
            dx=min(abs(p['x']-cx),mm['dw']/2-1); half=mm['dh']/2*(1-dx/(mm['dw']/2))
            p['y']=cy-half if p['y']<cy else cy+half
    d="M"+" L".join(f"{p['x']:.1f},{p['y']:.1f}" for p in pts)
    S.append(f'<path d="{d}"/>')
    for lb in e.get('labels',[]):
        T.append(f'<text x="{lb["x"]+2:.1f}" y="{lb["y"]+10.5:.1f}" font-size="11" fill="#B0301A" font-weight="bold">{esc(lb["text"])}</text>')
S.append('</g>')
# entità
for nid,n in N.items():
    mm=m[nid]; x,y=n['x'],n['y']
    if nid.startswith('R_'):
        cx=x+mm['dw']/2; top=y+mm['attrH']; cy=top+mm['dh']/2; w2=mm['dw']/2; h2=mm['dh']/2
        poly=f"{cx},{top} {cx+w2},{cy} {cx},{top+mm['dh']} {cx-w2},{cy}"
        T.append(f'<polygon points="{poly}" fill="white" stroke="#222" stroke-width="1.4"/>')
        if nid[2:] in IDENT:
            poly2=f"{cx},{top+6} {cx+w2-11},{cy} {cx},{top+mm['dh']-6} {cx-w2+11},{cy}"
            T.append(f'<polygon points="{poly2}" fill="none" stroke="#222" stroke-width="1.2"/>')
        T.append(f'<text x="{cx}" y="{cy+4}" font-size="11" text-anchor="middle" letter-spacing="0.3">{esc(mm["lab"])}</text>')
        k=len(mm['attrs'])
        for i,a in enumerate(mm['attrs']):
            sx=cx+i*DX; ay=top-(k-i)*DY
            T.append(f'<line x1="{sx}" y1="{top+(i*DX)*h2/w2 if i else top}" x2="{sx}" y2="{ay+4}" stroke="#222" stroke-width="1.1"/>')
            T.append(f'<circle cx="{sx}" cy="{ay}" r="3.6" fill="white" stroke="#222" stroke-width="1.1"/>')
            T.append(f'<text x="{sx+7}" y="{ay+4}" font-size="10.5">{esc(a)}</text>')
        continue
    top=y+mm['attrH']; bw,bh=mm['boxW'],mm['boxH']
    T.append(f'<rect x="{x}" y="{top}" width="{bw}" height="{bh}" fill="white" stroke="#222" stroke-width="1.5"/>')
    if nid in WEAK:
        T.append(f'<rect x="{x+4}" y="{top+4}" width="{bw-8}" height="{bh-8}" fill="none" stroke="#222" stroke-width="1.2"/>')
    T.append(f'<text x="{x+bw/2}" y="{top+bh/2+5}" font-size="14" text-anchor="middle" font-weight="bold" letter-spacing="0.6">{esc(nid)}</text>')
    k=len(mm['attrs'])
    for i,a in enumerate(mm['attrs']):
        sx=x+12+i*DX; ay=top-(k-i)*DY
        pk = a=="id" or (nid in WEAK and a=="tipo")
        T.append(f'<line x1="{sx}" y1="{top}" x2="{sx}" y2="{ay+4}" stroke="#222" stroke-width="1.1"/>')
        T.append(f'<circle cx="{sx}" cy="{ay}" r="3.8" fill="{"#222" if pk else "white"}" stroke="#222" stroke-width="1.1"/>')
        lab = f'<tspan text-decoration="underline" font-weight="bold">{esc(a)}</tspan>' if pk else esc(a)
        if pk and nid in WEAK: lab=f'<tspan text-decoration="underline" stroke-dasharray="2">{esc(a)}</tspan> (chiave parziale)'
        T.append(f'<text x="{sx+7}" y="{ay+4}" font-size="10.5">{lab}</text>')
# legenda
ly=H+15
T.append(f'<g font-size="11"><circle cx="50" cy="{ly}" r="3.8" fill="#222" stroke="#222"/><text x="60" y="{ly+4}">chiave primaria</text>'
         f'<circle cx="170" cy="{ly}" r="3.8" fill="white" stroke="#222"/><text x="180" y="{ly+4}">attributo</text>'
         f'<text x="260" y="{ly+4}" fill="#B0301A" font-weight="bold">(min,max)</text><text x="330" y="{ly+4}">cardinalità dal lato dell\'entità</text>'
         f'<rect x="530" y="{ly-8}" width="26" height="16" fill="white" stroke="#222"/><rect x="533" y="{ly-5}" width="20" height="10" fill="none" stroke="#222"/><text x="562" y="{ly+4}">entità debole / associazione identificante</text></g>')
S+=T; S.append('</svg>')
open('er_ortho.svg','w').write("\n".join(S))
