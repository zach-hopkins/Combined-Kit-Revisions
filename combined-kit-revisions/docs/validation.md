# Validation scope

This is an alpha integration. Passing installation/resource checks does not establish campaign balance or runtime compatibility with every EEex/SCS combination.

The build is pinned to the three commits in `upstream.lock.json`. English BG2EE and EET are the declared targets. EEex-only kits require the engine extension; detection recognizes its runtime marker or modern core component rather than treating the newer Quick Menu component as sufficient.

Development checks include:

* Coverage of all 134 upstream installer choices, with explicit base/optional/excluded status.
* Unique final menu IDs and rewritten upstream component dependencies.
* WeiDU syntax checks of the generated TP2/actions and integration patches.
* Native installation on an isolated clean Steam BG2EE copy, followed by resource assertions.
* Uninstall/reinstall and optional-component dependency checks.

Resource assertions cover RR 7th/8th-level bard spell slots; bounded Heckle effects and usage grants; Skald song caps; Inspiration caps; removal of recurring Kapellmeister restoration; and separate private HLA tables with valid resources.

Known boundaries:

* The integration is for a fresh mod build. Existing-save migration is not implemented.
* Additional AK/BW kits retain most original mechanics. Not every balance proposal from the earlier audit is implemented; specifically the RR Assassin/Swashbuckler chassis remains.
* Full EET transitions, actual gameplay with SCS, song/clone behavior and resistance interactions require in-game testing. Installation success is not evidence these have been playtested.
* Comprehensive Free Action/Haste cleanup remains the separate [personal Klatu fix](https://github.com/zach-hopkins/klatu-tweaks-and-fixes/releases/tag/v1.7.4-personal.1), applied after producers. This preserves the already-tested general scan rather than silently substituting a narrower implementation.

See the repository's validation record for the exact completed native checks.
