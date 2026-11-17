# RAG so znalosťami z ontológie – realitná kancelária

**Predmet:** Sémantický web · **Zadanie:** RAG (12. týždeň)
**Doména:** realitná kancelária (Žilina a okolie), nadväzuje na ontológiu `realitna-kancelaria.owl` z predošlého zadania.

---

## 1. Zadanie a jeho interpretácia

| Bod zadania | Riešenie |
|---|---|
| Spojazdniť RAG u seba | Lokálny LLM `gemma3:4b` a embedding model `bge-m3` v **Ollame**, vektorová DB **ChromaDB**, všetko v **Docker Compose**. Nič nejde do cloudu. |
| Napojiť na ontológiu | Ontológia sa používa pri indexovaní (sémantická anotácia úryvkov), pri spracovaní otázky (rozpoznanie pojmov, rozšírenie dopytu, re-ranking) a pri generovaní (definície, axiómy a fakty zo SPARQL idú do promptu). Pozri [§3](#3-úloha-ontológie-v-systéme). |
| Pridať ±10 PDF z domény | 11 PDF dokumentov (katalógy ponúk, vzory zmlúv, proces obhliadky, lokality, cenník, tím maklérov, sprievodca kúpou, trhová správa). |
| Zabaliť do apky | Webová aplikácia v Streamlite (chat, prehliadač ontológie so SPARQL konzolou, správa dokumentov). |
| Dokumentácia | Tento dokument + `README.md` + výsledky evaluácie v `docs/evaluacia_*.md`. |

### Musia byť dokumenty prepojené s ontológiou?

Dokumenty **nemusia byť z ontológie vytvorené** a ani ju nemusia citovať. Stačí, keď sú z rovnakej domény. Prepojenie
**vytvára systém**: ontológia slúži ako spoločný slovník (schéma), cez ktorý systém dokumentom aj otázkam „rozumie“.
V tomto projekte je prepojenie spravené na troch úrovniach:

1. **Lexikálne:** triedy ontológie dostali slovenské názvy a synonymá (`rdfs:label`, `skos:altLabel`), aby sa
   dali nájsť v texte.
2. **Anotáciou úryvkov:** pri indexovaní sa každý úryvok PDF označí pojmami ontológie, ktoré obsahuje
   (napr. `Garsonka`, `MC_Vlcince`, `NajomnyInzerat`).
3. **Inštanciami (ABox):** inzeráty, lokality a makléri z PDF sú aj inštanciami ontológie. Každá nesie anotáciu
   `rkx:zdrojovyDokument` s názvom PDF, kde je popísaná. Tie isté dáta teda existujú raz ako neštruktúrovaný text
   (PDF) a raz ako štruktúrovaný znalostný graf.

Tretia úroveň nie je pre RAG povinná, ale ukazuje hlavnú výhodu ontológie: na presné otázky („ktoré byty do
100 000 € sú v Žiline“) odpovedá SPARQL nad grafom spoľahlivejšie ako vektorové vyhľadávanie v texte.

---

## 2. Architektúra

```
                ┌──────────────────────────── Docker Compose ─────────────────────────────┐
                │                                                                          │
 prehliadač ──► │  app (Streamlit, Python 3.12)                       ollama               │
 :8501          │  ┌────────────────────────────────────────┐       ┌──────────────────┐   │
                │  │ main.py      – UI (chat, ontológia,     │ HTTP  │ gemma3:4b  (LLM) │   │
                │  │               dokumenty)                │──────►│ bge-m3 (embed.)  │   │
                │  │ rag.py       – RAG pipeline             │       └──────────────────┘   │
                │  │ ontology.py  – rdflib, odvodzovanie,    │        volume: modely        │
                │  │               NER, SPARQL               │                              │
                │  │ index.py     – PDF → úryvky → ChromaDB  │                              │
                │  └────────────────────────────────────────┘                              │
                │      │ ./ontology/*.owl,*.ttl   │ ./data/pdfs/*.pdf   │ volume: /index      │
                └──────┼──────────────────────────┼─────────────────────┼────────────────────┘
                       ▼                          ▼                     ▼
                 TBox + lexikón + ABox       11 PDF dokumentov     ChromaDB (vektory + metadáta)
```

**Služby v `docker-compose.yml`:**

- `ollama` – server pre lokálne LLM (image `ollama/ollama`). Modely sú v pomenovanom volume, takže sa stiahnu len raz.
- `ollama-init` – jednorazový kontajner, ktorý stiahne modely (`ollama pull`) a skončí.
- `app` – Streamlit aplikácia. Spustí sa až keď sú modely stiahnuté. Priečinky `ontology/`, `data/` sú pripojené
  zvonka, takže stačí pridať PDF alebo upraviť ontológiu bez novej zostavy obrazu.
- `docker-compose.gpu.yml` – voliteľné rozšírenie pre NVIDIA GPU.

### Voľba modelov

| Komponent | Model | Prečo |
|---|---|---|
| LLM | `gemma3:4b` (3,3 GB, Q4) | Dobrá podpora slovenčiny pri malej veľkosti, beží aj na 16 GB RAM. |
| Alternatíva | `qwen2.5:3b` (1,9 GB) | Zmestí sa celý do 4 GB VRAM, takže je rýchlejší, ale po slovensky píše horšie. |
| Embeddingy | `bge-m3` (1,2 GB) | Viacjazyčný model (100+ jazykov vrátane slovenčiny). Anglické modely ako `nomic-embed-text` zlyhávajú na slovenskom skloňovaní. |
| Vektorová DB | ChromaDB (lokálna) | Ukladá vektory aj metadáta (anotácie pojmami ontológie), kosínová podobnosť. |

Testovací HW: Intel i5-10600KF, 16 GB RAM, NVIDIA GTX 1650 (4 GB). Embeddingy bežia na CPU
(`EMBED_NUM_GPU=0`), aby LLM dostal čo najviac VRAM.

---

## 3. Úloha ontológie v systéme

### 3.1 Vstupné súbory

| Súbor | Obsah |
|---|---|
| `ontology/realitna-kancelaria.owl` | **Pôvodná ontológia (TBox)**, nezmenená: 36 tried, 10 objektových a 3 dátové vlastnosti, axiómy (disjunktnosť, kardinality, `hasValue` definície izieb), 3 inštancie (Žilinský kraj, okres Žilina, mesto Žilina). |
| `ontology/lexikon.ttl` | **Lexikálne rozšírenie:** `rdfs:label`/`skos:altLabel`/`rdfs:comment` pre každú triedu a vlastnosť. Nová trieda `:Obec` a pomocné vlastnosti `rkx:spravuje`, `rkx:zdrojovyDokument`, `rkx:tykaSaNehnutelnosti`. Importuje pôvodnú ontológiu (`owl:imports`). |
| `ontology/instancie.ttl` | **ABox** vygenerovaný z rovnakých dát ako PDF: 12 lokalít, 3 makléri, 19 nehnuteľností, 19 inzerátov, obhliadky. |

Pôvodná ontológia mala iba IRI ako `:DvojizbovyByt`, bez slovenských názvov. Lexikón je preto nevyhnutný:
bez neho by systém nevedel, že slovo „dvojizbák“ v otázke znamená triedu `:DvojizbovyByt`.

### 3.2 Odvodzovanie (jednoduchý reasoner v `ontology.py`)

Po načítaní sa do grafu doplnia odvodené trojice (v UI metrika „odvodené“):

- **Triedy definované cez `owl:intersectionOf`:** `DvojizbovyByt ≡ Byt ⊓ (pocetIzieb = 2)` ⇒ `DvojizbovyByt ⊑ Byt`.
- **Klasifikácia cez `hasValue`:** `Garsonka ⊑ Byt` a `Garsonka ⊑ (pocetIzieb = 1)` ⇒ `Garsonka ⊑ JednoizbovyByt`.
  Vďaka tomu otázka na „jednoizbové byty“ vráti aj garsónky.
- **Typovanie inštancií:** byt s `pocetIzieb = 2` je inštanciou `DvojizbovyByt`.
- **Inverzné vlastnosti:** z `ponukaNehnutelnost` vznikne `jePonukanaV`, z `jeSucastou` vznikne `zahrna` atď.
- **Tranzitivita `jeSucastou`** sa rieši v SPARQL cestou `:jeSucastou*` (Vlčince → Žilina → okres → kraj).

### 3.3 Kde sa ontológia používa v RAG pipeline

```
Otázka: „Ktoré jednoizbové byty máte na predaj v Žiline?“
   │
   ├─(1) Rozpoznanie pojmov (lexikón + tolerancia na skloňovanie)
   │      „jednoizbové byty“ → :JednoizbovyByt, „na predaj“ → :PredajnyInzerat, „Žiline“ → :Mesto_Zilina
   │
   ├─(2) Rozšírenie dopytu o podtriedy/nadtriedy
   │      + „garsónka, byt, inzerát, mesto …“  → embedding rozšíreného dopytu (bge-m3)
   │
   ├─(3) Vektorové vyhľadávanie v ChromaDB (top-20) + RE-RANKING
   │      skóre = kosínová podobnosť + 0,04 × (počet spoločných pojmov ontológie, max. +0,12)
   │      spoločné pojmy = pojmy otázky vrátane podtried ∩ anotácie úryvku vrátane nadtried
   │
   ├─(4) SPARQL nad znalostným grafom (ABox)
   │      ?neh a/rdfs:subClassOf* :JednoizbovyByt ; ?inz a/rdfs:subClassOf* :PredajnyInzerat ;
   │      ?lok :jeSucastou* :Mesto_Zilina  → INZ-101 (garsónka, 98 000 €), INZ-102 (115 000 €)
   │      cenové ohraničenie z otázky („do 100 000 €“, „od 500 eur“) sa pridá ako FILTER(?cena <= …)
   │
   ├─(5) Ontologický kontext: definícia, hierarchia, axiómy, disjunktnosť
   │      „garsónka ⊑ jednoizbový byt ⊑ byt ⊑ rezidenčná nehnuteľnosť ⊑ nehnuteľnosť; počet izieb = 1“
   │
   └─(6) Prompt = [ONT] ontológia + [KG] fakty + [D1..D5] úryvky PDF + otázka → gemma3:4b → odpoveď s citáciami
```

Príklad, kde axióm z ontológie priamo určuje odpoveď: na otázku *„Môžem si na záhrade v Závodí postaviť rodinný
dom?“* model dostane z ontológie `Zahrada` **disjunktná so** `StavebnyPozemok` a odpovie „Nie“ s odkazom [ONT].

### 3.4 Sémantická anotácia dokumentov

Pri indexovaní sa každý úryvok PDF prejde rozpoznávačom pojmov a do metadát v ChromaDB sa uloží zoznam
pojmov (napr. `DvojizbovyByt|MC_Solinky|PredajnyInzerat|Makler_Kovacova`). Záložka **Dokumenty** v aplikácii
ukazuje, ktoré pojmy ontológie sa v ktorom PDF vyskytujú najčastejšie, teda ako sú dokumenty „namapované“ na
ontológiu.

Rozpoznávanie pojmov (`Ontology.find`) nepoužíva ťažký NLP model. Je to slovníkové vyhľadávanie:

- normalizácia (malé písmená, odstránenie diakritiky),
- najprv najdlhšia zhoda (aby „mestská časť“ vyhrala nad „mesto“),
- porovnávanie slov so zhodou prefixu (`byt ~ bytu ~ byty`, `garsónka ~ garsónku`, `Vlčince ~ Vlčincoch`),
  čo nahrádza lematizáciu slovenčiny.

---

## 4. Doménové dokumenty

11 PDF v `data/pdfs/`, spolu 14 strán (31 úryvkov v indexe). Sú **fiktívne** (fiktívna kancelária *SemReal Žilina, s.r.o.*,
vymyslené osoby a ceny). Generuje ich skript `tools/generate_data.py` z jedného zdroja dát, ktorý zároveň
vytvorí `instancie.ttl`. PDF a ontológia sú preto navzájom konzistentné.

| PDF | Obsah | Hlavné pojmy ontológie |
|---|---|---|
| 01_ponuka_bytov_na_predaj | 7 predajných inzerátov bytov | Garsonka, Jedno/Dvoj/TrojizbovyByt, PredajnyInzerat, MestskaCast |
| 02_ponuka_domov_chat_pozemkov | rodinné domy, chata, pozemky, záhrada | RodinnyDom, Chata, StavebnyPozemok, Zahrada, Obec |
| 03_ponuka_prenajmov | prenájom bytov, kancelárií, obchodných priestorov | NajomnyInzerat, Kancelaria, ObchodnyPriestor |
| 04_vzor_kupnej_zmluvy | náležitosti kúpnej zmluvy, vklad do katastra, rezervácia | KupnaZmluva, Predavajuci, Kupujuci |
| 05_vzor_najomnej_zmluvy | nájomná zmluva, kaucia, výpoveď | NajomnaZmluva, Prenajimatel |
| 06_proces_obhliadky | rezervácia a priebeh obhliadky, evidencia | Obhliadka, PlanovanaObhliadka, UskutocnenaObhliadka |
| 07_lokality_zilina | mestské časti Žiliny a okolie | Kraj, Okres, Mesto, MestskaCast, Obec |
| 08_cennik_sluzieb | provízie a poplatky | Predavajuci, Prenajimatel, Kupujuci |
| 09_tim_maklerov | makléri a ich inzeráty | Makler |
| 10_sprievodca_kupou | hypotéka, kroky kúpy, časté otázky | KupnaZmluva, Garsonka vs. JednoizbovyByt |
| 11_trhova_sprava_2026 | ceny za m² podľa mestských častí | MestskaCast, Byt |

Ďalšie (aj reálne) PDF sa dajú pridať v aplikácii (záložka Dokumenty → nahrať) alebo skopírovaním do
`data/pdfs/`. Index sa po zmene automaticky prebuduje. Vhodné reálne zdroje sú napr. zákony zo Slov-Lex
(č. 182/1993 Z. z. o vlastníctve bytov, č. 162/1995 Z. z. katastrálny zákon, Občiansky zákonník – nájom bytu).

---

## 5. Aplikácia

**Chat**
- odpoveď sa streamuje, za ňou sú rozbaľovacie panely:
  - 🧠 rozpoznané pojmy, rozšírenie dopytu a ontologický kontext,
  - 🔗 fakty zo znalostného grafu vrátane vykonaného SPARQL dopytu,
  - 📄 zdroje (PDF, strana, podobnosť, bonus z ontológie).
- prepínač **Použiť ontológiu** v bočnom paneli umožňuje porovnať s obyčajným RAG.

**Ontológia**
- štatistiky (triedy, inštancie, assertované/odvodené trojice),
- strom tried, detail triedy (definícia, axiómy, disjunktnosť, vlastnosti), test rozpoznávania pojmov,
- **SPARQL konzola** s príkladmi (byty do 160 000 € so subsumpciou, tranzitívne lokality, agregácia podľa
  makléra, prepojenie inštancií na PDF).

**Dokumenty**
- prehľad zaindexovaných PDF a pojmov ontológie v nich, nahrávanie nových PDF, preindexovanie.

---

## 6. Inštalácia a spustenie

Požiadavky: Docker Desktop (Windows/macOS) alebo Docker Engine (Linux), aspoň 8 GB RAM pre Docker, asi 8 GB
miesta na disku.

```bash
git clone https://github.com/KubecBubec/RAG-zadanie.git
cd RAG-zadanie
docker compose up -d                                                   # CPU
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d   # NVIDIA GPU
```

Aplikácia: <http://localhost:8501>. Ollama API: <http://localhost:11434>.

| Premenná (`.env`) | Predvolená hodnota | Význam |
|---|---|---|
| `LLM_MODEL` | `gemma3:4b` | generatívny model v Ollame |
| `EMBED_MODEL` | `bge-m3` | embedding model |
| `NUM_CTX` | `6144` | veľkosť kontextového okna |
| `EMBED_NUM_GPU` | `0` | 0 = embeddingy na CPU; prázdne = automaticky |
| `LLM_NUM_GPU` | prázdne | počet vrstiev LLM na GPU (prázdne = automaticky); pri malej VRAM pomôže znížiť, aby ovládač nepresúval pamäť do RAM |

Užitočné príkazy:

```bash
docker compose logs -f app                                          # logy aplikácie
docker compose run --rm app python /workspace/tools/generate_data.py   # pregenerovanie PDF + inštancií
docker compose exec app python /workspace/tools/evaluate.py         # evaluácia s/bez ontológie
docker compose down                                                 # zastavenie (modely ostanú vo volume)
```

---

## 7. Evaluácia

Skript `tools/evaluate.py` položí 7 testovacích otázok v dvoch režimoch (bez ontológie a s ontológiou). Skóre je
podiel očakávaných kľúčových údajov (ID inzerátov, „nie“, „4 %“…), ktoré odpoveď obsahuje. Úplné odpovede sú v
`docs/evaluacia_<model>.md`.

**gemma3:4b** ([úplné odpovede](evaluacia_gemma3_4b.md))

| Otázka | Bez ontológie | S ontológiou |
|---|---|---|
| Ktoré jednoizbové byty máte na predaj v Žiline? | 50 % | **100 %** |
| Môžem si na záhrade v Závodí postaviť rodinný dom? | 100 % | 100 % |
| Aké nehnuteľnosti ponúkate v meste Žilina do 100 000 €? | 33 % | **67 %** |
| Ktoré nehnuteľnosti spravuje Peter Hruška? | 100 % | 100 % |
| Aká je kaucia pri prenájme bytu? | 100 % | 0 % |
| Koľko stojí provízia pri predaji domu? | 100 % | 100 % |
| Kedy sú naplánované obhliadky? | 100 % | 100 % |
| **Priemer** | **83 %** | **81 %** |

**qwen2.5:3b** ([úplné odpovede](evaluacia_qwen2.5_3b.md)): priemer **21 % bez ontológie, 43 % s ontológiou**.
Odpoveď trvá 11 – 20 s, kým pri gemma3:4b je to 22 – 86 s (GTX 1650).

**Čo z toho vyplýva:**

- Ontológia pomáha najmä pri **štruktúrovaných otázkach**, kde treba spojiť pojmy a hierarchie:
  - „jednoizbové byty“ musia zahŕňať aj garsónky, čo zabezpečí odvodené `Garsonka ⊑ JednoizbovyByt`,
  - „v Žiline“ musí zahŕňať aj mestské časti, čo zabezpečí `jeSucastou*`,
  - cenový limit rieši SPARQL filter.
  
  Obyčajný RAG v týchto prípadoch nájde len časť inzerátov alebo prevezme nesprávne ceny z tabuľky.
- Pri otázkach na **text dokumentov** (kaucia, provízia) ontológia nepridá informáciu. Môže len posunúť
  poradie úryvkov. Pri kaucii model s ontológiou uviedol iba zvyklosť kancelárie (1 – 2 nájomné) a vynechal
  zákonné maximum.
- Menší model (qwen 3B) z ontológie profituje viac (21 % → 43 %), lebo štruktúrované fakty mu uľahčujú
  odpoveď. Často však vynechá ID inzerátov, a preto ho prísna metrika penalizuje, aj keď sú nehnuteľnosti
  vymenované správne.
- Metrika je jednoduchá (hľadanie kľúčových údajov v texte) a sada má len 7 otázok, takže výsledky sú
  orientačné. Malé modely nie sú úplne deterministické a pri opakovaní sa skóre jednotlivých otázok môže líšiť.

---

## 8. Obmedzenia a možné rozšírenia

- **Rozpoznávanie pojmov** je slovníkové. Nové slová treba doplniť do `lexikon.ttl`. Lepšie by fungoval
  lematizátor slovenčiny (napr. Stanza/UDPipe) alebo LLM, ktorý namapuje otázku na pojmy ontológie.
- **Reasoner** pokrýva len použité konštrukcie OWL (intersectionOf, hasValue, inverseOf). Pre plné OWL DL by
  sa dal použiť HermiT/Pellet (napr. cez `owlready2`) a jeho výsledok uložiť ako odvodený graf.
- **Číselné podmienky:** jednoduchý parser zachytí len cenu („do/pod/od/nad X €“). Sumy nad 5 000 € berie ako
  kúpnu cenu, menšie ako mesačné nájomné. Všeobecnejšie riešenie je text-to-SPARQL, kde LLM generuje celý dopyt.
- **Výkon:** na GPU so 4 GB VRAM sa `gemma3:4b` zmestí len čiastočne, takže odpoveď trvá desiatky sekúnd.
  Menší model (`qwen2.5:3b`) je rýchlejší za cenu horšej slovenčiny.
- Dokumenty sú fiktívne. Pri reálnych dokumentoch (zákony) by bolo vhodné deliť text podľa paragrafov.
