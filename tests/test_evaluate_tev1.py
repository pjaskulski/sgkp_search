import unittest
from unittest.mock import Mock

from evaluate_tev1 import evaluate_case


class EvaluationTests(unittest.TestCase):
    def test_full_text_and_no_human_label_sent_to_model(self):
        service = Mock(model='tev1:4b')
        service._score_tev1.return_value = 0.8
        text = 'Tekst ' * 600
        result = evaluate_case(service, ['pytanie', 'hasło', text, 'TAK'], 0.5, 30)
        state = service._score_tev1.call_args.args[0]
        self.assertEqual(state['passage'], text)
        self.assertNotIn('Ocena człowieka', state)
        self.assertEqual(result[:4], [0.8, 'TAK', 'TAK', 'ok'])

    def test_failure_is_not_a_negative_decision(self):
        service = Mock(model='tev1:4b')
        service._score_tev1.side_effect = TimeoutError()
        result = evaluate_case(service, ['pytanie', 'hasło', 'tekst', 'NIE'], 0.5, 30)
        self.assertEqual(result[:4], ['', '', '', 'TimeoutError'])

    def test_basal_uses_its_own_scorer_with_identical_input(self):
        service = Mock(model='basal-1.5-4.5B-GGUF')
        service._score_basal.return_value = 0.2
        result = evaluate_case(service, ['młyny', 'Hasło', 'Pełny tekst', 'NIE'],
                               0.5, 30, backend='basal')
        service._score_tev1.assert_not_called()
        self.assertEqual(service._score_basal.call_args.args[0]['passage'], 'Pełny tekst')
        self.assertEqual(result[:4], [0.2, 'NIE', 'TAK', 'ok'])
