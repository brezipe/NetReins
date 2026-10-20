# NetReins

**Monitor a omezovač síťového provozu jednotlivých procesů pro Windows.**

[English](README.md)

![NetReins](docs/screenshot.png)

NetReins ukazuje, které programy právě používají síť, a u kteréhokoli z nich
umí omezit rychlost stahování a/nebo odesílání. Například aby OneDrive nebo
aktualizace hry nezabraly celé připojení.

- živá tabulka procesů s rychlostí downloadu a uploadu v **Mb/s** (obnova každou sekundu)
- limit downloadu a/nebo uploadu pro každý proces, nastavení i zrušení okamžitě
- ikona v oznamovací oblasti: omezuje dál na pozadí, pravým tlačítkem otevřít, zrušit všechna omezení nebo ukončit
- tmavý vzhled, angličtina a čeština (volba se pamatuje)
- jediný přenosný `.exe`, nic se neinstaluje

## Stažení

Stáhni `NetReins.exe` z [poslední verze](../../releases/latest) a spusť ho.
Windows si vyžádá práva správce. NetReins je potřebuje kvůli síťovému ovladači
[WinDivert](https://reqrypt.org/windivert.html), který omezování provádí.

**Požadavky:** Windows 10 nebo 11, 64bitové.

> **Varování Windows při prvním spuštění?** Nové verze ještě nemají u Microsoft
> SmartScreen reputaci. Klikni na **Další informace → Přesto spustit**. Některé
> antiviry označují WinDivert jako „HackTool“, protože stejný ovladač používají
> i jiné síťové nástroje. Každá verze se sestavuje z tohoto repozitáře přes
> [GitHub Actions](../../actions) a zveřejňuje se k ní kontrolní součet SHA-256.

## Použití

1. Spusť něco, co používá síť. Proces se objeví v tabulce.
2. Klikni na jeho řádek, vyplň **Limit download** a/nebo **Limit upload** v Mb/s
   a stiskni **Omezit**. Prázdné pole znamená „tento směr neomezovat“.
   Desetinná čísla fungují (`0.5` i `0,5`).
3. **Zrušit** odstraní oba limity vybraného procesu.

Klik na hlavičku sloupce řadí (výchozí je podle názvu procesu A→Z). Omezené
procesy jsou zvýrazněné, sloupec **Zahozeno** počítá pakety zahozené kvůli
plné frontě.

**Zavření okna** schová NetReins do oznamovací oblasti a limity dál platí.
Když odškrtneš *Při zavření skrýt do oznamovací oblasti*, křížek program
ukončí. Ukončit jde i pravým tlačítkem na ikoně → **Ukončit**. Limity existují
jen za běhu programu. Po ukončení jde provoz normálně dál, i kdyby program spadl.

Druhé spuštění jen přenese do popředí okno té běžící kopie.

**O programu** v menu ikony v oznamovací oblasti ukáže verzi, licenci, odkaz
na tento repozitář a použité komponenty třetích stran.

**Jednotky:** 1 Mb/s = 1 000 000 bitů za sekundu ≈ 122 kB/s, stejně jako ve
Správci úloh.

**Prohlížeče** (Chrome, Edge, Vivaldi, Firefox) mají hodně procesů, ale síť
obvykle obsluhuje jen jeden z nich. Omez ten, u kterého tabulka při stahování
ukazuje provoz.

## Jak to funguje

NetReins posílá všechny TCP a UDP pakety (kromě loopbacku) přes
[WinDivert](https://reqrypt.org/windivert.html). Každý paket přiřadí procesu
podle lokálního portu (`psutil.net_connections()`, cache obnovovaná zhruba
každé 2 s). Pakety omezených procesů procházejí token bucketem zvlášť pro každý
proces a směr. Co je nad limit, čeká v krátké frontě (asi 1 s provozu), a když
je fronta plná, paket se zahodí a TCP samo zpomalí. Rychlost se měří z paketů,
které NetReins skutečně vrací do sítě, takže čísla už odpovídají limitu a nic
se nepočítá dvakrát.

Přehled souborů a návod na sestavení je v [anglickém README](README.md#how-it-works).

## Spuštění ze zdrojového kódu

```bash
pip install -r requirements.txt
```

Pak spusť `python main.py` v terminálu otevřeném přes **Spustit jako správce**.

Testy (nepotřebují ovladač ani práva správce):

```bash
pip install -r requirements-dev.txt
```

```bash
python -m pytest
```

Sestavení jednoho exe (`dist\NetReins.exe`):

```bash
build_exe.bat
```

## Známá omezení

- Všechen TCP/UDP provoz prochází přes Python. Při stovkách Mb/s roste zátěž
  procesoru a celková propustnost může klesnout.
- Úplně nové spojení se může krátce ukázat jako *(nepřiřazeno)*, než se
  obnoví cache portů.
- Mapování podle portu nerozlišuje IPv4 a IPv6 sockety se stejným portem.

## Licence

NetReins je vydaný pod [licencí MIT](LICENSE). Obsahuje komponenty třetích
stran pod jejich vlastními licencemi, viz
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
