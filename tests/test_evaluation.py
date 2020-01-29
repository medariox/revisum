import os
import sys
sys.path.append('..' + os.sep + 'revisum')

from pathlib import Path

import pytest
from revisum.snippet import Snippet
from revisum.chunk import Chunk
from revisum.trainer import SnippetTrainer
from gensim.models.doc2vec import Doc2Vec


tests_data = os.path.join(Path(__file__).parent, 'data')


code_to_find = [
    """
    def test_preparing_url(self, url, expected):

    def normalize_percent_encode(x):
        # Helper function that normalizes equivalent
        # percent-encoded bytes before comparisons
        for c in re.findall(r'%[a-fA-F0-9]{2}', x):
            x = x.replace(c, c.upper())
        return x

    r = requests.Request('GET', url=url)
    p = r.prepare()
    assert normalize_percent_encode(p.url) == expected
    """
]

other_code = [
    """
    def normalize_percent_encode(x):
        # Helper function that normalizes equivalent
        # percent-encoded bytes before comparisons
        for c in re.findall(r'%[a-fA-F0-9]{2}', x):
            x = x.replace(c, c.upper())
        return x
    """
]


def evaluate():

    tokens = Snippet.as_tokens(other_code)

    for test_dir in os.listdir(tests_data):

        # repo_id, iterations, snippets = test_dir.split('_')

        model_dir = os.path.join(tests_data, test_dir)
        model_path = os.path.join(model_dir, 'd2v.model')

        if not os.path.isfile(model_path):
            if not os.path.isdir(model_dir):
                os.makedirs(model_dir)

        model = Doc2Vec.load(model_path)
        # model.trainables.reset_weights(model.hs, model.negative, model.wv, model.docvecs)

        print('--------------------------------------')
        print(test_dir)
        print(model_dir)

        SnippetTrainer(repo_id=test_dir, path=model_dir).iterate(
            15, model=model, model_path=model_path)

        model2 = Doc2Vec.load(model_path)
        new_vector = model2.infer_vector(tokens)
        sims = model2.docvecs.most_similar([new_vector])
        confidence = sims[0][1]

        print('\n')
        print(tokens)
        tokens_el = Snippet.as_elements(tokens)
        print(tokens_el)
        print('\n')

        path = os.path.join(tests_data, test_dir)
        snippet_id = Chunk.load_snippet_id(sims[0][0], path=path)
        matched_code = Snippet.load(snippet_id, path=path)

        matched_tokens = Snippet.as_tokens(str(matched_code))
        print(matched_tokens)
        tokens_el = Snippet.as_elements(matched_tokens)
        print(tokens_el)
        print('\n')
        print(sims)
        print('\n')

        # assert confidence > 0.95

        snippet_id = sims[0][0]
        print('Iterations: ' + str(model2.epochs))
        print('Confidence: ' + str(confidence))
        print('Snippet ID: ' + snippet_id)
        print('\n')

        # assert snippet_id == '2-1-4915-1362490'

        print('The 100 most frequent words:')
        print(model.wv.index2entity[:100])


evaluate()
