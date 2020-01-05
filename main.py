import os.path

from gensim.models.doc2vec import Doc2Vec

from revisum.pull_request import ReviewedPullRequest
from revisum.review import ValidReview
from revisum.snippet import Snippet
from revisum.trainer import SnippetsTrainer
from revisum.utils import get_project_root, gh_session


def train():
    repo = gh_session().get_repo('psf/requests')
    pulls = repo.get_pulls(state='all', sort='updated', direction='desc')

    review_count = 0
    limit = 50
    snippets = []

    newest_review = ValidReview.newest_accepted(repo.id)

    for pull in pulls:

        if newest_review == pull.number:
            print('Reached newest review!')
            break

        pull_request = ReviewedPullRequest(repo.id, pull.number, repo.full_name, pull.head.sha)
        if pull_request.is_valid:
            for snippet in pull_request.snippets:
                print('--------------------------------------------------------------------')
                print(str(snippet))
                print('--------------------------------------------------------------------')
            snippets += pull_request.snippets
            pull_request.save()
            review_count += 1

            print('Total reviews: [{count}/{limit}]'.format(count=review_count,
                                                            limit=limit))
        if review_count == limit:
            break

    SnippetsTrainer(snippets).train(repo.id, iterations=20, force=False)


train()


def evaluate(repo_id):
    path = get_project_root()
    model_path = os.path.join(path, 'data', str(repo_id), 'd2v.model')
    model = Doc2Vec.load(model_path)

    old_code = [
        'try:', 'return complexjson.loads(self.text, **kwargs)',
        'except JSONDecodeError:',
        "print('Response content is not in the json format')"
    ]

    min_code = [
        """
        from .modular_Exponential import *
        """
    ]

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

    tokens = Snippet.tokenize(code2)
    print(tokens)

    tokens_el = Snippet.tokenize_el(code2)
    print(tokens_el)

    new_vector = model.infer_vector(tokens)
    sims = model.docvecs.most_similar([new_vector])
    print(sims)

    print('The 100 most frequent words:')
    print(model.wv.index2entity[:100])

    print('--------------------------------------')
    match_id = sims[0][0]
    print('For {input} matched {result}!'.format(
        input=tokens, result=match_id))

    print('--------------------------------------')
    matched_code = Snippet.load_chunk(match_id)
    print(str(matched_code))
    matched_tokens = Snippet.tokenize(str(matched_code))
    print(matched_tokens)

    # for chunk in matched_code:
    #     print(str(chunk))
    #     matched_tokens = Snippet.tokenize(str(chunk))
    #     print(matched_tokens)

    print('--------------------------------------')
    snippet_id = match_id.split('-', 1)[1]
    print('Reason:')
    reviews = ValidReview.load(
        Snippet.pr_number(snippet_id), Snippet.repo_id(snippet_id))
    for review in reviews:
        print('Rating:')
        print(review.rating)
        print('Body:')
        print(review.body)


evaluate('1362490')
