# Evaluácia: RAG bez ontológie vs. s ontológiou
Model: `gemma3:4b`, embeddingy: `bge-m3`, top-k = 5
Skóre = podiel očakávaných kľúčových údajov, ktoré odpoveď obsahuje.

## 1. Ktoré jednoizbové byty máte na predaj v Žiline?

*Očakávané:* INZ-101, INZ-102

### Bez ontológie — skóre 1/2, 86.0 s
*Zdroje:* 01_ponuka_bytov_na_predaj.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1, 03_ponuka_prenajmov.pdf:1, 11_trhova_sprava_2026.pdf:1

> Máme k dispozícii nasledovné jednoizbové byty na predaj v Žiline:
> 
> *   **ID inzerátu:** INZ-102
>     *   **Typ nehnuteľnosti:** jednoizbový byt
>     *   **Lokalita:** Hliny (Žilina)
>     *   **Výmera:** 36 m²
>     *   **Cena:** 115 000 € [D2]

### S ontológiou — skóre 2/2, 61.2 s
*Rozpoznané pojmy:* jednoizbový byt, predajný inzerát, Žilina  
*Fakty z KG:* 2  
*Zdroje:* 01_ponuka_bytov_na_predaj.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1, 03_ponuka_prenajmov.pdf:1, 11_trhova_sprava_2026.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1

> Máme k dispozícii nasledujúce jednoizbové byty na predaj v Žiline:
> 
> *   **INZ-101**: garsónka, Vlčince (Žilina), výmera 28 m², počet izieb 1, cena 98 000 €. [KG]
> *   **INZ-102**: jednoizbový byt, Hliny (Žilina), výmera 36 m², počet izieb 1, cena 115 000 €. [KG]

## 2. Môžem si na záhrade v Závodí postaviť rodinný dom?

*Očakávané:* nie

### Bez ontológie — skóre 1/1, 32.4 s
*Zdroje:* 02_ponuka_domov_chat_pozemkov.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:2, 07_lokality_zilina.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1

> Na základe poskytnutých dokumentov [D1], [D2] a [D3] je odpoveď nasledovná:
> 
> Nie, na záhrade v Závodí (Žilina) uvedenej v inzeráte INZ-206, **nie je určená na výstavbu rodinného domu**. [D2]  Záhradná záhrada má výmeru 420 m² a cena je 24 000 €. Dokument [D2] jasne uvádza, že "Oplotená záhrada so záhradnou chatkou na náradie a ovocnými stromami. Voda zo studne. Pozemok NIE JE určený na výstavbu rodinného domu."

### S ontológiou — skóre 1/1, 36.4 s
*Rozpoznané pojmy:* záhrada, Závodie, rodinný dom  
*Fakty z KG:* 1  
*Zdroje:* 02_ponuka_domov_chat_pozemkov.pdf:1, 07_lokality_zilina.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:2, 02_ponuka_domov_chat_pozemkov.pdf:1, 07_lokality_zilina.pdf:1

> Na základe poskytnutých informácií, konkrétne [D1] a [D3], odpoveď znie:
> 
> Nie, na záhradu v Závodí (INZ-206) **nie je povolené** postaviť rodinný dom. Záhrada je definovaná ako "záhrada, na ktorej výstavba rodinného domu nie je povolená" [ONT] a konkrétne inzerát [KG] uvádza výmeru 420 m² a cenu 24 000 €.  [D3] zdôrazňuje, že ide o "Oplotená záhrada so záhradnou chatkou na náradie a ovocnými stromami. Voda zo studne. Pozemok NIE JE určený na výstavbu rodinného domu."

## 3. Aké nehnuteľnosti ponúkate v meste Žilina do 100 000 €?

*Očakávané:* INZ-101, INZ-204, INZ-206

### Bez ontológie — skóre 1/3, 37.5 s
*Zdroje:* 07_lokality_zilina.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1, 11_trhova_sprava_2026.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1

> Na základe poskytnutých informácií ponúkame nasledujúce nehnuteľnosti v meste Žilina s cenou do 100 000 €:
> 
> *   **ID inzerátu:** INZ-101
>     *   **Typ nehnuteľnosti:** garsónka
>     *   **Lokalita:** Vlčince (Žilina)
>     *   **Výmera:** 28 m²
>     *   **Cena:** 98 000 €
> *   **ID inzerátu:** INZ-102
>     *   **Typ nehnuteľnosti:** jednoizbový byt
>     *   **Lokalita:** Hliny (Žilina)
>     *   **Výmera:** 36 m²
>     *   **Cena:** 1 115 000 € (Táto nehnuteľnosť presahuje stanovený rozpočet, ale uvádzame ju pre úplnosť informácií.)

### S ontológiou — skóre 2/3, 31.6 s
*Rozpoznané pojmy:* nehnuteľnosť, inzerát, mesto, Žilina  
*Fakty z KG:* 3  
*Zdroje:* 02_ponuka_domov_chat_pozemkov.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1, 03_ponuka_prenajmov.pdf:1, 11_trhova_sprava_2026.pdf:1

> Ponúkame nasledujúce nehnuteľnosti v meste Žilina do 100 000 €:
> 
> *   INZ-101: garsónka, Vlčince (Žilina), výmera 28 m², počet izieb 1, cena 98 000 €
> *   INZ-204: stavebný pozemok, Bytčica → Žilina, výmera 812 m², cena 89 000 €

## 4. Ktoré nehnuteľnosti spravuje Peter Hruška?

*Očakávané:* INZ-201, INZ-203, INZ-204

### Bez ontológie — skóre 3/3, 42.8 s
*Zdroje:* 02_ponuka_domov_chat_pozemkov.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:2, 09_tim_maklerov.pdf:1, 10_sprievodca_kupou.pdf:1, 04_vzor_kupnej_zmluvy.pdf:1

> Ing. Peter Hruška spravuje nasledovné inzeráty:
> 
> *   **INZ-201** – Predaj: chata, obec Terchová (okres Žilina) Výmera: 64 m², počet izieb: 3. Cena: kúpna cena 139 000 €.
> *   **INZ-202** – Predaj: stavebný pozemok, Bytčica (Žilina) Výmera: 812 m². Cena: kúpna cena 89 000 €.
> *   **INZ-203** – Predaj: stavebný pozemok, obec Teplička nad Váhom (okres Žilina) Výmera: 1050 m². Cena: kúpna cena 115 000 €.
> *   **INZ-204** – Predaj: záhrada, Závodie (Žilina) Výmera: 420 m². Cena: kúpna cena 24 000 €. [D1]

### S ontológiou — skóre 3/3, 60.9 s
*Rozpoznané pojmy:* nehnuteľnosť, Ing. Peter Hruška  
*Fakty z KG:* 6  
*Zdroje:* 02_ponuka_domov_chat_pozemkov.pdf:1, 10_sprievodca_kupou.pdf:1, 09_tim_maklerov.pdf:1, 05_vzor_najomnej_zmluvy.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1

> Ing. Peter Hruška spravuje nasledovné nehnuteľnosti:
> 
> *   INZ-203 – Predaj: chata, obec Terchová (okres Žilina) Výmera: 64 m², počet izieb: 3. Cena: kúpna cena 139 000 €. [KG]
> *   INZ-204 – Predaj: stavebný pozemok, Bytčica (Žilina) Výmera: 812 m². Cena: kúpna cena 89 000 €. [KG]
> *   INZ-205 – Predaj: stavebný pozemok, Teplička nad Váhom → okres Žilina, 1050 m², cena 115 000 €. [KG]
> *   INZ-206 – Predaj: záhrada – Závodie → Žilina, 420 m², cena 24 000 €. [KG]
> *   INZ-201 – Predaj: rodinný dom – Bánová → Žilina, 142 m², počet izieb 5, cena 345 000 €. [KG]
> *   INZ-202 – Predaj: rodinný dom – Rajecké Teplice → okres Žilina, 168 m², počet izieb 6, cena 289 000 €. [KG]

## 5. Aká je kaucia pri prenájme bytu?

*Očakávané:* trojnásob

### Bez ontológie — skóre 1/1, 22.0 s
*Zdroje:* 05_vzor_najomnej_zmluvy.pdf:1, 05_vzor_najomnej_zmluvy.pdf:1, 04_vzor_kupnej_zmluvy.pdf:1, 08_cennik_sluzieb.pdf:1, 04_vzor_kupnej_zmluvy.pdf:1

> Kaucia pri prenájme bytu v SemReal Žilina je zvyčajne jedno až dve mesačné nájomné. [D1], [D2]  Prenajímateľ môže požadovať zábezpeku najviac vo výške trojnásobku mesačného nájomného. [D2]

### S ontológiou — skóre 0/1, 28.0 s
*Rozpoznané pojmy:* nájomný inzerát, byt  
*Fakty z KG:* 0  
*Zdroje:* 05_vzor_najomnej_zmluvy.pdf:1, 05_vzor_najomnej_zmluvy.pdf:1, 03_ponuka_prenajmov.pdf:1, 10_sprievodca_kupou.pdf:1, 03_ponuka_prenajmov.pdf:1

> Kaucia pri prenájme bytu môže byť vo výške jedno až dve mesačné nájomné. [D1], [D2]  Konkrétne, inzeráty INZ-302 a INZ-303 uvádzajú kauciu vo výške jedného alebo dvoch nájomných. [D3]

## 6. Koľko stojí provízia pri predaji domu?

*Očakávané:* 4 %

### Bez ontológie — skóre 1/1, 27.5 s
*Zdroje:* 08_cennik_sluzieb.pdf:1, 08_cennik_sluzieb.pdf:1, 04_vzor_kupnej_zmluvy.pdf:1, 04_vzor_kupnej_zmluvy.pdf:1, 11_trhova_sprava_2026.pdf:1

> Provízia pri predaji domu podľa [D2] je 4 % z kúpnej ceny, minimálne 3 500 €.  [KG]

### S ontológiou — skóre 1/1, 35.3 s
*Rozpoznané pojmy:* predajný inzerát, dom  
*Fakty z KG:* 0  
*Zdroje:* 08_cennik_sluzieb.pdf:1, 08_cennik_sluzieb.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1, 11_trhova_sprava_2026.pdf:1

> Provízia pri predaji domu podľa [D1] je 4 % z kúpnej ceny, minimálne 3 500 €. [D1]

## 7. Kedy sú naplánované obhliadky?

*Očakávané:* 2026-11-24, 2026-11-26

### Bez ontológie — skóre 2/2, 63.1 s
*Zdroje:* 06_proces_obhliadky.pdf:1, 06_proces_obhliadky.pdf:1, 10_sprievodca_kupou.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1, 01_ponuka_bytov_na_predaj.pdf:2

> Obhliadky sú naplánované v pracovné dni od 8:00 do 18:00 a v sobotu od 9:00 do 12:00 [D1]. Rezervácia obhliadky sa uskutočňuje telefonicky alebo e-mailom u makléra, ktorý spravuje inzerát [D1].  Konkrétne termíny obhliadok pre inzeráty sú nasledovné:
> 
> *   INZ-103: 2026-11-24 [D2]
> *   INZ-105: 2026-11-10 [D2]
> *   INZ-201: 2026-11-26 [D2]

### S ontológiou — skóre 2/2, 46.5 s
*Rozpoznané pojmy:* obhliadka  
*Fakty z KG:* 3  
*Zdroje:* 06_proces_obhliadky.pdf:1, 06_proces_obhliadky.pdf:1, 10_sprievodca_kupou.pdf:1, 04_vzor_kupnej_zmluvy.pdf:1, 10_sprievodca_kupou.pdf:1

> Na plánované obhliadky sú naplánované nasledovné termíny:
> 
> *   2026-11-24 (plánovaná obhliadka, INZ-103, dvojizbový byt – Solinky (Žilina), klient K001)
> *   2026-11-26 (plánovaná obhliadka, INZ-201, rodinný dom – Bánová (Žilina), klient K002) [KG]

## Súhrn

| Otázka | Bez ontológie | S ontológiou |
|---|---|---|
| Ktoré jednoizbové byty máte na predaj v Žiline? | 50% (86 s) | 100% (61 s) |
| Môžem si na záhrade v Závodí postaviť rodinný dom? | 100% (32 s) | 100% (36 s) |
| Aké nehnuteľnosti ponúkate v meste Žilina do 100 000 €? | 33% (37 s) | 67% (32 s) |
| Ktoré nehnuteľnosti spravuje Peter Hruška? | 100% (43 s) | 100% (61 s) |
| Aká je kaucia pri prenájme bytu? | 100% (22 s) | 0% (28 s) |
| Koľko stojí provízia pri predaji domu? | 100% (27 s) | 100% (35 s) |
| Kedy sú naplánované obhliadky? | 100% (63 s) | 100% (46 s) |
| **Priemer** | **83%** | **81%** |
