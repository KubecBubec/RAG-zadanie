# Evaluácia: RAG bez ontológie vs. s ontológiou
Model: `qwen2.5:3b`, embeddingy: `bge-m3`, top-k = 5
Skóre = podiel očakávaných kľúčových údajov, ktoré odpoveď obsahuje.

## 1. Ktoré jednoizbové byty máte na predaj v Žiline?

*Očakávané:* INZ-101, INZ-102

### Bez ontológie — skóre 1/2, 120.1 s
*Zdroje:* 01_ponuka_bytov_na_predaj.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1, 03_ponuka_prenajmov.pdf:1, 11_trhova_sprava_2026.pdf:1

> Na predaj máme inzerát ID INZ-102 - jednoizbový byt v Hliny s výmerami 36 m² a cenou kúpna 115 000 €.

### S ontológiou — skóre 0/2, 16.5 s
*Rozpoznané pojmy:* jednoizbový byt, predajný inzerát, Žilina  
*Fakty z KG:* 2  
*Zdroje:* 01_ponuka_bytov_na_predaj.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1, 03_ponuka_prenajmov.pdf:1, 11_trhova_sprava_2026.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1

> Na predaj máme jednoizbový byt v Hliny, Žilina s cenou 115 000 €.

## 2. Môžem si na záhrade v Závodí postaviť rodinný dom?

*Očakávané:* nie

### Bez ontológie — skóre 0/1, 13.6 s
*Zdroje:* 02_ponuka_domov_chat_pozemkov.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:2, 07_lokality_zilina.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1

> Áno, môžete si na záhrade v Závodí postaviť rodinný dom. V dokumente [D3] (07_lokality_zilina.pdf, strana 1) je uveden, že okolie Žiliny Rajecké Teplice sú obľúbené pre rodinné domy, a v Závodí sú voľné stavebné pozemky. Výsledná cena pre stavebný pozemok v Závodí je 89 000 €.

### S ontológiou — skóre 1/1, 15.8 s
*Rozpoznané pojmy:* záhrada, Závodie, rodinný dom  
*Fakty z KG:* 1  
*Zdroje:* 02_ponuka_domov_chat_pozemkov.pdf:1, 07_lokality_zilina.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:2, 02_ponuka_domov_chat_pozemkov.pdf:1, 07_lokality_zilina.pdf:1

> Áno, je možné si na záhrade v Závodí postaviť rodinný dom. Na základe zdrojov, máte ponuku záhrady v Závodí, Žilina s výmerou 420 m² a cenou 24 000 €. Táto záhrada nie je určená na výstavbu rodinného domu, čo je potrebné podľa pravidel.

## 3. Aké nehnuteľnosti ponúkate v meste Žilina do 100 000 €?

*Očakávané:* INZ-101, INZ-204, INZ-206

### Bez ontológie — skóre 1/3, 11.6 s
*Zdroje:* 07_lokality_zilina.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1, 11_trhova_sprava_2026.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1

> Pri základe poskytnutého kontextu, SemReal Žilina ponúka následné nehnuteľnosti do 100 000 €:
> 
> - INZ-101: garsónka v Vlčince, cena 98 000 €

### S ontológiou — skóre 0/3, 17.6 s
*Rozpoznané pojmy:* nehnuteľnosť, inzerát, mesto, Žilina  
*Fakty z KG:* 3  
*Zdroje:* 02_ponuka_domov_chat_pozemkov.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1, 01_ponuka_bytov_na_predaj.pdf:1, 03_ponuka_prenajmov.pdf:1, 11_trhova_sprava_2026.pdf:1

> V meste Žilina do 100 000 € ponúkame:
> 
> 1. Garsónka v Vlčince, 28 m², cena 98 000 €, maklér Mgr. Jana Kováčová [D1]
> 
> Tento inzerát je jediný výsledok hľadania v meste Žilina do 100 000 €.

## 4. Ktoré nehnuteľnosti spravuje Peter Hruška?

*Očakávané:* INZ-201, INZ-203, INZ-204

### Bez ontológie — skóre 2/3, 12.8 s
*Zdroje:* 02_ponuka_domov_chat_pozemkov.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:2, 09_tim_maklerov.pdf:1, 10_sprievodca_kupou.pdf:1, 04_vzor_kupnej_zmluvy.pdf:1

> Peter Hruška spravuje inzeráty typu "rodinné domy", "chaty" a "pozemky". Idúce správne idy sú INZ-203, INZ-204 a INZ-205.

### S ontológiou — skóre 0/3, 18.9 s
*Rozpoznané pojmy:* nehnuteľnosť, Ing. Peter Hruška  
*Fakty z KG:* 6  
*Zdroje:* 02_ponuka_domov_chat_pozemkov.pdf:1, 10_sprievodca_kupou.pdf:1, 09_tim_maklerov.pdf:1, 05_vzor_najomnej_zmluvy.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1

> Peter Hruška spravuje nasledovné nehnuteľnosti:
> 
> 1. Rodinný dom v Bánovej, Žilina, počet izieb 5, cena 345 000 €
> 2. Rodinný dom v Rajeckých Tepliciach, okres Žilina, počet izieb 6, cena 289 000 €
> 3. Chata v Terchová, okres Žilina, počet izieb 3, cena 139 000 €
> 
> Spravuje ich ako maklér.

## 5. Aká je kaucia pri prenájme bytu?

*Očakávané:* trojnásob

### Bez ontológie — skóre 0/1, 11.1 s
*Zdroje:* 05_vzor_najomnej_zmluvy.pdf:1, 05_vzor_najomnej_zmluvy.pdf:1, 04_vzor_kupnej_zmluvy.pdf:1, 08_cennik_sluzieb.pdf:1, 04_vzor_kupnej_zmluvy.pdf:1

> Pri prenájme bytu sa kaucia v SemReal Žilina, s.r.o. v zvyčajnom prípade vymaže jedno až dve mesačné nájomné.

### S ontológiou — skóre 1/1, 15.6 s
*Rozpoznané pojmy:* nájomný inzerát, byt  
*Fakty z KG:* 0  
*Zdroje:* 05_vzor_najomnej_zmluvy.pdf:1, 05_vzor_najomnej_zmluvy.pdf:1, 03_ponuka_prenajmov.pdf:1, 10_sprievodca_kupou.pdf:1, 03_ponuka_prenajmov.pdf:1

> Pri prenájme bytu sa prenajímateľ môže požadovať kauciu najviac vo výške trojnásobku mesačného nájomného. V ponuke SemReal je kaucia zvyčajne jedno až dve mesačné nájomné.

## 6. Koľko stojí provízia pri predaji domu?

*Očakávané:* 4 %

### Bez ontológie — skóre 0/1, 11.4 s
*Zdroje:* 08_cennik_sluzieb.pdf:1, 08_cennik_sluzieb.pdf:1, 04_vzor_kupnej_zmluvy.pdf:1, 04_vzor_kupnej_zmluvy.pdf:1, 11_trhova_sprava_2026.pdf:1

> [KG] Pri predávaniu domu, provízia je 3% z kúpnej ceny, najviac 3 500 €.

### S ontológiou — skóre 0/1, 18.6 s
*Rozpoznané pojmy:* predajný inzerát, dom  
*Fakty z KG:* 0  
*Zdroje:* 08_cennik_sluzieb.pdf:1, 08_cennik_sluzieb.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1, 11_trhova_sprava_2026.pdf:1

> [ONT] Pojem "predajný inzerát" definínu, že cena je kúpna cena. V inzeráte [D3] je cena kúpna cena 289 000 €. V inzeráte [D4] je cena kúpna cena 139 000 €. V inzeráte [D5] je cena kúpna cena 89 000 €. Všetky tieto inzeráty sú predajnými inzerátmi. Toto znamená, že cena je kúpna cena. V praxi sa však provízia platí na kúpnu cenu. V dokumente [D2] sa uvede, že sprostredkovanie predaja bytu predávajúci platí 3% z kúpnej ceny, min. 3 000 €. Tento dokument je fiktívny a slúži na študijné účely. Z toho vyplýva, že pri predaji domu by platila min. 3 000 € + 3% z kúpnej ceny.

## 7. Kedy sú naplánované obhliadky?

*Očakávané:* 2026-11-24, 2026-11-26

### Bez ontológie — skóre 0/2, 14.2 s
*Zdroje:* 06_proces_obhliadky.pdf:1, 06_proces_obhliadky.pdf:1, 10_sprievodca_kupou.pdf:1, 02_ponuka_domov_chat_pozemkov.pdf:1, 01_ponuka_bytov_na_predaj.pdf:2

> Naplánované obhliadky sa sú obvykle rezervované osobným telefonickým alebo e-mailovým zvonekom u makléra, ktorý spravuje inzerát. V dokumente [D1] je uvedený, že rezervácia obhliadky je možné bezplatne zrušiť najneskôr 24 hodín vopred. Dokumenty neujemajú, kedy konkrétne sú naplánované obhliadky, iba že rezervácia je možné bezplatne zrušiť najneskôr 24 hodín vopred.

### S ontológiou — skóre 2/2, 14.5 s
*Rozpoznané pojmy:* obhliadka  
*Fakty z KG:* 3  
*Zdroje:* 06_proces_obhliadky.pdf:1, 06_proces_obhliadky.pdf:1, 10_sprievodca_kupou.pdf:1, 04_vzor_kupnej_zmluvy.pdf:1, 10_sprievodca_kupou.pdf:1

> Naplánované obhliadky sú určené na dňy: 2026-11-24, 2026-11-10 a 2026-11-26.

## Súhrn

| Otázka | Bez ontológie | S ontológiou |
|---|---|---|
| Ktoré jednoizbové byty máte na predaj v Žiline? | 50% (120 s) | 0% (16 s) |
| Môžem si na záhrade v Závodí postaviť rodinný dom? | 0% (14 s) | 100% (16 s) |
| Aké nehnuteľnosti ponúkate v meste Žilina do 100 000 €? | 33% (12 s) | 0% (18 s) |
| Ktoré nehnuteľnosti spravuje Peter Hruška? | 67% (13 s) | 0% (19 s) |
| Aká je kaucia pri prenájme bytu? | 0% (11 s) | 100% (16 s) |
| Koľko stojí provízia pri predaji domu? | 0% (11 s) | 0% (19 s) |
| Kedy sú naplánované obhliadky? | 0% (14 s) | 100% (14 s) |
| **Priemer** | **21%** | **43%** |
