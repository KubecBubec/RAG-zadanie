"""Generátor doménových dát pre RAG zadanie (realitná kancelária, Žilina).

Z jedného zdroja pravdy (zoznam inzerátov, maklérov, lokalít nižšie) vytvorí:
  1. ~11 PDF dokumentov v data/pdfs/  (neštruktúrované dáta pre RAG)
  2. ontology/instancie.ttl            (štruktúrované dáta – ABox ontológie)

Každý inzerát v ontológii nesie anotáciu rkx:zdrojovyDokument s názvom PDF,
v ktorom je popísaný -> dokumenty a ontológia sú explicitne prepojené.

Všetky firmy, osoby a ceny sú FIKTÍVNE (vytvorené na študijné účely).

Spustenie (v Dockeri, odporúčané):
    docker compose run --rm app python /workspace/tools/generate_data.py
Lokálne:
    pip install reportlab && python tools/generate_data.py
"""
from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(os.environ.get("WORKSPACE", Path(__file__).resolve().parents[1]))
PDF_DIR = ROOT / "data" / "pdfs"
TTL_OUT = ROOT / "ontology" / "instancie.ttl"

FIRMA = "SemReal Žilina, s.r.o. (fiktívna realitná kancelária)"
ADRESA = "Národná 1, 010 01 Žilina"

# ---------------------------------------------------------------------------
# Zdroj pravdy
# ---------------------------------------------------------------------------
# id -> (label, trieda, nadradená lokalita)
LOKALITY = {
    "Mesto_Zilina": ("Žilina", "Mesto", "Okres_Zilina"),
    "Mesto_RajeckeTeplice": ("Rajecké Teplice", "Mesto", "Okres_Zilina"),
    "Obec_Terchova": ("Terchová", "Obec", "Okres_Zilina"),
    "Obec_TeplickaNadVahom": ("Teplička nad Váhom", "Obec", "Okres_Zilina"),
    "MC_StareMesto": ("Staré Mesto", "MestskaCast", "Mesto_Zilina"),
    "MC_Hliny": ("Hliny", "MestskaCast", "Mesto_Zilina"),
    "MC_Vlcince": ("Vlčince", "MestskaCast", "Mesto_Zilina"),
    "MC_Solinky": ("Solinky", "MestskaCast", "Mesto_Zilina"),
    "MC_Hajik": ("Hájik", "MestskaCast", "Mesto_Zilina"),
    "MC_Banova": ("Bánová", "MestskaCast", "Mesto_Zilina"),
    "MC_Bytcica": ("Bytčica", "MestskaCast", "Mesto_Zilina"),
    "MC_Zavodie": ("Závodie", "MestskaCast", "Mesto_Zilina"),
}

MAKLERI = {
    "Makler_Kovacova": ("Mgr. Jana Kováčová", "byty na predaj, Staré Mesto, Hliny, Vlčince",
                        "jana.kovacova@semreal.example", "+421 900 000 101"),
    "Makler_Hruska": ("Ing. Peter Hruška", "rodinné domy, chaty, pozemky, okolie Žiliny",
                      "peter.hruska@semreal.example", "+421 900 000 102"),
    "Makler_Benova": ("Lucia Beňová", "prenájom bytov, kancelárie a obchodné priestory",
                      "lucia.benova@semreal.example", "+421 900 000 103"),
}

DOC_BYTY = "01_ponuka_bytov_na_predaj.pdf"
DOC_DOMY = "02_ponuka_domov_chat_pozemkov.pdf"
DOC_PRENAJOM = "03_ponuka_prenajmov.pdf"

# (id, typ inzerátu, trieda nehnuteľnosti, lokalita, výmera m², izby|None, cena €, maklér, dokument, popis)
INZERATY = [
    ("INZ-101", "PredajnyInzerat", "Garsonka", "MC_Vlcince", 28, 1, 98000, "Makler_Kovacova", DOC_BYTY,
     "Garsónka na 3. poschodí zatepleného panelového domu s výťahom. Kompletná rekonštrukcia v roku 2023, "
     "nová kuchynská linka, plastové okná, pivnica. Energetická trieda B. Vhodná ako investícia na prenájom."),
    ("INZ-102", "PredajnyInzerat", "JednoizbovyByt", "MC_Hliny", 36, 1, 115000, "Makler_Kovacova", DOC_BYTY,
     "Jednoizbový byt so samostatnou kuchyňou a loggiou na 5. poschodí. Pôvodný stav jadra, nové stúpačky. "
     "Výborná dostupnosť do centra (10 minút pešo), obchody a škola v blízkosti."),
    ("INZ-103", "PredajnyInzerat", "DvojizbovyByt", "MC_Solinky", 52, 2, 149000, "Makler_Kovacova", DOC_BYTY,
     "Dvojizbový byt po čiastočnej rekonštrukcii, 2. poschodie, balkón orientovaný na juh. Kúpeľňa s vaňou, "
     "samostatné WC. Parkovanie pred domom. Možnosť hypotéky, voľný ihneď."),
    ("INZ-104", "PredajnyInzerat", "DvojizbovyByt", "MC_StareMesto", 61, 2, 198000, "Makler_Kovacova", DOC_BYTY,
     "Priestranný dvojizbový byt v tehlovom meštianskom dome v historickom centre. Vysoké stropy (3,2 m), "
     "drevené parkety, nová elektroinštalácia. Bez balkóna, parkovanie v rezidentskej zóne."),
    ("INZ-105", "PredajnyInzerat", "TrojizbovyByt", "MC_Hajik", 74, 3, 189000, "Makler_Kovacova", DOC_BYTY,
     "Trojizbový byt s dvoma loggiami, 4. poschodie z 8. Kompletná rekonštrukcia, vstavané skrine, "
     "kuchyňa so spotrebičmi. Vhodný pre rodinu s deťmi – škôlka a park v blízkosti."),
    ("INZ-106", "PredajnyInzerat", "TrojizbovyByt", "MC_Vlcince", 70, 3, 179500, "Makler_Kovacova", DOC_BYTY,
     "Trojizbový byt v pôvodnom stave, vhodný na rekonštrukciu podľa vlastných predstáv. 1. poschodie, "
     "zateplený dom, nový výťah. Cena je zohľadnená stavom bytu."),
    ("INZ-107", "PredajnyInzerat", "Byt", "MC_Hliny", 88, 4, 229000, "Makler_Kovacova", DOC_BYTY,
     "Štvorizbový byt s dvoma kúpeľňami a šatníkom, 6. poschodie, výhľad na Malú Fatru. Garážové státie "
     "v cene. Byt je po celkovej rekonštrukcii z roku 2024."),
    ("INZ-201", "PredajnyInzerat", "RodinnyDom", "MC_Banova", 142, 5, 345000, "Makler_Hruska", DOC_DOMY,
     "Rodinný dom (bungalov s podkrovím) na pozemku 640 m². Tepelné čerpadlo, podlahové kúrenie, "
     "fotovoltické panely. Garáž pre dve autá. Kolaudácia v roku 2019."),
    ("INZ-202", "PredajnyInzerat", "RodinnyDom", "Mesto_RajeckeTeplice", 168, 6, 289000, "Makler_Hruska", DOC_DOMY,
     "Starší rodinný dom po čiastočnej rekonštrukcii (strecha 2021, okná 2022) na pozemku 900 m². "
     "Kúpele a cyklotrasa v pešej vzdialenosti. Vhodný aj na prestavbu na penzión."),
    ("INZ-203", "PredajnyInzerat", "Chata", "Obec_Terchova", 64, 3, 139000, "Makler_Hruska", DOC_DOMY,
     "Zrubová chata s krbom v obci Terchová, pozemok 410 m². Elektrina, vlastná studňa, žumpa. "
     "Ideálna na rekreáciu a krátkodobý prenájom turistom – Vrátna dolina 5 km."),
    ("INZ-204", "PredajnyInzerat", "StavebnyPozemok", "MC_Bytcica", 812, None, 89000, "Makler_Hruska", DOC_DOMY,
     "Rovinatý stavebný pozemok s prístupovou cestou, elektrina a voda na hranici pozemku, plyn v ulici. "
     "Podľa územného plánu určený na výstavbu rodinných domov."),
    ("INZ-205", "PredajnyInzerat", "StavebnyPozemok", "Obec_TeplickaNadVahom", 1050, None, 115000, "Makler_Hruska", DOC_DOMY,
     "Stavebný pozemok v novej lokalite rodinných domov, mierne svahovitý s výhľadom. Všetky inžinierske "
     "siete vrátane kanalizácie. Vydané územné rozhodnutie."),
    ("INZ-206", "PredajnyInzerat", "Zahrada", "MC_Zavodie", 420, None, 24000, "Makler_Hruska", DOC_DOMY,
     "Oplotená záhrada so záhradnou chatkou na náradie a ovocnými stromami. Voda zo studne. "
     "Pozemok NIE JE určený na výstavbu rodinného domu."),
    ("INZ-301", "NajomnyInzerat", "Garsonka", "MC_Hliny", 27, 1, 520, "Makler_Benova", DOC_PRENAJOM,
     "Zariadená garsónka na prenájom, 2. poschodie. Nájomné 520 € mesačne vrátane energií, kaucia vo výške "
     "jedného nájomného. Vhodná pre študenta alebo jednotlivca. Domáce zvieratá po dohode."),
    ("INZ-302", "NajomnyInzerat", "DvojizbovyByt", "MC_Vlcince", 55, 2, 720, "Makler_Benova", DOC_PRENAJOM,
     "Dvojizbový byt na dlhodobý prenájom, čiastočne zariadený. Nájomné 720 € mesačne + energie cca 150 €. "
     "Kaucia dve mesačné nájomné. Minimálna doba nájmu 1 rok."),
    ("INZ-303", "NajomnyInzerat", "TrojizbovyByt", "MC_StareMesto", 78, 3, 950, "Makler_Benova", DOC_PRENAJOM,
     "Trojizbový byt v centre na prenájom, kompletne zariadený, umývačka riadu, práčka so sušičkou. "
     "Nájomné 950 € mesačne + energie. Vhodné pre rodinu alebo zdieľané bývanie."),
    ("INZ-304", "NajomnyInzerat", "Kancelaria", "MC_StareMesto", 45, None, 650, "Makler_Benova", DOC_PRENAJOM,
     "Kancelária na prenájom na 1. poschodí administratívnej budovy, dve miestnosti, kuchynka, "
     "spoločné sociálne zariadenia. Optická sieť, recepcia. Nájomné 650 € mesačne + služby."),
    ("INZ-305", "NajomnyInzerat", "ObchodnyPriestor", "MC_Hliny", 96, None, 1400, "Makler_Benova", DOC_PRENAJOM,
     "Obchodný priestor na prízemí s výkladom do frekventovanej ulice, sklad 20 m², bezbariérový vstup. "
     "Vhodný pre predajňu alebo prevádzku služieb. Nájomné 1 400 € mesačne."),
    ("INZ-306", "NajomnyInzerat", "Kancelaria", "MC_Vlcince", 120, None, 1300, "Makler_Benova", DOC_PRENAJOM,
     "Open-space kancelária so zasadačkou, 4 parkovacie miesta v cene, klimatizácia. "
     "Nájomné 1 300 € mesačne + energie. Možnosť úpravy priestoru podľa potrieb nájomcu."),
]

TRIEDA_LABEL = {
    "Garsonka": "garsónka", "JednoizbovyByt": "jednoizbový byt", "DvojizbovyByt": "dvojizbový byt",
    "TrojizbovyByt": "trojizbový byt", "Byt": "štvorizbový byt", "RodinnyDom": "rodinný dom",
    "Chata": "chata", "StavebnyPozemok": "stavebný pozemok", "Zahrada": "záhrada",
    "Kancelaria": "kancelária", "ObchodnyPriestor": "obchodný priestor",
}

OBHLIADKY = [
    ("OBH-001", "PlanovanaObhliadka", "Klient_K001", "INZ-103", "2026-11-24"),
    ("OBH-002", "UskutocnenaObhliadka", "Klient_K001", "INZ-105", "2026-11-10"),
    ("OBH-003", "PlanovanaObhliadka", "Klient_K002", "INZ-201", "2026-11-26"),
]


def eur(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ") + " €"


def lok_full(lok_id: str) -> str:
    label, cls, parent = LOKALITY[lok_id]
    if cls == "MestskaCast":
        return f"{label} ({LOKALITY[parent][0]})"
    if cls == "Obec":
        return f"obec {label} (okres Žilina)"
    return label


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------
def register_fonts() -> tuple[str, str]:
    candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ]
    for regular, bold in candidates:
        if Path(regular).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont("Body", regular))
            pdfmetrics.registerFont(TTFont("Body-Bold", bold))
            return "Body", "Body-Bold"
    raise SystemExit("Nenašiel som TTF font s podporou diakritiky (DejaVu/Arial).")


FONT, FONT_B = register_fonts()
ss = getSampleStyleSheet()
S_TITLE = ParagraphStyle("t", parent=ss["Title"], fontName=FONT_B, fontSize=18, leading=22)
S_SUB = ParagraphStyle("s", parent=ss["Normal"], fontName=FONT, fontSize=9, textColor=colors.grey,
                       alignment=TA_CENTER, spaceAfter=10)
S_H = ParagraphStyle("h", parent=ss["Heading2"], fontName=FONT_B, fontSize=13, spaceBefore=10, spaceAfter=4)
S_P = ParagraphStyle("p", parent=ss["Normal"], fontName=FONT, fontSize=10, leading=14, spaceAfter=6)
S_CELL = ParagraphStyle("c", parent=S_P, fontSize=8.5, leading=11, spaceAfter=0)


def build_pdf(name: str, title: str, sections: list) -> None:
    """sections: list of ("h", text) | ("p", text) | ("table", rows) | ("sp", None)."""
    story = [Paragraph(title, S_TITLE), Paragraph(f"{FIRMA} · {ADRESA}", S_SUB)]
    for kind, val in sections:
        if kind == "h":
            story.append(Paragraph(val, S_H))
        elif kind == "p":
            story.append(Paragraph(val, S_P))
        elif kind == "table":
            rows = [[Paragraph(str(c), S_CELL) for c in r] for r in val]
            t = Table(rows, repeatRows=1, hAlign="LEFT")
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe8f1")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story += [t, Spacer(1, 8)]
        elif kind == "sp":
            story.append(Spacer(1, 8))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Dokument je fiktívny a slúži na študijné účely (predmet Sémantický web). "
                           "Nejde o právne ani finančné poradenstvo.", S_SUB))
    doc = SimpleDocTemplate(str(PDF_DIR / name), pagesize=A4, title=title, author=FIRMA,
                            leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm)
    doc.build(story)
    print("PDF:", name)


def listing_sections(items) -> list:
    out = []
    rows = [["ID", "Typ", "Lokalita", "Výmera", "Izby", "Cena"]]
    for i in items:
        iid, ityp, cls, lok, vym, izby, cena, mak, _doc, _p = i
        cena_s = eur(cena) + (" / mesiac" if ityp == "NajomnyInzerat" else "")
        rows.append([iid, TRIEDA_LABEL[cls], lok_full(lok), f"{vym} m²", izby or "–", cena_s])
    out.append(("h", "Prehľad ponuky"))
    out.append(("table", rows))
    for i in items:
        iid, ityp, cls, lok, vym, izby, cena, mak, _doc, popis = i
        typ = "Prenájom" if ityp == "NajomnyInzerat" else "Predaj"
        cena_s = (f"mesačné nájomné {eur(cena)}" if ityp == "NajomnyInzerat" else f"kúpna cena {eur(cena)}")
        izby_s = f", počet izieb: {izby}" if izby else ""
        out.append(("h", f"{iid} – {typ}: {TRIEDA_LABEL[cls]}, {lok_full(lok)}"))
        out.append(("p", f"<b>Výmera:</b> {vym} m²{izby_s}. <b>Cena:</b> {cena_s}. "
                         f"<b>Maklér:</b> {MAKLERI[mak][0]} ({MAKLERI[mak][3]})."))
        out.append(("p", popis))
    return out


# ---------------------------------------------------------------------------
# Dokumenty
# ---------------------------------------------------------------------------
def make_pdfs() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    by_doc = lambda d: [i for i in INZERATY if i[8] == d]  # noqa: E731

    build_pdf(DOC_BYTY, "Katalóg ponuky: byty na predaj (november 2026)", [
        ("p", "Tento katalóg obsahuje aktuálne predajné inzeráty bytov v meste Žilina. Ponúkame garsónky, "
              "jednoizbové, dvojizbové, trojizbové aj väčšie byty v mestských častiach Staré Mesto, Hliny, "
              "Vlčince, Solinky a Hájik. Všetky ceny sú uvedené vrátane provízie realitnej kancelárie."),
    ] + listing_sections(by_doc(DOC_BYTY)))

    build_pdf(DOC_DOMY, "Katalóg ponuky: rodinné domy, chaty a pozemky", [
        ("p", "Ponuka rezidenčných nehnuteľností typu dom (rodinné domy a chaty) a pozemkov v meste Žilina "
              "a v obciach okresu Žilina. Pri pozemkoch rozlišujeme stavebný pozemok (určený na výstavbu podľa "
              "územného plánu) a záhradu, na ktorej výstavba rodinného domu nie je povolená. Pri pozemkoch "
              "uvádzame výmeru pozemku, pri domoch úžitkovú plochu."),
    ] + listing_sections(by_doc(DOC_DOMY)))

    build_pdf(DOC_PRENAJOM, "Katalóg ponuky: prenájmy bytov a komerčných priestorov", [
        ("p", "Nájomné inzeráty – byty na dlhodobý prenájom a komerčné nehnuteľnosti (kancelárie a obchodné "
              "priestory). Pri nájomných inzerátoch je uvedená cena vždy mesačné nájomné. Komerčné priestory "
              "nemajú počet izieb, uvádzame len výmeru."),
    ] + listing_sections(by_doc(DOC_PRENAJOM)))

    build_pdf("04_vzor_kupnej_zmluvy.pdf", "Vzor a náležitosti kúpnej zmluvy na nehnuteľnosť", [
        ("p", "Kúpna zmluva je zmluva, ktorou predávajúci prevádza vlastnícke právo k nehnuteľnosti na kupujúceho "
              "a kupujúci sa zaväzuje zaplatiť kúpnu cenu. Predmetom kúpnej zmluvy je vždy konkrétna "
              "nehnuteľnosť (byt, dom, pozemok, komerčný priestor). Zmluva musí mať písomnú formu a podpisy "
              "účastníkov musia byť úradne osvedčené."),
        ("h", "Povinné náležitosti"),
        ("p", "1. Presná identifikácia zmluvných strán (meno, dátum narodenia, rodné číslo, trvalý pobyt). "
              "2. Presná identifikácia nehnuteľnosti podľa listu vlastníctva: katastrálne územie, číslo listu "
              "vlastníctva, parcelné číslo, pri byte číslo bytu, poschodie, vchod a spoluvlastnícky podiel na "
              "spoločných častiach domu. 3. Kúpna cena a spôsob jej úhrady. 4. Prejav vôle previesť "
              "vlastnícke právo. 5. Dátum a podpisy."),
        ("h", "Úhrada kúpnej ceny"),
        ("p", "Odporúčame úhradu cez notársku alebo advokátsku úschovu, prípadne cez vinkulovaný účet v banke. "
              "Peniaze sa predávajúcemu uvoľnia až po povolení vkladu vlastníckeho práva do katastra "
              "nehnuteľností v prospech kupujúceho. Pri financovaní hypotékou banka vyžaduje záložnú zmluvu."),
        ("h", "Vklad do katastra"),
        ("p", "Vlastnícke právo kupujúci nadobudne až povolením vkladu do katastra nehnuteľností na základe "
              "návrhu na vklad. Návrh podáva spravidla kupujúci alebo realitná kancelária v zastúpení. "
              "Okresný úrad – katastrálny odbor rozhoduje v zákonnej lehote; za zrýchlené konanie sa platí "
              "vyšší správny poplatok podľa aktuálneho sadzobníka."),
        ("h", "Rezervačná zmluva"),
        ("p", "Pred kúpnou zmluvou kancelária SemReal uzatvára s kupujúcim rezervačnú zmluvu. Rezervačný "
              "poplatok je 2 000 € pri bytoch a 3 000 € pri domoch a pozemkoch a započítava sa do kúpnej ceny. "
              "Rezervácia platí 30 dní, počas ktorých nehnuteľnosť nie je ponúkaná iným záujemcom."),
        ("h", "Kontrolný zoznam pred podpisom"),
        ("p", "Overiť list vlastníctva (ťarchy, záložné práva, vecné bremená); overiť, či predávajúci nemá "
              "nedoplatky voči správcovi domu; skontrolovať energetický certifikát; dohodnúť termín "
              "odovzdania nehnuteľnosti a spísať odovzdávací protokol so stavmi meračov."),
    ])

    build_pdf("05_vzor_najomnej_zmluvy.pdf", "Nájomná zmluva na byt: náležitosti a pravidlá", [
        ("p", "Nájomná zmluva upravuje dočasné užívanie nehnuteľnosti nájomcom za odplatu (nájomné). "
              "Prenajímateľ je vlastník nehnuteľnosti, ktorý ju prenajíma. Predmetom nájomnej zmluvy je "
              "konkrétna nehnuteľnosť – byt, rodinný dom alebo komerčný priestor (kancelária, obchodný priestor)."),
        ("h", "Obsah zmluvy"),
        ("p", "Zmluva obsahuje identifikáciu prenajímateľa a nájomcu, presné označenie bytu, výšku mesačného "
              "nájomného a zálohových platieb za služby (energie), spôsob a termín platby, dobu nájmu (určitú "
              "alebo neurčitú), výšku zábezpeky (kaucie), zoznam vybavenia a pravidlá pre domáce zvieratá."),
        ("h", "Kaucia (finančná zábezpeka)"),
        ("p", "Pri nájme bytu môže prenajímateľ požadovať zábezpeku najviac vo výške trojnásobku mesačného "
              "nájomného. V ponuke SemReal je kaucia zvyčajne jedno až dve mesačné nájomné. Kaucia sa vracia "
              "po skončení nájmu po odpočítaní prípadných škôd a nedoplatkov."),
        ("h", "Skončenie nájmu"),
        ("p", "Nájom na určitú dobu končí uplynutím doby. Nájom na neurčitú dobu možno ukončiť dohodou alebo "
              "výpoveďou z dôvodov uvedených v zákone; výpovedná lehota je spravidla tri mesiace. Pri "
              "odovzdaní bytu sa spíše protokol o stave bytu a stavoch meračov."),
        ("h", "Komerčné priestory"),
        ("p", "Pri prenájme kancelárií a obchodných priestorov sa nájomné často dohaduje bez energií a služieb, "
              "ktoré sa rozpočítavajú podľa plochy. Bežná je dlhšia doba nájmu (3 – 5 rokov) a indexácia "
              "nájomného podľa inflácie."),
    ])

    build_pdf("06_proces_obhliadky.pdf", "Ako prebieha obhliadka nehnuteľnosti", [
        ("p", "Obhliadka je osobná návšteva nehnuteľnosti záujemcom (kupujúcim alebo budúcim nájomcom) za "
              "prítomnosti makléra. Kancelária rozlišuje plánovanú obhliadku (rezervovaný termín, ktorý ešte "
              "neprebehol) a uskutočnenú obhliadku (už prebehla a je k nej spísaný záznam)."),
        ("h", "Rezervácia obhliadky"),
        ("p", "Kupujúci si obhliadku rezervuje telefonicky alebo e-mailom u makléra, ktorý spravuje daný "
              "inzerát. Pri rezervácii uvedie ID inzerátu (napr. INZ-103), preferovaný termín a počet osôb. "
              "Obhliadky prebiehajú v pracovné dni 8:00 – 18:00 a v sobotu 9:00 – 12:00. Rezerváciu je možné "
              "bezplatne zrušiť najneskôr 24 hodín vopred."),
        ("h", "Priebeh obhliadky"),
        ("p", "Maklér predstaví nehnuteľnosť, odovzdá kópiu listu vlastníctva a energetický certifikát. "
              "Odporúčame skontrolovať vlhkosť a plesne, stav okien, rozvody vody a elektriny, tlak vody, "
              "pivnicu, stav spoločných priestorov a hluk v rôznych častiach dňa. Obhliadka trvá 30 – 45 minút."),
        ("h", "Po obhliadke"),
        ("p", "Z uskutočnenej obhliadky maklér spíše krátky záznam a do 24 hodín kontaktuje záujemcu. Ak má "
              "záujemca záujem, nasleduje rezervačná zmluva (pri kúpe) alebo príprava nájomnej zmluvy "
              "(pri prenájme)."),
        ("h", "Evidencia obhliadok (november 2026)"),
        ("table", [["ID", "Stav", "Klient", "Inzerát", "Dátum"]] + [
            [o[0], "plánovaná" if o[1] == "PlanovanaObhliadka" else "uskutočnená",
             o[2].replace("Klient_", "klient "), o[3], o[4]] for o in OBHLIADKY]),
    ])

    build_pdf("07_lokality_zilina.pdf", "Sprievodca lokalitami: Žilina a okolie", [
        ("p", "Žilina je krajské mesto Žilinského kraja a sídlo okresu Žilina. Mesto sa člení na mestské "
              "časti, z ktorých najvýznamnejšie pre trh s bývaním sú uvedené nižšie. Hierarchia lokalít: "
              "mestská časť je súčasťou mesta, mesto a obce sú súčasťou okresu a okres je súčasťou kraja."),
        ("h", "Staré Mesto"),
        ("p", "Historické centrum s Mariánskym námestím. Prevažujú tehlové meštianske domy, vysoké stropy, "
              "obmedzené parkovanie. Najvyššie ceny bytov v meste, vhodné pre investíciu aj kancelárie."),
        ("h", "Hliny"),
        ("p", "Sídlisko v tesnej blízkosti centra, dobrá občianska vybavenosť a školy. Mix panelových domov a "
              "novostavieb, populárne medzi mladými rodinami aj študentmi."),
        ("h", "Vlčince"),
        ("p", "Najväčšie sídlisko v Žiline, výborná dostupnosť MHD, obchodné centrá, nemocnica v blízkosti. "
              "Väčšina domov je zateplená. Dobrý pomer ceny a kvality."),
        ("h", "Solinky"),
        ("p", "Sídlisko na juhovýchode mesta pri lesoparku Chrasť. Pokojné bývanie, nižšie ceny ako na Vlčincoch."),
        ("h", "Hájik"),
        ("p", "Tiché sídlisko v blízkosti Bôrika a Vodného diela Žilina, vhodné pre rodiny. Veľa zelene."),
        ("h", "Bánová, Bytčica a Závodie"),
        ("p", "Okrajové mestské časti s prevahou rodinných domov a nových lokalít pre výstavbu. Bánová je "
              "obľúbená pre rodinné domy, v Bytčici sú voľné stavebné pozemky, v Závodí záhrady a záhradkárske "
              "osady."),
        ("h", "Okolie Žiliny"),
        ("p", "Rajecké Teplice – kúpeľné mesto 15 km južne, rodinné domy s väčšími pozemkami. Terchová – obec v "
              "Malej Fatre, chaty a rekreačné objekty, potenciál krátkodobého prenájmu. Teplička nad Váhom – "
              "obec susediaca so Žilinou, rýchlo rastúca lokalita rodinných domov."),
    ])

    build_pdf("08_cennik_sluzieb.pdf", "Cenník služieb realitnej kancelárie", [
        ("p", "Cenník platí od 1. 9. 2026. Provízia sa platí až po úspešnom predaji alebo prenájme "
              "nehnuteľnosti."),
        ("table", [
            ["Služba", "Pre koho", "Cena"],
            ["Sprostredkovanie predaja bytu", "predávajúci", "3 % z kúpnej ceny, min. 3 000 €"],
            ["Sprostredkovanie predaja domu / pozemku", "predávajúci", "4 % z kúpnej ceny, min. 3 500 €"],
            ["Sprostredkovanie prenájmu bytu", "prenajímateľ", "1 mesačné nájomné"],
            ["Prenájom kancelárie / obchodného priestoru", "prenajímateľ", "2 mesačné nájomné"],
            ["Právny servis (kúpna zmluva, návrh na vklad)", "kupujúci / predávajúci", "v cene provízie"],
            ["Energetický certifikát", "predávajúci", "od 150 €"],
            ["Profesionálne foto a 3D obhliadka", "predávajúci", "v cene provízie"],
            ["Odhad trhovej ceny (bez zmluvy)", "ktokoľvek", "90 €"],
            ["Obhliadka nehnuteľnosti", "kupujúci / záujemca", "bezplatne"],
        ]),
        ("h", "Exkluzívna zmluva"),
        ("p", "Pri exkluzívnej zmluve o sprostredkovaní (min. 3 mesiace) znižujeme províziu o 0,5 percentuálneho "
              "bodu a nehnuteľnosť propagujeme na všetkých realitných portáloch."),
    ])

    build_pdf("09_tim_maklerov.pdf", "Náš tím maklérov", [
        ("p", "Každý inzerát spravuje jeden maklér, ktorý je kontaktnou osobou pre obhliadky aj zmluvy."),
    ] + sum([[("h", m[0]), ("p", f"<b>Špecializácia:</b> {m[1]}. <b>E-mail:</b> {m[2]}, <b>tel.:</b> {m[3]}. "
                                   f"<b>Spravované inzeráty:</b> "
                                   + ", ".join(i[0] for i in INZERATY if i[7] == mid) + ".")]
             for mid, m in MAKLERI.items()], []))

    build_pdf("10_sprievodca_kupou.pdf", "Sprievodca kupujúceho: kúpa nehnuteľnosti krok za krokom", [
        ("h", "1. Financovanie"),
        ("p", "Pred hľadaním si overte výšku hypotéky. Banky bežne financujú do 80 % hodnoty nehnuteľnosti "
              "(LTV), zvyšných 20 % a vedľajšie náklady (znalecký posudok, poplatky, rezervačný poplatok) "
              "hradí kupujúci z vlastných zdrojov. Mladí do 35 rokov môžu využiť zvýhodnené produkty bánk."),
        ("h", "2. Výber a obhliadka"),
        ("p", "Vyberte si typ nehnuteľnosti (byt, rodinný dom, pozemok) a lokalitu. Rezervujte si obhliadku u "
              "makléra. Odporúčame absolvovať aspoň dve obhliadky v rôznom čase dňa."),
        ("h", "3. Rezervácia"),
        ("p", "Podpisom rezervačnej zmluvy a úhradou rezervačného poplatku sa nehnuteľnosť stiahne z ponuky na "
              "30 dní. V tomto čase vybavíte úver a pripravíme kúpnu zmluvu."),
        ("h", "4. Kúpna zmluva a vklad"),
        ("p", "Kúpna zmluva sa podpisuje s úradne osvedčenými podpismi, kúpna cena ide do úschovy. Po povolení "
              "vkladu do katastra sa stávate vlastníkom a peniaze sa uvoľnia predávajúcemu."),
        ("h", "5. Odovzdanie a prepisy"),
        ("p", "Pri odovzdaní sa spíše protokol so stavmi meračov. Nový vlastník prepíše energie, prihlási sa u "
              "správcu domu a do 31. januára nasledujúceho roka podá priznanie k dani z nehnuteľností."),
        ("h", "Časté otázky"),
        ("p", "<b>Aký je rozdiel medzi garsónkou a jednoizbovým bytom?</b> Garsónka má jednu obytnú miestnosť s "
              "kuchynským kútom, jednoizbový byt má spravidla samostatnú kuchyňu. Obe majú jednu izbu."),
        ("p", "<b>Môžem stavať na záhrade?</b> Nie, záhrada nie je stavebný pozemok. Na výstavbu potrebujete "
              "pozemok určený územným plánom na výstavbu."),
    ])

    build_pdf("11_trhova_sprava_2026.pdf", "Trhová správa: bývanie v Žiline, 3. štvrťrok 2026", [
        ("p", "Ilustratívna správa realitnej kancelárie SemReal na základe vlastnej ponuky a dopytu. Čísla sú "
              "fiktívne a slúžia na študijné účely."),
        ("table", [
            ["Mestská časť", "Priem. cena bytu €/m²", "Zmena medziročne", "Priem. nájom €/m²"],
            ["Staré Mesto", "3 250", "+4,1 %", "12,5"],
            ["Hliny", "3 050", "+3,6 %", "12,0"],
            ["Vlčince", "2 700", "+2,9 %", "11,2"],
            ["Solinky", "2 650", "+3,1 %", "10,8"],
            ["Hájik", "2 600", "+2,5 %", "10,5"],
        ]),
        ("h", "Hlavné trendy"),
        ("p", "Najvyšší dopyt je po dvojizbových bytoch do 160 000 €, ktoré sa predávajú v priemere za 41 dní. "
              "Garsónky sú žiadané investormi na prenájom študentom (výnos 5 – 6 % ročne). Rodinné domy v "
              "Bánovej a Tepličke nad Váhom zdraželi o 5 %, ceny stavebných pozemkov v okolí Žiliny sa "
              "pohybujú od 90 do 140 € za m². Pri komerčných nehnuteľnostiach rastie dopyt po menších "
              "kanceláriách do 60 m² v centre."),
    ])


# ---------------------------------------------------------------------------
# ABox (instancie.ttl)
# ---------------------------------------------------------------------------
def make_ttl() -> None:
    L = []
    w = L.append
    w("@prefix :     <http://www.semanticweb.org/kubo/ontologies/2026/9/realitna-kancelaria#> .")
    w("@prefix rkx:  <http://www.semanticweb.org/kubo/ontologies/2026/9/realitna-kancelaria-rag#> .")
    w("@prefix owl:  <http://www.w3.org/2002/07/owl#> .")
    w("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    w("@prefix skos: <http://www.w3.org/2004/02/skos/core#> .")
    w("@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .\n")
    w("# Vygenerované skriptom tools/generate_data.py – inštancie (ABox) zodpovedajúce PDF dokumentom.\n")

    for lid, (label, cls, parent) in LOKALITY.items():
        if lid == "Mesto_Zilina":
            continue  # už je v pôvodnej ontológii
        w(f':{lid} a owl:NamedIndividual, :{cls} ; rdfs:label "{label}"@sk ; :jeSucastou :{parent} ; '
          f'rkx:zdrojovyDokument "07_lokality_zilina.pdf" .')
    w("")
    for mid, (name, spec, mail, tel) in MAKLERI.items():
        w(f':{mid} a owl:NamedIndividual, :Makler ; rdfs:label "{name}"@sk ; rkx:popis "{spec}"@sk ; '
          f'rkx:kontakt "{mail}, {tel}" ; rkx:zdrojovyDokument "09_tim_maklerov.pdf" .')
    w("")
    for iid, ityp, cls, lok, vym, izby, cena, mak, doc, popis in INZERATY:
        n = iid.replace("INZ-", "")
        neh, inz = f"Nehnutelnost_{n}", f"Inzerat_{n}"
        props = [f":nachadzaSaV :{lok}", f':vymera "{vym}"^^xsd:decimal']
        if izby:
            props.append(f':pocetIzieb "{izby}"^^xsd:integer')
        w(f':{neh} a owl:NamedIndividual, :{cls} ; rdfs:label "{TRIEDA_LABEL[cls]} – {lok_full(lok)} ({iid})"@sk ; '
          + " ; ".join(props) + f' ; rkx:zdrojovyDokument "{doc}" .')
        w(f':{inz} a owl:NamedIndividual, :{ityp} ; rdfs:label "{iid}"@sk ; :ponukaNehnutelnost :{neh} ; '
          f':cena "{cena}"^^xsd:decimal ; rkx:popis "{popis}"@sk ; rkx:zdrojovyDokument "{doc}" .')
        w(f':{mak} rkx:spravuje :{inz} .')
    w("")
    for kid in sorted({o[2] for o in OBHLIADKY}):
        w(f':{kid} a owl:NamedIndividual, :Kupujuci ; rdfs:label "klient {kid[-4:]}"@sk .')
    for oid, cls, kid, iid, datum in OBHLIADKY:
        o = oid.replace("-", "_")
        w(f':{o} a owl:NamedIndividual, :{cls} ; rdfs:label "{oid}"@sk ; '
          f':tykaSaNehnutelnosti :Nehnutelnost_{iid[4:]} ; rkx:datum "{datum}"^^xsd:date ; '
          f'rkx:zdrojovyDokument "06_proces_obhliadky.pdf" .'.replace(":tykaSa", "rkx:tykaSa"))
        w(f':{kid} :rezervujeObhliadku :{o} .')

    TTL_OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("TTL:", TTL_OUT)


if __name__ == "__main__":
    make_pdfs()
    make_ttl()
