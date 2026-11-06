# Tuzla Canton: law history in git

Part of [lexifina/global-law](https://github.com/lexifina/global-law), one git history for every country's law: this is the law of Tuzla Canton, Federation of Bosnia and Herzegovina, Bosnia and Herzegovina, which global-law reads at `bosnia-and-herzegovina/federation/tuzla-canton/acts/`.

The law of Tuzla Canton (Tuzlanski kanton), one of the ten cantons of the Federation of Bosnia and Herzegovina, as a git history: one file per article, one commit per law, dated the day it took effect, with the law as the commit's author. `git log` lists every change to an article; checking out a date gives the text in force that day.

It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law), which places it at `ba-03/`. The Federation's own law is in [lexifina/bosnia-federation-law](https://github.com/lexifina/bosnia-federation-law), the state's in [lexifina/bosnia-and-herzegovina-law](https://github.com/lexifina/bosnia-and-herzegovina-law).

Each law is in the language and script of the gazette edition it was published in: the Službene novine Tuzlanskog kantona rotate between Bosnian, Croatian and Serbian editions, and the Serbian edition is printed in Cyrillic.

## What this repository holds

Six laws the Assembly of Tuzla Canton published in the Službene novine Tuzlanskog kantona from 2021 to July 2026 that no later law in those issues amends, repeals or consolidates, each in one of two forms:

- the law as enacted, dated the day it took effect; or
- an official consolidated text (prečišćeni tekst) established by the Assembly's Legislative Committee and published in the gazette, dated the day it was published (it applies from its publication, as its last article says). Earlier versions of these laws are not in the record yet.

| Law | Version date | Text |
| --- | --- | --- |
| Zakon o radio-televiziji Tuzlanskog kantona | 3 December 2021 | Official consolidated text |
| Закон о музејској дјелатности | 22 June 2024 | As enacted |
| Закон о државној служби у Тузланском кантону | 8 August 2024 | Official consolidated text |
| Закон о позоришној дјелатности | 15 July 2025 | As enacted |
| Zakon o uvjetima i postupku legalizacije bespravno izgrađenih građevina | 26 February 2026 | Official consolidated text |
| Zakon o osnivanju javne ustanove institut za društvena i religijska istraživanja u Tuzli | 6 March 2026 | As enacted |

Not included yet: the Constitution of Tuzla Canton (the only free text found is marked unofficial); laws that were later amended and have no newer consolidated text; amending and budget laws; laws whose tables the two PDF readers order differently.

## Source

The Assembly of Tuzla Canton (Skupština Tuzlanskog kantona), <https://skupstinatk.gov.ba/sluzbene-novine-tk>: every issue of the Službene novine Tuzlanskog kantona as a PDF with a text layer.

## Dates

- Each law's commit is dated at **noon, Europe/Sarajevo, on the day it took effect**: the issue's date plus the days the law's own final article names (most often the eighth day after publication); a consolidated text on the day of its issue.
- Versions that take effect after the retrieval day would go on the `buducnost` branch, never merged into `main`.

## Files

`<law>/clan-001.md` is Član (Članak, Члан) 1, `clan-005-a.md` Član 5a. `uvod.md` holds the preamble (the legal basis and the Assembly's adoption, or the Legislative Committee's decision for a consolidated text), `naslov.md` the title, `potpis.md` the signature block. Chapter headings stay in the file of the article they stand before. One paragraph per line.

## How it is checked

- Every version is read back from git on the day it took effect and on the day before; both must match `corpus.json`.
- The letters and digits of every law equal those of the gazette issue, read independently with a different PDF reader, from the first paragraph to the last article; the signature block's lines all occur in it.
- Whether a law was later amended, repealed or consolidated is judged from every later law in the scanned issues (a law is left out when a later amending law or consolidated text cites its gazette number next to a word of its subject, or any later law cites it next to words of repeal). Decisions of the Constitutional Court are not checked.
- Health checks: no merge commits, commit dates never go backwards, nothing dated in the future, and every commit's trailers parse.

## What "author" means

The author of a commit is the law that made it, named by its gazette number, with an e-mail address that cannot exist (`<key>@skupstinatk.gov.ba.invalid`). The committer is always Lexifina.

## Limits

This is not an official publication. The binding text is the one published in the Službene novine Tuzlanskog kantona. Only the laws listed in `data/versions.json` are included; amendments published after the last issue read (10/26 of 2026-07-10) are not in the record.
