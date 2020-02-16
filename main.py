import os

from gensim.models.doc2vec import Doc2Vec

from revisum.chunk import Chunk
from revisum.review import Review
from revisum.snippet import Snippet
from revisum.trainer import SnippetTrainer
from revisum.collector import SnippetCollector
from revisum.utils import get_project_root


def train(repo_name):

    collector = SnippetCollector(repo_name)
    collector.collect(limit=10)
    SnippetTrainer(collector.repo_id).train(iterations=20, force=False)


train('psf/requests')


def evaluate(repo_id):
    path = get_project_root()
    model_path = os.path.join(path, 'data', str(repo_id), 'd2v.model')
    model = Doc2Vec.load(model_path)

    code = [
        """
        def guess_filename(obj):
            name = getattr(obj, 'name', None)
            if (name and isinstance(name, basestring) and name[0] != '<' and
                name[-1] != '>'):
            return os.path.basename(name)
        """
    ]

    code2 = [
        """
        def __eq__(self, other):
            if isinstance(other, Mapping):
                other = CaseInsensitiveDict(other)
            else:
                return NotImplemented
            # Compare insensitively
            return dict(self.lower_items()) == dict(other.lower_items())
        """
    ]

    tokens = Snippet.as_tokens(code)
    print(tokens)

    elements = Snippet.as_elements(code)
    print(elements)

    new_vector = model.infer_vector(tokens)
    sims = model.docvecs.most_similar([new_vector])
    print(sims)

    print('The 100 most frequent words:')
    print(model.wv.index2entity[:100])

    print('--------------------------------------')
    match_id = sims[0][0]
    print('For {input} matched {result}!'.format(input=tokens, result=match_id))

    print('--------------------------------------')
    chunk = Chunk.load(match_id)
    print(chunk.as_text(pretty=True))
    print(chunk.as_tokens())
    print(chunk.as_tokens(pretty=True))

    print('--------------------------------------')
    snippet_id = Chunk.load_snippet_id(match_id)
    snippet = Snippet.load(snippet_id)
    print(str(snippet))

    print('--------------------------------------')
    repo_id = Chunk.repo_id(match_id)
    pr_number = Chunk.pr_number(match_id)
    print('Reason:')
    reviews = Review.load(pr_number, repo_id)
    for review in reviews:
        print('Rating:')
        print(review.rating)
        print('Body:')
        print(review.body)

    print('--------------------------------------')
    print('Unique word tokens: {0}'.format(len(model.wv.vocab)))
    print('Trained document tags: {0}'.format(len(model.docvecs)))


evaluate('1362490')
