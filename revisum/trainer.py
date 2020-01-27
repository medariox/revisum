import os.path
import pickle

from collections import OrderedDict

from gensim.models.doc2vec import Doc2Vec, TaggedDocument

from .snippet import Snippet
from .utils import get_project_root
from .database.snippet import maybe_init, Snippet as DataSnippet
from .metrics import Metrics


class SnippetsTrainer(object):

    def __init__(self, snippets=None, repo_id=None, path=None, external=False):
        if not (snippets or (repo_id and path)):
            raise ValueError('SnippetsTrainer needs either snippets or repo_id')

        self._snippets = snippets or self._from_db(repo_id, path)
        self.repo_id = repo_id
        self.external = external
        self._tokens = []
        self._tagged_data = []

    @property
    def snippets(self):
        """
        Gets all the snippets used for the training.

        :return: All the availible snippets.
        :type: list
        """
        if not isinstance(self._snippets, list):
            self._snippets = [self._snippets]

        return self._snippets

    @property
    def tokens(self):
        """
        Snippets used for the training as tokens.

        :return: List of tokens.
        :type: list
        """
        if not self._tokens:
            if self.external:
                self._tokens = [{'0': self.snippets}]
            else:
                self._tokens = [
                    self._to_tokens(s) for s in self.snippets
                ]

        return self._tokens

    @property
    def tagged_data(self):
        if not self._tagged_data:
            self._make_tagged_data()

        return self._tagged_data

    def _make_tagged_data(self):
        tagged_data = []

        for snippet in self.snippets:

            chunks = OrderedDict()
            for chunk in snippet._chunks:
                chunks[chunk.b64_hash] = chunk

            for b64_hash, unique_chunk in chunks.items():
                tagged_line = TaggedDocument(words=unique_chunk.merged_tokens,
                                             tags=[b64_hash])
                tagged_data.append(tagged_line)

        self._tagged_data = tagged_data

    @staticmethod
    def _to_tokens(snippet):
        """
        Represent a whole snippet as a single list of tokens.

        :type: list
        """
        snippet_lines = []
        # Only use target snippets for now
        for line in snippet.to_tokens('target'):
            snippet_lines += line

        return {snippet.snippet_id: snippet_lines}

    @staticmethod
    def _from_db(repo_id, path=None):
        return Snippet.load_all(repo_id, path)

    def evaluate(self, repo_id, threshold=0.75):
        path = get_project_root()
        model_path = os.path.join(path, 'data', str(repo_id), 'd2v.model')
        if not os.path.isfile(model_path):
            return []

        model = Doc2Vec.load(model_path)
        results = []
        for snippet_tokens in self.tokens:
            snippet = {}
            for snippet_id, token_list in snippet_tokens.items():
                new_vector = model.infer_vector(token_list)
                sims = model.docvecs.most_similar([new_vector])

                candidates = [{'id': snip[0], 'confidence': snip[1]}
                              for snip in sims if snip[1] >= threshold]
                if candidates:
                    snippet['id'] = snippet_id
                    snippet['candidates'] = candidates

                    results.append(snippet)

        return results

    def train(self, repo_id, iterations=100, force=False, path=None):
        if path is not None:
            model_dir = path
        else:
            model_dir = os.path.join(get_project_root(), 'data', str(repo_id))

        model_path = os.path.join(model_dir, 'd2v.model')

        if not self.tagged_data:
            print('Nothing to train for: {0}'.format(repo_id))
            return

        if force or not os.path.isfile(model_path):
            if not os.path.isdir(model_dir):
                os.makedirs(model_dir)

            print('Building new vocabulary')
            model = Doc2Vec(vector_size=50,
                            alpha=0.025,
                            # min_alpha=0.00025,
                            min_count=2,
                            dm=0,
                            hs=1)
            model.build_vocab(self.tagged_data)
        else:
            print('Updating existing vocabulary')
            model = Doc2Vec.load(model_path)
            model.trainables.reset_weights(model.hs, model.negative, model.wv, model.docvecs)
            # model.build_vocab(tagged_data, update=True)

        self.iterate(iterations, repo_id=repo_id, model=model,
                     model_path=model_path)

        metrics = Metrics(repo_id)
        metrics.save()

    def iterate(self, times, **kwargs):
        repo_id = kwargs.get('repo_id') or self.repo_id
        if not times or times < 1:
            print('No iterations for: {0}'.format(repo_id))
            return

        model = kwargs['model']
        model_path = kwargs.get('model_path')
        # Reset iterations
        model.trainables.reset_weights(model.hs, model.negative, model.wv, model.docvecs)
        model.train(documents=self.tagged_data,
                    total_examples=model.corpus_count,
                    epochs=times)

        print('Unique word tokens: {0}'.format(len(model.wv.vocab)))
        print('Trained document tags: {0}'.format(len(model.docvecs)))

        model.save(model_path)
        print('Model saved for: {0}'.format(repo_id))
