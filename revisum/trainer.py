import os.path

from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from utils import get_project_root


class SnippetsTrainer(object):

    def __init__(self, snippets):
        self._snippets = snippets

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

    def train(self, update=False):
        path = get_project_root()
        model_path = os.path.join(path, 'data', 'd2v.model')

        tagged_data = []
        for snippet in self.snippets:
            snippet_lines = []
            # Only use target snippets for now
            for line in snippet.as_tokens('target'):
                snippet_lines += line
            print(snippet_lines)
            tagged_line = TaggedDocument(words=snippet_lines,
                                         tags=[snippet.snippet_id])
            tagged_data.append(tagged_line)

        if not update:
            model = Doc2Vec(vector_size=50,
                            alpha=0.025,
                            min_alpha=0.00025,
                            min_count=1,
                            dm=0)
            model.build_vocab(tagged_data)
        else:
            model = Doc2Vec.load(model_path)
            model.build_vocab(tagged_data, update=True)

        for epoch in range(100):
            print('Training iteration: {0}'.format(epoch))
            model.train(tagged_data,
                        total_examples=model.corpus_count,
                        epochs=model.epochs)

        model.save(model_path)
        print('Model saved')
