# Alpha validation record — 22 October 2026

Version: 0.1.0-alpha.1. All testing used independent copies; the personal game installation was not changed.

| Check | Result |
|---|---|
| Fresh download/build of all three pinned upstream repositories | Passed |
| Installer/dependency/NPC separation regression suite | 14 tests passed |
| WeiDU 251 syntax checks | 140 generated/integration files passed |
| Plain Steam BG2EE native base install | Passed; EEex-only choices explicitly skipped |
| Steam BG2EE + EEex 1.2.0 native base install | Passed; EEex-only kits included |
| Private HLA mappings | 92 without EEex; 99 with EEex; unique references and custom HLA resources verified |
| RR bard seventh/eighth spell-level access | Verified at bard levels 21/29 |
| Heckle, Skald and Inspiration bounds | Verified installed effect data and grants |
| Kapellmeister recurring spell restoration | Removed from installed song resources |
| Shared armor/item changes with EK fix | Native BW armor and mage-item components passed with EEex |
| EK clone callback fixture regression | 15 guard cases passed using the actual callback |

Additional native installation checks covered RR racial adjustments, equipment and upgrades, nonstacking familiar-strength thievery potions; BW new spells, armored casting, mage/priest item access, shields and helmets; and Mazzy, Jan, Rasaad and companion bard spellbook options. Nalia's missing equipment-access prerequisite was correctly rejected; its prerequisite is declared before the NPC choice in the corrected menu.

RR equipment emitted an upstream `no effects altered on MISC2P.ITM` warning on the Steam game; it installed successfully. Existing upstream ability-alias warnings were also observed. These are recorded rather than represented as a warning-free build.

Full EET campaign transitions and actual SCS combat have not been tested here. New kit balance, song/clone stacking in gameplay and ongoing-save migration are not validated by installation/resource assertions. This remains an alpha for fresh-build testing.
