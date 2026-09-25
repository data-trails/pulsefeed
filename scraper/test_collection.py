import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

import collection
import scrape
from source_workbook import WORKBOOK, REGISTRY, compile_registry, read_tables


class DateTests(unittest.TestCase):
    def test_real_archive_date_formats(self):
        for text, expected in [
            ('2026-06-04_PC_Minutes.pdf', '2026-06-04'),
            ('20260902-PC-Agenda.pdf', '2026-09-02'),
            ('pc_packet_9.17.26.pdf', '2026-09-17'),
            ('07-27-2026-AGENDA.pdf', '2026-07-27'),
            ('2024 May 20', '2024-05-20'),
            ('agenda-september-17-2026', '2026-09-17'),
            ('Sept 17, 2026', '2026-09-17'),
        ]:
            with self.subTest(text=text):
                date = collection.parse_date(text)
                self.assertIsNotNone(date)
                self.assertEqual(date.date().isoformat(), expected)

    def test_invalid_and_ambiguous_dates_are_not_fabricated(self):
        for text in ('/1/2/1339/file.pdf', '2026-02-31', 'June 4', '9/34/26'):
            self.assertIsNone(collection.parse_date(text))

    def test_table_date_and_filename_priority(self):
        soup = BeautifulSoup('<table><tr><td>August 19, 2026</td><td><a href="packet.pdf">Packet</a></td></tr></table>', 'html.parser')
        self.assertEqual(collection.link_date(soup.a).date().isoformat(), '2026-08-19')
        soup = BeautifulSoup('<div><a href="2026-08-19-PC.pdf">Packet</a><a href="2026-09-16-PC.pdf">Packet</a></div>', 'html.parser')
        self.assertEqual(collection.link_date(soup.find_all('a')[1]).date().isoformat(), '2026-09-16')

    def test_conflicting_dates_require_review(self):
        collection.begin_source()
        a = BeautifulSoup('<a href="PC-Minutes-08-06-26.pdf">August 8, 2026</a>', 'html.parser').a
        self.assertIsNone(collection.link_date(a))
        self.assertIn('Conflicting', collection.source_diagnostics()['issues'][0])


class CollectionTests(unittest.TestCase):
    def setUp(self):
        collection.begin_source()

    def test_mixed_board_page_does_not_leak(self):
        soup = BeautifulSoup('''<h2>Planning Commission</h2><a href="pc_packet_9.17.26.pdf">Packet</a>
            <h2>City Council</h2><a href="agenda-9.17.26.pdf">Agenda</a>''', 'html.parser')
        links = soup.find_all('a')
        self.assertTrue(collection.planning_link(links[0], 'https://city.test/meetings/#planning-commission'))
        self.assertFalse(collection.planning_link(links[1], 'https://city.test/meetings/#planning-commission'))

    def test_fragment_alone_is_not_scope(self):
        a = BeautifulSoup('<a href="agenda.pdf">Agenda</a>', 'html.parser').a
        self.assertFalse(collection.planning_link(a, 'https://city.test/meetings/#planning-commission'))

    def test_extensionless_downloads(self):
        for url in ('https://city.test/?ddownload=14332', '/AgendaCenter/ViewFile/Agenda/_09172026-1', '/doc/file', '/packet.PDF?x=1'):
            self.assertTrue(collection.document_link(url))
        self.assertFalse(collection.document_link('/meetings'))

    def test_base_href_and_table_context(self):
        html = '<base href="https://city.test/"><table><tr><td>September 17, 2026</td><td><a href="Documents/packet.pdf">Packet</a></td></tr></table>'
        soup = BeautifulSoup(html, 'lxml')
        soup._source_url = 'https://city.test/directory/planning_commission.php'
        source = {'county': 'Ottawa', 'name': 'Test Planning Commission', 'url': soup._source_url}
        with patch.object(scrape, 'fetch_html', return_value=soup), patch.object(scrape, 'is_within_window', return_value=True), patch.object(scrape, 'parse_pdf_full', return_value={'items': '', 'parcels': [], 'doc_type': ''}):
            items = scrape.scrape_html_source(source, set())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['link'], 'https://city.test/Documents/packet.pdf')
        self.assertEqual(items[0]['date'], '2026-09-17')

    def test_landing_page_download(self):
        soup = BeautifulSoup('<a href="/document/july-27-2026-planning-commission-agenda/">July 27, 2026 Planning Commission Agenda</a>', 'lxml')
        child = BeautifulSoup('<main><a href="https://cdn.test/07-27-2026-AGENDA.pdf">Download</a></main><nav><a href="map.pdf">Map</a></nav>', 'lxml')
        source = {'county': 'Allegan', 'name': 'City Planning Commission', 'url': 'https://city.test/planning-commission/'}
        with patch.object(scrape, 'fetch_html', side_effect=[soup, child]), patch.object(scrape, 'is_within_window', return_value=True), patch.object(scrape, 'parse_pdf_full', return_value={'items': '', 'parcels': [], 'doc_type': ''}):
            items = scrape.scrape_html_source(source, set())
        self.assertEqual([i['link'] for i in items], ['https://cdn.test/07-27-2026-AGENDA.pdf'])

    def test_oversize_pdf_is_not_truncated_and_parsed(self):
        class Response:
            url = 'https://city.test/packet.pdf'
            status_code = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def raise_for_status(self): pass
            def iter_content(self, size): return iter([b'%PDF-', b'x' * 20])
        with patch.object(collection.SESSION, 'get', return_value=Response()):
            raw, _ = collection.request_bytes(Response.url, max_bytes=10)
        self.assertIsNone(raw)
        self.assertTrue(collection.source_diagnostics()['issues'])

    def test_nested_list_does_not_borrow_another_meeting_date(self):
        soup = BeautifulSoup('<table><tr><td><ul><li><a href="pc_packet_1.15.26.pdf">January 15, 2026</a></li><li><a href="pc_packet_3.19.26.pdf">March 19, 2026</a></li></ul></td></tr></table>', 'html.parser')
        self.assertEqual(collection.link_date(soup.find_all('a')[1]).date().isoformat(), '2026-03-19')

    def test_html_error_page_is_not_a_pdf(self):
        with patch.object(scrape, 'request_bytes', return_value=(b'<html>Access denied</html>', 'https://city.test')):
            self.assertIsNone(scrape.fetch_pdf_bytes('https://city.test/packet.pdf'))

    def test_doc_type_uses_agenda_filename_before_approval_of_minutes(self):
        self.assertEqual(scrape.detect_doc_type('https://city.test/agenda.pdf', 'Agenda', 'Approval of minutes'), 'Agenda')

    def test_lowercase_agenda_subitems_are_retained(self):
        text = 'AGENDA\n1. Call to order\n2. Discussion/Action\na. Preliminary Site Plan Review\n3. Adjournment'
        self.assertIn('Site Plan', scrape.filter_pdf_by_topic(scrape.extract_agenda_items(text)))

    def test_failed_source_keeps_existing_and_refresh_replaces_duplicates(self):
        source = {'id': 'TEST', 'county': 'Ottawa', 'name': 'Test PC', 'deploymentStatus': 'Production'}
        item = {'id': 'stable', 'county': 'Ottawa', 'source': 'Test PC', 'link': 'https://city.test/a.pdf', 'date': '2026-09-17', 'title': 'Old'}
        with patch.object(scrape, 'is_within_window', return_value=True):
            self.assertEqual(len(scrape.merge_feed([item], [], [source])), 1)
            items = scrape.merge_feed([item], [{**item, 'title': 'Revised'}], [source])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Revised')

    def test_corrupt_existing_feed_is_not_silently_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'feed.json'
            path.write_text('{broken')
            with self.assertRaises(ValueError): scrape.load_existing(path)

    def test_failed_pdf_refresh_retains_prior_extraction(self):
        source = {'id': 'TEST', 'county': 'Ottawa', 'name': 'Test PC', 'deploymentStatus': 'Production'}
        old = {'id': 'stable', 'county': 'Ottawa', 'source': 'Test PC', 'link': 'https://city.test/a.pdf', 'date': '2026-09-17', 'pdfItems': 'Site plan review', 'summary': 'Site plan review'}
        new = {**old, 'pdfStatus': 'unavailable', 'pdfItems': '', 'summary': ''}
        with patch.object(scrape, 'is_within_window', return_value=True):
            merged = scrape.merge_feed([old], [new], [source])[0]
        self.assertEqual(merged['pdfItems'], 'Site plan review')
        self.assertIn('retained', merged['details'])


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tables = read_tables(WORKBOOK)

    def test_workbook_matches_shared_registry(self):
        sources = compile_registry(self.tables)
        self.assertEqual(sources, json.loads(REGISTRY.read_text()))
        self.assertEqual(len(sources), len(self.tables['Active Sources']))
        held = {s['Source ID'] for s in self.tables['Hold - Future Scope']}
        self.assertFalse(held & {s['id'] for s in sources})

    def test_original_39_operational_sources_and_ids_are_preserved(self):
        original = json.loads((Path(__file__).parent / 'fixtures/original_sources.json').read_text())
        registry = {(s['county'], s['name']): s for s in compile_registry(self.tables) if s['deploymentStatus'] == 'Production'}
        self.assertGreaterEqual(len(registry), sum(len(rows) for rows in original.values()))
        self.assertTrue({'OTT-COOP-CITY-PC', 'OTT-HUDS-CITY-PC'}.issubset({s['id'] for s in registry.values()}))
        for rows in original.values():
            for row in rows:
                actual = registry[(row['county'], row['name'])]
                expected = {k: v for k, v in row.items() if k not in {'county', 'name'}}
                self.assertEqual(actual['endpoints'], expected)
                self.assertEqual(scrape.make_id(row, 'https://test/doc.pdf'), scrape.make_id(actual, 'https://test/doc.pdf'))

    def test_duplicate_ids_fail(self):
        self.tables['Active Sources'].append(copy.deepcopy(self.tables['Active Sources'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'): compile_registry(self.tables)

    def test_missing_endpoint_fails_before_scraping(self):
        self.tables['Source Endpoints'] = self.tables['Source Endpoints'][1:]
        with self.assertRaisesRegex(ValueError, 'RSS mismatch'): compile_registry(self.tables)

    def test_rss_disagreement_fails(self):
        self.tables['Active Sources'][0]['Production RSS URL'] += 'changed'
        with self.assertRaisesRegex(ValueError, 'RSS mismatch'): compile_registry(self.tables)

    def test_candidate_cannot_activate_without_endpoints(self):
        row = next(r for r in self.tables['Active Sources'] if r['Deployment Status'] != 'Production')
        row['Deployment Status'] = 'Production'
        with self.assertRaisesRegex(ValueError, 'Missing production'): compile_registry(self.tables)


if __name__ == '__main__':
    unittest.main()
