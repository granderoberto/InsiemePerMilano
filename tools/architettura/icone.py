"""Icone dei disegni di architettura: gruppi SVG centrati in (0,0), riquadro 100x100, tratto nero spesso."""


def icona(nome):
    s = 'fill="none" stroke="#101010" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"'
    if nome == "persone":
        return (f'<g {s}><circle cx="-14" cy="-16" r="13" fill="#fff"/><path d="M-38 30 C-38 8 -26 0 -14 0 C-2 0 10 8 10 30 Z" fill="#fff"/>'
                f'<circle cx="20" cy="-8" r="11" fill="#fff"/><path d="M12 30 C12 14 20 8 28 8 C38 8 44 16 44 30 Z" fill="#fff"/></g>')
    if nome == "sito":
        return (f'<g {s}><rect x="-44" y="-34" width="88" height="68" rx="3" fill="#fff"/><line x1="-44" y1="-18" x2="44" y2="-18"/>'
                f'<circle cx="-34" cy="-26" r="2" fill="#101010"/><circle cx="-26" cy="-26" r="2" fill="#101010"/><circle cx="-18" cy="-26" r="2" fill="#101010"/>'
                f'<line x1="-32" y1="-4" x2="14" y2="-4"/><line x1="-32" y1="8" x2="32" y2="8"/><line x1="-32" y1="20" x2="2" y2="20"/></g>')
    if nome == "database":
        return (f'<g {s}><path d="M-36 -26 L-36 26 C-36 40 36 40 36 26 L36 -26" fill="#fff"/><ellipse cx="0" cy="-26" rx="36" ry="13" fill="#fff"/>'
                f'<path d="M-36 -2 C-36 12 36 12 36 -2"/><path d="M-36 14 C-36 28 36 28 36 14" stroke-width="0"/></g>')
    if nome == "email":
        return (f'<g {s}><rect x="-42" y="-28" width="84" height="56" rx="3" fill="#fff"/><path d="M-42 -26 L0 6 L42 -26"/></g>')
    if nome == "mappa":
        return (f'<g {s}><path d="M-40 -22 L-14 -32 L14 -22 L40 -32 L40 30 L14 40 L-14 30 L-40 40 Z" fill="#fff"/><line x1="-14" y1="-32" x2="-14" y2="30"/><line x1="14" y1="-22" x2="14" y2="40"/>'
                f'<path d="M0 -4 C-14 -22 -4 -40 0 -40 C4 -40 14 -22 0 -4 Z" fill="#e30613"/><circle cx="0" cy="-26" r="4" fill="#fff" stroke-width="3"/></g>')
    if nome == "identita":
        return (f'<g {s}><rect x="-44" y="-30" width="88" height="60" rx="4" fill="#fff"/><circle cx="-20" cy="-6" r="9"/><path d="M-34 22 C-34 10 -26 6 -20 6 C-14 6 -6 10 -6 22"/>'
                f'<line x1="8" y1="-12" x2="34" y2="-12"/><line x1="8" y1="0" x2="34" y2="0"/><line x1="8" y1="12" x2="24" y2="12"/></g>')
    if nome == "ia":
        pin = "".join(f'<line x1="{x}" y1="-40" x2="{x}" y2="-30"/><line x1="{x}" y1="30" x2="{x}" y2="40"/><line x1="-40" y1="{x}" x2="-30" y2="{x}"/><line x1="30" y1="{x}" x2="40" y2="{x}"/>' for x in (-14, 0, 14))
        return f'<g {s}><rect x="-30" y="-30" width="60" height="60" rx="5" fill="#fff"/>{pin}<text x="0" y="9" font-size="26" font-weight="800" text-anchor="middle" fill="#101010" stroke="none" font-family="Helvetica, Arial, sans-serif">IA</text></g>'
    if nome == "git":
        return (f'<g {s}><line x1="-22" y1="-26" x2="-22" y2="26"/><path d="M-22 6 C-22 -10 22 0 22 -22"/><circle cx="-22" cy="-30" r="9" fill="#fff"/>'
                f'<circle cx="-22" cy="30" r="9" fill="#fff"/><circle cx="22" cy="-26" r="9" fill="#fff"/></g>')

    if nome == "server":
        righe = "".join(f'<rect x="-40" y="{y}" width="80" height="22" rx="3" fill="#fff"/><circle cx="-28" cy="{y + 11}" r="3" fill="#101010"/><line x1="-14" y1="{y + 11}" x2="26" y2="{y + 11}"/>' for y in (-40, -12, 16))
        return f'<g {s}>{righe}</g>'
    if nome == "disco":
        return (f'<g {s}><path d="M-40 -6 L-40 14 C-40 28 40 28 40 14 L40 -6" fill="#fff"/><ellipse cx="0" cy="-6" rx="40" ry="16" fill="#fff"/>'
                f'<circle cx="26" cy="12" r="3" fill="#101010" stroke-width="2"/><line x1="-26" y1="12" x2="4" y2="12" stroke-width="3"/></g>')
    if nome == "laptop":
        return (f'<g {s}><rect x="-32" y="-34" width="64" height="44" rx="3" fill="#fff"/><path d="M-44 20 L44 20 L38 32 L-38 32 Z" fill="#fff"/><line x1="-12" y1="-12" x2="12" y2="-12"/><line x1="-12" y1="0" x2="2" y2="0"/></g>')
    if nome == "container":
        celle = "".join(f'<rect x="{x}" y="{y}" width="20" height="18" fill="#fff"/>' for x in (-36, -12, 12) for y in (-14, 8))
        return f'<g {s}>{celle}<path d="M-44 -26 L44 -26" /><path d="M-40 30 C-20 40 20 40 40 30"/></g>'
    if nome == "utente":
        return f'<g {s}><circle cx="0" cy="-16" r="15" fill="#fff"/><path d="M-30 34 C-30 8 -16 2 0 2 C16 2 30 8 30 34 Z" fill="#fff"/></g>'
    return ""


