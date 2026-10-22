import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ckr_build',ROOT/'tools/build.py')
build=importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

class InstallerIntegrationTests(unittest.TestCase):
    def test_commented_component_is_not_imported(self):
        text='/* BEGIN ~Ghost~ DESIGNATED 9 */\nBEGIN ~Real~ DESIGNATED 4\nCOPY ~a~ ~b~\n'
        self.assertEqual(set(build.parse_components(text)),{4})

    def test_flag_text_inside_multiline_description_is_preserved(self):
        text='BEGIN ~Real~ DESIGNATED 4\nCOPY ~a~ ~b~\nSAY DESC ~Description\nREQUIRE_COMPONENT is just text\n~\n'
        parsed=build.parse_components(text)[4]
        self.assertIn('REQUIRE_COMPONENT is just text',parsed['body'])
        self.assertEqual(parsed['flags'],[])

    def test_predicates_are_captured_not_executed_as_actions(self):
        parsed=build.parse_components('BEGIN ~X~ DESIGNATED 8\nGROUP ~Kits~\nREQUIRE_PREDICATE GAME_IS ~eet~ ~EET only~\nCOPY ~a~ ~b~')[8]
        self.assertEqual(len(parsed['flags']),2)
        self.assertNotIn('REQUIRE_PREDICATE',parsed['body'])

    def test_multiline_comment_cannot_create_false_components(self):
        text='BEGIN ~One~ DESIGNATED 1\n/*\nBEGIN ~Not real~ DESIGNATED 2\n*/\nCOPY ~a~ ~b~\nBEGIN ~Three~ DESIGNATED 3\n'
        self.assertEqual(set(build.parse_components(text)),{1,3})

    def test_rr_progression_is_base_not_optional(self):
        rules=json.loads((ROOT/'rules.json').read_text())
        self.assertIn(['RR',6],rules['base_order'])

    def test_no_npc_component_can_enter_base(self):
        rules=json.loads((ROOT/'rules.json').read_text())
        self.assertTrue(all(p not in ['AK_NPC','AK_TWEAK'] for p,n in rules['base_order']))

    def test_competing_original_kit_replacements_are_excluded(self):
        rules=json.loads((ROOT/'rules.json').read_text())
        base={tuple(x) for x in rules['base_order']}
        for p,ids in {'BW':[1001,1002,1003,2007],'AK':[7000,7004,7007,7006]}.items():
            for n in ids:
                self.assertNotIn((p,n),base)
                self.assertIn(n,rules['excluded'][p])

    def test_origin_detection_distinguishes_three_ak_installers(self):
        for p,path in build.INSTALLERS.items(): self.assertEqual(build.original_provider(path),p)
        self.assertIsNone(build.original_provider('EEEX/EEEX.TP2'))

    def test_built_menu_has_no_component_id_collision(self):
        path=ROOT/'build/package/combined-kit-revisions/component-catalog.json'
        if not path.exists(): self.skipTest('Build package first for catalog validation')
        catalog=json.loads(path.read_text())
        optional=[x['component'] for x in catalog if x['mode']=='optional']
        self.assertEqual(len(optional),len(set(optional)))
        self.assertEqual(len(catalog),134)

    def test_menu_predicates_do_not_depend_on_always_variables(self):
        path=ROOT/'build/package/combined-kit-revisions/combined-kit-revisions.tp2'
        if not path.exists():self.skipTest('Build package first')
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.startswith('REQUIRE_PREDICATE'):
                self.assertNotIn('CKR_AK_',line)
                self.assertNotIn('CKR_BW_',line)
                self.assertNotIn('CKR_EEEX',line)

    def test_garrick_prompt_is_not_embedded_in_kit(self):
        path=ROOT/'build/package/BardicWonders/lib/troubadour.tpa'
        if not path.exists():self.skipTest('Build package first')
        text=path.read_text(encoding='utf-8')
        self.assertNotIn('ACTION_READLN',text)
        self.assertNotIn('~garric.cre~',text)

    def test_companion_spellbooks_are_not_changed_by_spell_component(self):
        path=ROOT/'build/package/BardicWonders/lib/new_spells.tpa'
        if not path.exists():self.skipTest('Build package first')
        text=path.read_text(encoding='utf-8')
        self.assertNotIn('~HAERDALIS~',text)
        self.assertNotIn('~VOGHILN~',text)

    def test_package_exposes_only_combined_installer(self):
        root=ROOT/'build/package'
        if not root.exists():self.skipTest('Build package first')
        for path in build.INSTALLERS.values():self.assertFalse((root/path).exists(),path)
        self.assertTrue((root/build.TP2).exists())

    def test_nalia_dependency_is_declared_before_npc_choice(self):
        path=ROOT/'build/package/combined-kit-revisions/combined-kit-revisions.tp2'
        if not path.exists():self.skipTest('Build package first')
        text=path.read_text(encoding='utf-8')
        self.assertLess(text.index('DESIGNATED 10008204'),text.index('DESIGNATED 20200010'))

    def test_original_inquisitor_is_an_early_configuration(self):
        path=ROOT/'build/package/combined-kit-revisions/combined-kit-revisions.tp2'
        if not path.exists():self.skipTest('Build package first')
        text=path.read_text(encoding='utf-8')
        self.assertLess(text.index('DESIGNATED 10\n'),text.index('DESIGNATED 0\n'))
        condition='NOT MOD_IS_INSTALLED ~combined-kit-revisions/combined-kit-revisions.tp2~ ~10~'
        self.assertIn('OUTER_SET CKR_AK_3003 = CKR_BASE_PRESENT AND '+condition,text)
        block=text[text.index('PRINT ~[CKR base / AK] Artisan\'s Kitpack: Inquisitor Overhaul~'):]
        self.assertIn('ACTION_IF 1 AND '+condition+' BEGIN',block.split('END ELSE BEGIN')[0])

if __name__=='__main__':unittest.main()
