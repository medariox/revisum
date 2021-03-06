import os.path
from collections import OrderedDict

from gensim.models.doc2vec import Doc2Vec, TaggedDocument

from .snippet import Snippet
from .utils import get_project_root


class SnippetTrainer(object):

    def __init__(self, repo_id, snippets=None, path=None, external=False):
        self._snippets = snippets or Snippet.load_all(repo_id, merged_only=True, path=path)
        self.repo_id = repo_id
        self.external = external
        self._tokens = []
        self._tagged_data = []

    @property
    def snippets(self):
        """
        Snippets used for the training.

        :return: All the availible snippets.
        :type: generator
        """
        return iter(self._snippets)

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
            self._tagged_data = list(self._make_tagged_data())

        return self._tagged_data

    def _make_tagged_data(self):
        chunks_sha1 = set()

        for snippet in self.snippets:
            for chunk in snippet.chunks:
                # Skip chunks that were already added
                if chunk.sha1_hash in chunks_sha1:
                    continue

                chunks_sha1.add(chunk.sha1_hash)
                tagged_line = TaggedDocument(words=chunk.merged_tokens,
                                             tags=[chunk.chunk_id])
                yield tagged_line

    @staticmethod
    def _to_tokens(snippet):
        """
        Represent a whole snippet as a single list of tokens.

        :type: list
        """
        snippet_lines = []
        # Only use target snippets for now
        for line in snippet.to_tokens():
            snippet_lines += line

        return {snippet.snippet_id: snippet_lines}

    def evaluate(self, threshold=0.75):
        path = get_project_root()
        model_path = os.path.join(path, 'data', str(self.repo_id), 'd2v.model')
        if not os.path.isfile(model_path):
            return []

        model = Doc2Vec.load(model_path)

        results = []
        for snpt in self.snippets:
            snippet = OrderedDict()
            snippet['snippet_id'] = snpt.snippet_id

            for chnk in snpt.chunks:
                new_vector = model.infer_vector(chnk.merged_tokens)
                sims = model.docvecs.most_similar([new_vector])

                candidates = [{'chunk_id': snip[0], 'confidence': snip[1]}
                              for snip in sims if snip[1] >= threshold]

                chunk_info = chnk.to_json()
                chunk_info['candidates'] = candidates

                if snippet.get('chunks') is None:
                    snippet['chunks'] = [chunk_info]
                else:
                    snippet['chunks'].append(chunk_info)

            results.append(snippet)

        return results

    def train(self, iterations=20, force=False, path=None):
        if path is not None:
            model_dir = path
        else:
            model_dir = os.path.join(get_project_root(), 'data', str(self.repo_id))

        model_path = os.path.join(model_dir, 'd2v.model')

        if not self.tagged_data:
            print('Nothing to train for: {0}'.format(self.repo_id))
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
            # model.trainables.reset_weights(model.hs, model.negative, model.wv, model.docvecs)
            # model.build_vocab(tagged_data, update=True)

        self.iterate(iterations, model=model, model_path=model_path)

    def iterate(self, times, **kwargs):
        if not times or times < 1:
            print('No iterations for: {0}'.format(self.repo_id))
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
        print('Model saved for: {0}'.format(self.repo_id))
