# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 René Fieler (RenFie)
"""Guard the compact mobile web-booking layout against future table-column changes."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class MobileBookingLayoutTests(unittest.TestCase):
    def test_independent_collapsed_cards_and_desktop_table(self):
        template = (ROOT / "templates" / "bookings.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "mobile.css").read_text(encoding="utf-8")
        self.assertIn('class="table-wrap mobile-web-booking-list web-bookings-desktop"', template)
        self.assertIn('class="web-bookings-compact"', template)
        self.assertIn('<details class="compact-booking">', template)
        self.assertIn('<summary class="compact-booking-summary">', template)
        self.assertIn('category_names.get(t.category_id', template)
        self.assertIn('.web-bookings-desktop{display:none!important}', css)
        self.assertIn('.web-bookings-compact{display:grid;', css)
        self.assertIn('.web-bookings-compact .compact-booking-summary', css)
        self.assertNotIn('<details class="compact-booking" open', template)

    def test_category_sorting_remains_available(self):
        template = (ROOT / "templates" / "bookings.html").read_text(encoding="utf-8")
        app = (ROOT / "src" / "app.py").read_text(encoding="utf-8")
        self.assertIn("('category','Kategorie')", template)
        self.assertIn("if sort_key == 'category':", app)

if __name__ == "__main__":
    unittest.main()
