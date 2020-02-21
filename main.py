import os

from gensim.models.doc2vec import Doc2Vec

from revisum.chunk import Chunk
from revisum.review import Review
from revisum.snippet import Snippet
from revisum.trainer import SnippetTrainer
from revisum.collector import SnippetCollector
from revisum.utils import get_project_root


def collect(repo_name):
    print('Collecting and training {0} started.'.format(repo_name))

    collector = SnippetCollector(repo_name)
    collector.collect(limit=10)
    SnippetTrainer(collector.repo_id).train(iterations=20, force=False)


collect('psf/requests')


def evaluate(repo_id):
    print('\nEvaluation for {0} started.'.format(repo_id))

    path = get_project_root()
    model_path = os.path.join(path, 'data', str(repo_id), 'd2v.model')
    model = Doc2Vec.load(model_path)

    code = [
        """
        def _handle_requests(self):
            for _ in range(self.requests_to_handle):
                sock = self._accept_connection()
                if not sock:
                    break

                handler_result = self.handler(sock)

                self.handler_results.append(handler_result)
                sock.close()
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

    print('\nReason:')
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
