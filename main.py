import os.path

from pathlib import Path

from gensim.models.doc2vec import Doc2Vec

from revisum.chunk import Chunk
from revisum.pull_request import PullRequest
from revisum.review import ValidReview
from revisum.snippet import Snippet
from revisum.trainer import SnippetsTrainer
from revisum.utils import get_project_root, gh_session
from revisum.parsers.python_parser import PythonFileParser

repo = gh_session().get_repo('psf/requests')


def train():
    pulls = repo.get_pulls(state='all', sort='updated', direction='desc')

    review_count = 0
    limit = 50
    snippets = []

    newest_review = ValidReview.newest_accepted(repo.id)

    for pull in pulls:

        if newest_review == pull.number:
            print('Reached newest review!')
            break

        pull_request = PullRequest(repo.id, pull.number, repo.full_name, pull.head.sha)
        if pull_request.is_valid:
            for snippet in pull_request.snippets:
                print('--------------------------------------------------------------------')
                print(str(snippet))
                print('--------------------------------------------------------------------')
            snippets += pull_request.snippets
            pull_request.save()
            review_count += 1

            print('Total reviews: [{count}/{limit}]'.format(count=review_count, limit=limit))
        if review_count == limit:
            break

    SnippetsTrainer(snippets).train(repo.id, iterations=20, force=False)


train()


def first_run(repo_id):
    cur_path = get_project_root()
    path = Path(os.path.join(cur_path, 'tmp'))

    snippets = []

    files = list(path.rglob('*.py'))
    for file_no, f in enumerate(files, 1):
        parser = PythonFileParser(0, repo_id, f)
        chunks = parser.parse(file_no=file_no)
        if not chunks:
            continue

        snippet_id = Snippet.make_id(0, file_no, 0, repo_id)
        snippet = Snippet(snippet_id, chunks, str(f), str(f))
        snippets.append(snippet)

    for snippet in snippets:
        snippet.save()
        for chunk in snippet._chunks:
            chunk.save(0, repo_id)

    SnippetsTrainer(snippets).train(repo_id, iterations=20, force=False)


first_run(repo.id)


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
    matched_code = Chunk.load(match_id)
    print(Chunk.as_text(matched_code, pretty=True))
    print(Chunk.as_tokens(matched_code))

    print('--------------------------------------')
    snippet_id = Chunk.load_snippet_id(match_id)
    chunks = Snippet.load(snippet_id)
    for chunk in chunks:
        print(str(chunk))

    print('--------------------------------------')
    pr_number, repo_id = Chunk.pr_id_from_hash(match_id)
    print('Reason:')
    reviews = ValidReview.load(pr_number, repo_id)
    for review in reviews:
        print('Rating:')
        print(review.rating)
        print('Body:')
        print(review.body)


evaluate('1362490')
