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


class PricingTests(unittest.TestCase):
    def engine(self, data):
        engine = module['PricingEngine'].__new__(module['PricingEngine'])
        engine.data = data
        engine._by_model = engine._index_real_rates(data)
        return engine

    def test_explicit_free_model_prices_mixed_month(self):
        engine = self.engine({'source': {'models': {
            'free': {'cost': {'input': 0, 'output': 0}},
            'paid': {'cost': {'input': 1, 'output': 2}},
        }}})
        records = [dict(ts_ms=1793520000000, provider='source', model=model,
                        input=1000000, output=0, reasoning=0, cache_read=0,
                        cache_write=0) for model in ('free', 'paid')]
        buckets = module['aggregate_by_month'](records, engine)
        self.assertNotIn('unknown', module['render'](buckets))
        self.assertEqual(sum(b['cost'] for b in buckets.values()), 1)
        self.assertEqual(engine.cost('source', 'free', records[0]), (0, True))

    def test_missing_or_incomplete_prices_stay_unknown(self):
        for cost in ({}, {'input': 0}, {'input': 0, 'output': 0, 'cache_read': -1}):
            engine = self.engine({'source': {'models': {'model': {'cost': cost}}}})
            self.assertIsNone(engine._rate('source', 'model'))

    def test_paid_equivalent_precedes_zero_rate(self):
        engine = self.engine({
            'source-plan': {'models': {'model': {'cost': {'input': 0, 'output': 0}}}},
            'source': {'models': {'model': {'cost': {'input': 1, 'output': 2}}}},
        })
        self.assertEqual(engine._rate('source-plan', 'model')['input'], 1)
        self.assertEqual(engine._rate('other', 'model')['input'], 1)
