import unittest
from financeiro.reports import build_evolution_presentation


class EvolutionPresentationTest(unittest.TestCase):
    def test_empty_and_zero_baseline(self):
        self.assertEqual(build_evolution_presentation([]), dict(evolution=[], total_cents=0, trend_percent=None, forecast=[]))
        result = build_evolution_presentation([dict(month='2026-01', total_cents=0), dict(month='2026-02', total_cents=100)])
        self.assertEqual(result['total_cents'], 100)
        self.assertIsNone(result['trend_percent'])

    def test_total_trend_and_recursive_rounding(self):
        data = [dict(month=f'2026-0{i+1}', total_cents=value) for i, value in enumerate([100, 200, 401])]
        result = build_evolution_presentation(data)
        self.assertEqual(result['total_cents'], 701)
        self.assertEqual(result['trend_percent'], 301)
        self.assertEqual([row['total_cents'] for row in result['forecast'][:3]], [234, 278, 304])
        self.assertEqual(len(result['forecast']), 12)
        self.assertEqual(result['forecast'][-1]['month'], '2027-03')
        self.assertEqual(data[-1]['total_cents'], 401)

    def test_short_window_ties_and_negative_baseline(self):
        result = build_evolution_presentation([dict(month='2026-12', total_cents=7)])
        self.assertIsNone(result['trend_percent'])
        self.assertTrue(all(row['total_cents'] == 7 for row in result['forecast']))
        result = build_evolution_presentation([dict(month='2026-01', total_cents=-2), dict(month='2026-02', total_cents=-1)])
        self.assertEqual(result['trend_percent'], 50)
        self.assertEqual(result['forecast'][0]['total_cents'], -1)


if __name__ == '__main__':
    unittest.main()
