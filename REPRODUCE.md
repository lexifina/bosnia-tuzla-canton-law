# How this repository was made (Tuzla Canton)

This file is written by the build on 2026-11-03, the day the source data was retrieved.

## Sources

| Source | Address | Retrieved | Licence |
| --- | --- | --- | --- |
| Skupština Tuzlanskog kantona: Službene novine Tuzlanskog kantona (each issue as a PDF) | <https://skupstinatk.gov.ba/sluzbene-novine-tk> | 2026-10-30 | Official text, not protected: Zakon o autorskom i srodnim pravima BiH (Sl. glasnik BiH 63/10), čl. 8(1)(b) |
| Skupština Tuzlanskog kantona: Službene novine Tuzlanskog kantona (each issue as a PDF) | <https://skupstinatk.gov.ba/sluzbene-novine-tk> | 2026-11-03 | Official text, not protected: Zakon o autorskom i srodnim pravima BiH (Sl. glasnik BiH 63/10), čl. 8(1)(b) |

Every word of law in this repository comes from these sources. Lexifina reads them and records each act's dated versions, and the laws that made each change, in one corpus file. This repository is built from that file.

## What is in it

| Act | Title | Versions | Span |
| --- | --- | ---: | --- |
| `o-muzejskoj-djelatnosti` | Закон о музејској дјелатности | 1 | 2024-06-22 to 2024-06-22 |
| `o-drzavnoj-sluzbi-u-tuzlanskom-kantonu` | Закон о државној служби у Тузланском кантону | 1 | 2024-08-08 to 2024-08-08 |
| `o-pozorisnoj-djelatnosti` | Закон о позоришној дјелатности | 1 | 2025-07-15 to 2025-07-15 |
| `o-osnivanju-javne-ustanove-institut-za-drustvena-i-religijsk` | Zakon o osnivanju javne ustanove institut za društvena i religijska istraživanja u Tuzli | 1 | 2026-03-06 to 2026-03-06 |
| `o-uvjetima-i-postupku-legalizacije-bespravno-izgradjenih-gra` | Zakon o uvjetima i postupku legalizacije bespravno izgrađenih građevina | 1 | 2026-02-26 to 2026-02-26 |
| `o-radio-televiziji-tuzlanskog-kantona` | Zakon o radio-televiziji Tuzlanskog kantona | 1 | 2021-12-03 to 2021-12-03 |

The build made 6 commits:

| Commits | Kind |
| ---: | --- |
| 6 | first version of an act |
| 0 | one law on its in-force day |
| 0 | changes no amendment note explains, credited to the publisher |

Other counts:
- 0 commits on the branch `buducnost`: laws not yet in force on 2026-11-03.
- 0 commits dated 1 January 1970: in force before 1970, with the real day in their `In-force` trailer.
- 6 laws in the record.
- 9 tags.

## Dates

Each commit is dated at noon (Europe/Sarajevo) on the day the change took effect. The other dates, enacted and published, are trailers.

When a law gives no date of its own, the default rule applies: A law takes effect on the day its own final article names, counted from its publication in the Službene novine Tuzlanskog kantona. https://skupstinatk.gov.ba/sluzbene-novine-tk

## How the history is built

`tools/build.py` turns the corpus into this history in one pass: one commit per law, on the day it took effect. The same corpus always gives the same commit hashes. `tools/check_repo.py` reads every version back from git and compares it with the corpus. `tools/on.py` shows the law as it stood on any date. The corpus format is described in `tools/SCHEMA.md`.

- Corpus: sha256 `fa574d726154e760ccd8525bf34cd09680910c613bd104bede2b8df18bc85b86` (432254 bytes).
- Builder blob hashes (`git hash-object`): `build.py` `900da0d33bfd1ef455267fb4dcef7961fd5acc9c`, `check.py` `5d719354ea4c62d240c93d2cae446307d81d9e81`, `on.py` `aff48cf1b68d50c7ba8f399ca32261871c301824`.
- Python 3.14.4; git version 2.53.0.

## Checks

6 versions of 6 acts read back from git on the day each took effect and on the day before: 0 mismatches. Trailers: 0 commits whose trailers git cannot parse. Health: 0 merge commits on main, 0 commit dates that go backwards, 0 commits dated after the build.

A second build from the same corpus into an empty folder gave identical hashes for all 6 history commits and 9 tags (history tip `e0d7ab53ae2ea58c6384c0c7706183a3220497ba`).

## Decisions made by hand

- Laws part 1: laws the Assembly of Tuzla Canton published in the Službene novine Tuzlanskog kantona from 2022-01-01 to 2026-07-10 (every issue on the Assembly site in that span; laws are checked against every later issue) that no later law in those issues amends, repeals or consolidates: a law is left out when any later amending law or consolidated text cites its gazette number next to a word of its subject, or any later law cites it next to words of repeal. Amending and budget laws are left out. Each is its text as enacted, dated the issue date plus the days its final article names, credited to the law; or, where the Legislative Committee of the Assembly has published an official consolidated text (prečišćeni tekst) that nothing later touches, that text, dated the day it was published (it applies from its publication, as its last article says). Amendments published after 2026-07-10, and decisions of the Constitutional Court, are not in the record.
- Each law is kept in the language and script of the gazette edition it was published in (the issues rotate between the Croatian, Serbian and Bosnian editions; the Serbian edition is in Cyrillic).
- Units: uvod.md is the preamble (legal basis and adoption), naslov.md the title, clan-NNN.md each article with its heading (chapter headings stay with the article after them), potpis.md the signature block (its left half, then its right half).
- Laws part 2: laws the Assembly of Tuzla Canton published in the Službene novine Tuzlanskog kantona from 2021-01-01 to 2026-07-10 (every issue on the Assembly site in that span; laws are checked against every later issue) that no later law in those issues amends, repeals or consolidates: a law is left out when any later amending law or consolidated text cites its gazette number next to a word of its subject, or any later law cites it next to words of repeal. Amending and budget laws are left out. Each is its text as enacted, dated the issue date plus the days its final article names, credited to the law; or, where the Legislative Committee of the Assembly has published an official consolidated text (prečišćeni tekst) that nothing later touches, that text, dated the day it was published (it applies from its publication, as its last article says). Amendments published after 2026-07-10, and decisions of the Constitutional Court, are not in the record.
- Each law is kept in the language and script of the gazette edition it was published in (the issues rotate between the Croatian, Serbian and Bosnian editions; the Serbian edition is in Cyrillic).
- Units: uvod.md is the preamble (legal basis and adoption), naslov.md the title, clan-NNN.md each article with its heading (chapter headings stay with the article after them), potpis.md the signature block (its left half, then its right half).

## What AI did and did not do

The scripts that read the sources and build this repository were written by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`) under Lexifina's direction.

No model wrote, translated or corrected legal text. No model runs at build time. Every word of law in this repository comes from the official sources above.

The commit messages are written by `build.py` from the source data.

Model use at data-build time:
- none: the text is read from the gazette PDFs' text layer by a deterministic parser; no model output is legal text.
- none: the text is read from the gazette PDFs' text layer by a deterministic parser; no model output is legal text.
