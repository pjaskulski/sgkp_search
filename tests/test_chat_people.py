import json
import unittest
from unittest.mock import patch

import app as web


class PeopleRetrievalTests(unittest.TestCase):
    def test_interpretation_keeps_inflected_person_even_with_empty_names(self):
        entity = {'name': 'Elizą Orzeszkową', 'kind': 'person',
                  'canonical': 'Eliza Orzeszkowa', 'surname': 'Orzeszkowa'}
        with patch.object(web, 'preliminary_chat_answer', return_value=json.dumps({
                'names': [], 'entities': [entity]})) as model:
            result = web.model_interpret_question('Hasła związane z Elizą Orzeszkową?', {}, [], False)
        self.assertEqual(result['names'], ['Elizą Orzeszkową'])
        self.assertEqual(result['entities'], [entity])
        model.assert_called_once()

    def test_entities_do_not_invent_people_or_expand_identity(self):
        result = web.validated_question_entities([
            {'name': 'Nieobecna', 'kind': 'person', 'canonical': 'Nieobecna'},
            {'name': 'Jan Kowalski', 'kind': 'person', 'canonical': 'Jan Nowak', 'surname': 'Nowak'},
            {'name': 'Jan Kowalski', 'kind': 'bad'}], 'Co wiadomo o Jan Kowalski?')
        self.assertEqual(result, [{'name': 'Jan Kowalski', 'kind': 'person',
                                  'canonical': 'Jan Kowalski', 'surname': None}])

    def test_model_base_form_maps_to_actual_question_without_changing_person(self):
        entity = {'name': 'Eliza Orzeszkowa', 'kind': 'person',
                  'canonical': 'Eliza Orzeszkowa', 'surname': 'Orzeszkowa'}
        with patch.object(web, 'preliminary_chat_answer', return_value=json.dumps({
                'names': ['Eliza Orzeszkowa'], 'entities': [entity]})):
            result = web.model_interpret_question('Hasła związane z Elizą Orzeszkową?', {}, [], False)
        self.assertEqual(result['names'], ['Elizą Orzeszkową'])
        self.assertEqual(result['entities'][0]['canonical'], 'Eliza Orzeszkowa')
        self.assertIsNone(web.explicit_question_name('Ignacy Łukaszewicz', 'Ignacy Łukasiewicz'))
        self.assertIsNone(web.explicit_question_name('Eliza Orzeszkowa', 'Eliza czy Orzeszkowa?'))

    def test_body_mentions_initials_reversed_order_and_filters(self):
        entity = {'name': 'Ignacy Łukasiewicz', 'kind': 'person',
                  'canonical': 'Ignacy Łukasiewicz', 'surname': 'Łukasiewicz'}
        hits = [
            {'passage_id': 'a', 'entry_id': '1', 'nazwa': 'Chorkówka',
             'text': 'Założona przez Ignacego Łukasiewicza.'},
            {'passage_id': 'b', 'entry_id': '2', 'nazwa': 'Hanczarów',
             'text': 'Właściciel: Łukasiewicz Ignacy.'},
            {'passage_id': 'c', 'entry_id': '3', 'nazwa': 'Inne hasło',
             'text': 'I. Łukasiewicz, założyciel rafineryi nafty.'},
            {'passage_id': 'd', 'entry_id': '4', 'nazwa': 'Łukasiewicz', 'text': 'Brak wzmianki.'}]
        with patch.object(web.Meili, 'search', return_value={'hits': hits}) as search:
            result = web.person_passages('p', entity, ['tom = "01"'], ['text'])
        self.assertEqual({hit['passage_id'] for hit in result}, {'a', 'b', 'c'})
        queries = [call.args[1]['q'] for call in search.call_args_list]
        self.assertIn('łukasiewicz', queries)
        self.assertIn('Łukasiewicz Ignacy', queries)
        for call in search.call_args_list:
            self.assertEqual(call.args[1]['filter'], ['tom = "01"'])
            self.assertEqual(call.args[1]['attributesToSearchOn'], ['text'])

    def test_person_body_source_reaches_final_answer_not_title_search(self):
        entity = {'name': 'Eliza Orzeszkowa', 'kind': 'person',
                  'canonical': 'Eliza Orzeszkowa', 'surname': 'Orzeszkowa'}
        source = {'passage_id': '06-04545-001_p0001', 'entry_id': '06-04545-001',
                  'nazwa': 'Milkowszczyzna', 'tom': '06', 'strona': 1,
                  'text': 'Miejsce urodzenia Elizy Orzeszkowej.', 'jest_miejscowoscia': True}
        with patch.object(web, 'manifest', return_value={
                'entries_index': 'e', 'passages_index': 'p', 'vectors': False}), \
             patch.object(web, 'model_interpret_question', return_value={
                 'names': [entity['name']], 'entities': [entity], 'district': None,
                 'many_localities': False}), \
             patch.object(web.Meili, 'search', return_value={'hits': [source]}), \
             patch.object(web, 'named_passages') as title_search, \
             patch.object(web.Chat, 'answer', return_value='Milkowszczyzna [1].') as answer:
            result = web.app.test_client().post('/api/v1/chat', json={
                'question': 'Eliza Orzeszkowa', 'verify': False,
                'filters': {'jest_miejscowoscia': 'true'}})
        self.assertEqual(result.status_code, 200)
        title_search.assert_not_called()
        self.assertEqual(result.json['sources'][0]['entry_id'], source['entry_id'])
        self.assertIn('Miejsce urodzenia Elizy Orzeszkowej', str(answer.call_args))


if __name__ == '__main__':
    unittest.main()
