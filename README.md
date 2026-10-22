# Combined Kit Revisions

An opinionated integration of **Rogue Rebalancing (RR)**, **Bardic Wonders (BW)** and **Artisan's Kitpack (AK)** for BG2EE/EET. Your AK fork includes the Eldritch Knight clone/armor fix.

Version 0.1.0 is an **alpha integration**, intended for a fresh mod build and validation before campaign use. Do not install it over the standalone class mods or an ongoing personal campaign.

## Installer layout

* **Component 10 — Keep the original Inquisitor.** Select this before component 0 to retain the original area Dispel Magic and True Sight instead of Artisan's Smite Magic, aura and other Inquisitor changes. Install SCS's dispel adjustment afterwards to obtain its 1.5-times-level variant. Without component 10, the base retains Artisan's overhaul. This choice does not change other paladin kits.
* **Component 0 — Opinionated class and kit base.** RR original thief/bard kits, dual wielding and HLAs; **RR expanded bard spell progression is included by default** (7th-level spells at bard 21, 8th-level at 29). AK supplies the other original class/kit overhauls and its new kit catalog; BW supplies additional bard kits and bounded true-bard Inspirations. EEex-only kits are installed only when EEex is present, with explicit skip messages otherwise. Reduced-stat Dragon Disciple and unholy-only Pale Master are the selected alternatives.
* **[RR] / [BW] / [AK] optional components.** Equipment, encounters, race restrictions, item access, song mechanics, visual choices and late patches remain separate. Optional components require the base.
* **NPC choices.** Individual origin-labeled assignments remain separate, including Garrick, Imoen, Minsc, Jan, Xan and other supported companions. BW companion spellbook grants are also a separate choice. The base has no bespoke companion adjustment or kit reassignment; global class rules still affect characters using those classes.

`rules.json` is the authoritative selection and ordering manifest. The built `component-catalog.json` maps each upstream choice to the base, an optional component, or an explicitly excluded competing alternative. Original RR/BW/AK overhaul alternatives do not appear as stackable toggles.

See the [complete component menu](combined-kit-revisions/docs/components.md) and [validation record](combined-kit-revisions/docs/validation-results.md).

## Build on Windows

Install Python 3.11+ and obtain a current Windows WeiDU executable from [WeiDU](https://weidu.org/).

```powershell
py tools/build.py --weidu C:\Tools\WeiDU\weidu.exe
```

The builder downloads all three repositories at the commits in `upstream.lock.json`. It assembles the original assets and generated integration sources in `build/package/`, exposing only the combined installer. Copy that folder's contents to a **fresh BG2EE/EET build** and run `setup-combined-kit-revisions.exe`. Without `--weidu`, use your existing WeiDU executable with `combined-kit-revisions/combined-kit-revisions.tp2`.

For development, `--source RR=path --source AK=path --source BW=path` uses clean local checkouts and verifies their commits. Output cannot target a nonempty directory that is not already marked as a CKR build.

Upstream archives and generated assets are intentionally not checked into this integration repository. This keeps upstream provenance clear and avoids representing public source availability as blanket permission to redistribute all assets. The build consumes the pinned originals locally.

## Curated rules in this version

* RR controls Assassin, Bounty Hunter, Swashbuckler, Blade, Jester and Skald; competing full AK/BW replacements are excluded.
* Bounty Hunter gains the shared AK Analyze tool without AK's Manhunter snare or replacement poison/traps.
* Jester gains a bounded BW-derived Heckle: 25% miscast / +1 critical miss, save negates, one use at level 1 and every six levels. No berserk rider.
* RR Skald combat song bonuses cap at +3 ordinary / +4 enhanced.
* BW combat Inspirations cap at +2, casting-speed Inspiration at +1. RR ordinary/enhanced bard songs suppress equivalent attack/save Inspirations.
* Kapellmeister retains caster support but recurring song spell restoration is disabled.
* Every final HLA mapping is copied to a private CKR table, eliminating shared-table ownership conflicts.

The longer comparison document is a design reference, not a claim that every proposed hybrid has already been ported. This version keeps RR's Assassin/Swashbuckler mechanics rather than importing the full AK implementations. Other new kits retain upstream mechanics except documented CKR changes. Broad balance claims require playtesting.

## Installation stages

Install core classes/kits before SCS creates dependent AI. Install optional item/dialogue finalization components after the content they inspect. “One installer” removes internal provider competition; it does not promise arbitrary order independence with every external mod.

Use the personal Klatu Free Action/Haste fix after item/spell producers for comprehensive Free Action coverage; CKR does not replace that separate compatibility mod. See `docs/validation.md` for the tested scope and known limits.

## Origins

* [Rogue Rebalancing — aVENGER, Wisp and contributors](https://github.com/Spellhold-Studios/Rogue-Rebalancing).
* [Bardic Wonders — The Artisan and contributors](https://github.com/TheArtisanBG/Bardic-Wonders).
* [Artisan's Kitpack — The Artisan and contributors, personal EK fix](https://github.com/zach-hopkins/The-Artisan-s-Kitpack).

Original authors retain rights in their work. RR's published license is CC BY-NC-SA 3.0. This repository's integration code is released under the same license; that does not relicense upstream BW/AK assets. See `NOTICE.md`.
