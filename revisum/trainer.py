import os.path

from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from utils import get_project_root


class SnippetsTrainer(object):

    def __init__(self, snippets, external=False):
        self._snippets = snippets
        self.external = external
        self._tokens = []

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
        Gets all the snippets used for the training.

        :return: All the availible snippets.
        :type: list
        """
        if not self._tokens:
            if self.external:
                self._tokens = [self.snippets]
            else:
                self._tokens = [
                    self._to_tokens(s) for s in self.snippets
                ]

        return self._tokens

    @staticmethod
    def _to_tokens(snippet):
        """
        Represent a snippet as a single list of tokens.

        :type: list
        """
        snippet_lines = []
        # Only use target snippets for now
        for line in snippet.as_tokens('target'):
            snippet_lines += line

        return snippet_lines

    def evaluate(self, repo_id, threshold=0.75):
        path = get_project_root()
        model_path = os.path.join(path, 'data', str(repo_id), 'd2v.model')
        if not os.path.isfile(model_path):
            return []

        model = Doc2Vec.load(model_path)
        for token_list in self.tokens:
            print(token_list)
            new_vector = model.infer_vector(token_list)
            sims = model.docvecs.most_similar([new_vector])
            print(sims)

        best_snippets = [snip[0] for snip in sims if snip[1] >= threshold]
        return best_snippets

    def train(self, repo_id, force=False):
        path = get_project_root()
        model_dir = os.path.join(path, 'data', str(repo_id))
        model_path = os.path.join(model_dir, 'd2v.model')

        tagged_data = []
        for snippet in self.snippets:
            tagged_line = TaggedDocument(words=self._to_tokens(snippet),
                                         tags=[snippet.snippet_id])
            tagged_data.append(tagged_line)

        if force or not os.path.isfile(model_path):
            if not os.path.isdir(model_dir):
                os.makedirs(model_dir)

            print('Building new vocabulary')
            model = Doc2Vec(vector_size=50,
                            alpha=0.025,
                            min_alpha=0.00025,
                            min_count=1,
                            hs=1,
                            dm=0)
            model.build_vocab(tagged_data)
        else:
            print('Updating existing vocabulary')
            model = Doc2Vec.load(model_path)
            model.build_vocab(tagged_data, update=True)

        for epoch in range(100):
            print('Training iteration: {0}'.format(epoch))
            model.train(tagged_data,
                        total_examples=model.corpus_count,
                        epochs=model.epochs)

        model.save(model_path)
        print('Model saved for: {0}'.format(repo_id))
