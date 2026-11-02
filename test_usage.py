import runpy
import unittest

module = runpy.run_path(__file__.replace("test_usage.py", "opencode-usage"))

class UsageTests(unittest.TestCase):
    def test_unpriced_month_is_unknown(self):
        output = module['render']({'2026-11': {'tokens': 10, 'cost': 0, 'unpriced': True}})
        self.assertIn('unknown', output)

    def test_v2_only_schema(self):
        import sqlite3
        db = module['OpencodeDB'].__new__(module['OpencodeDB'])
        db.con = sqlite3.connect(':memory:')
        db.con.row_factory = sqlite3.Row
        db.con.execute('CREATE TABLE session_message (time_created INTEGER, type TEXT, data TEXT)')
        db.con.execute('INSERT INTO session_message VALUES (?, ?, ?)', (1000, 'assistant', '{"model":{"id":"test","providerID":"provider"},"tokens":{"input":42}}'))
        records = list(db.assistant_messages())
        self.assertEqual(records[0]['input'], 42)
        self.assertEqual(records[0]['model'], 'test')
        db.close()
