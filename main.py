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
    collector.collect(limit=20)
    SnippetTrainer(collector.repo_id).train(iterations=20, force=False)


train('psf/requests')


def evaluate(repo_id):
    path = get_project_root()
    model_path = os.path.join(path, 'data', str(repo_id), 'd2v.model')
    model = Doc2Vec.load(model_path)

    code = [
        """
        def normalize_percent_encode(x):
            # Helper function that normalizes equivalent
            # percent-encoded bytes before comparisons
            for c in re.findall(r'%[a-fA-F0-9]{2}', x):
                x = x.replace(c, c.upper())
            return x
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

    tokens = Snippet.as_tokens(code2)
    print(tokens)

    elements = Snippet.as_elements(code2)
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

    print('--------------------------------------')
    snippet_id = Chunk.load_snippet_id(match_id)
    snippet = Snippet.load(snippet_id)
    for chunk in snippet.chunks:
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        print(str(chunk))

    print('--------------------------------------')
    pr_number, repo_id = Chunk.pr_id_from_hash(match_id)
    print('Reason:')
    reviews = Review.load(pr_number, repo_id)
    for review in reviews:
        print('Rating:')
        print(review.rating)
        print('Body:')
        print(review.body)


evaluate('1362490')
