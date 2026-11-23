"""Read-only bilingual legal and changelog regression tests (stdlib + Jinja2)."""
import ast
import re
import unittest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

BASE = Path(__file__).resolve().parents[1]

class LegalPagesTest(unittest.TestCase):
    def test_published_gpl_is_exact(self):
        bundled = (BASE/'static/legal/GPL-2.0.txt').read_bytes()
        self.assertIn(b'GNU GENERAL PUBLIC LICENSE', bundled)
        self.assertIn(b'NO WARRANTY', bundled)
        self.assertEqual(bundled, (BASE.parent/'LICENSE').read_bytes()) if (BASE.parent/'LICENSE').exists() else None
    def test_markdown_is_in_sync(self):
        for lang, name in [('de','CHANGELOG.md'),('en','CHANGELOG.en.md')]:
            canonical=(BASE/name).read_bytes()
            self.assertEqual(canonical,(BASE/'static/legal'/('CHANGELOG.'+lang+'.md')).read_bytes())
            if (BASE.parent/name).exists():
                self.assertEqual(canonical,(BASE.parent/name).read_bytes())
    def test_parser_and_xss_safety(self):
        source = ast.parse((BASE/'src/app.py').read_text(encoding='utf-8'))
        wanted = {'_render_changelog_body', '_parse_changelog_sections'}
        nodes=[]
        for node in source.body:
            if isinstance(node,ast.FunctionDef) and node.name in wanted:
                nodes.append(node)
        self.assertEqual({node.name for node in nodes},wanted)
        namespace={'re':re}
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),
                     '<legal-test>','exec'),namespace)
        sections=namespace['_parse_changelog_sections']('## First\n- **Value** and `code`\n\n## Second\n<script>alert(1)</script>\n')
        self.assertEqual(len(sections),2)
        self.assertIn('<strong>Value</strong>',str(sections[0]['body_html']))
        self.assertIn('<code>code</code>',str(sections[0]['body_html']))
        self.assertNotIn('<script>',str(sections[1]['body_html']))
        self.assertIn('&lt;script&gt;',str(sections[1]['body_html']))
    def test_templates_compile_and_switch(self):
        env=Environment(loader=FileSystemLoader(BASE/'templates'),autoescape=True)
        for path in ('base.html','license_info.html','changelog_info.html'):
            env.get_template(path)
        self.assertIn('license_info', (BASE/'templates/base.html').read_text())
        self.assertIn('changelog_info', (BASE/'templates/base.html').read_text())
        for name in ('license_info.html','changelog_info.html'):
            raw=(BASE/'templates'/name).read_text()
            self.assertIn("ui_language == 'en'",raw)
            self.assertIn('data-no-i18n',raw)

if __name__=='__main__':
    unittest.main()
