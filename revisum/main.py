import os.path

from gensim.models.doc2vec import Doc2Vec

from pull_request import ReviewedPullRequest
from review import ValidReview
from snippet import Snippet
from trainer import SnippetsTrainer
from utils import get_project_root, gh_session


def train():
    repo = gh_session().get_repo('keon/algorithms')
    pulls = repo.get_pulls(state='all')

    review_count = 0
    limit = 50
    snippets = []

    for pull in pulls:

        pull_request = ReviewedPullRequest(repo.id, pull.number)
        if pull_request.has_valid_review() and pull_request.snippets:
            for snippet in pull_request.snippets:
                print('--------------------------------------------------------------------')
                print(snippet.target_lines())
                print('--------------------------------------------------------------------')
            snippets += pull_request.snippets
            pull_request.save()
            review_count += 1

        print('Total reviews: [{count}/{limit}]'.format(count=review_count,
                                                        limit=limit))
        if review_count == limit:
            break

    SnippetsTrainer(snippets).train(repo.id, force=False)

# train()


def evaluate(repo_id):
    path = get_project_root()
    model_path = os.path.join(path, 'data', str(repo_id), 'd2v.model')
    model = Doc2Vec.load(model_path)

    old_code = [
        'try:', 'return complexjson.loads(self.text, **kwargs)',
        'except JSONDecodeError:',
        "print('Response content is not in the json format')"
    ]

    code = [
        'while', 'power', '>', '0', ':',
        'if', 'power', '&', '1', ':',
        'result', '=', '(', 'result', '*', 'base',
        ')', '%', 'mod', 'power', '=', 'power', '>>', '1',
        'base', '=', '(', 'base', '*', 'base', ')', '%', 'mod',
        'return', 'result'
    ]

    tokens = Snippet.tokenize(code)
    print(tokens)

    tokens_el = Snippet.tokenize_el(code)
    print(tokens_el)

    new_vector = model.infer_vector(tokens)
    sims = model.docvecs.most_similar([new_vector])
    print(sims)

    print('The 100 most frequent words:')
    print(model.wv.index2entity[:100])

    snippet_id = sims[0][0]
    print('--------------------------------------')
    print('For {input} matched {result}!'.format(
        input=tokens, result=snippet_id))

    matched_code = Snippet.load(snippet_id)
    print(matched_code)
    matched_tokens = Snippet.tokenize(str(matched_code))
    print(matched_tokens)

    print('Reason:')
    reviews = ValidReview.load(
        Snippet.pr_number(snippet_id), Snippet.repo_id(snippet_id))
    for review in reviews:
        print('Rating:')
        print(review.rating)
        print('Body:')
        print(review.body)


evaluate('74073233')
