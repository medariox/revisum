import hug
import requests

from pull_request import ReviewedPullRequest
from trainer import SnippetsTrainer
from snippet import Snippet
from review import ValidReview
from utils import gh_session


@hug.get('/snippets/{snippet_id}')
def retrieve(snippet_id: hug.types.text):
    snippet = Snippet.load(snippet_id)

    if snippet:
        reviews = ValidReview.load(Snippet.pr_number(snippet_id),
                                   Snippet.repo_id(snippet_id))

        revs = [{'rating': review.rating, 'body': review.body}
                for review in reviews]

        return {
            'id': snippet_id,
            'reviews': revs,
            'tokens': snippet.as_tokens('target')
        }


@hug.get('/repos/{repo_id}')
def evaluate_code(repo_id: hug.types.number, snippet_url: hug.types.text,
                  threshold: float = 0.75):
    response = requests.get(snippet_url)
    code = [line for line in response.iter_lines(decode_unicode=True)]
    snippet = Snippet.tokenize(code)

    return SnippetsTrainer(snippet, external=True).evaluate(
        repo_id=repo_id, threshold=threshold
    )


@hug.get('/repos/{repo_id}/pulls/{pull_id}')
def evaluate_snippet(repo_id: hug.types.number, pull_id: hug.types.number,
                     threshold: float = 0.75):
    snippets = ReviewedPullRequest(repo_id, pull_id).snippets()

    return SnippetsTrainer(snippets).evaluate(
        repo_id=repo_id, threshold=threshold
    )


@hug.put('/repos/{repo_id}/train')
def train(repo_id: hug.types.number, limit: hug.types.number = 10,
          iterations: hug.types.number = 100):
    pulls = gh_session().get_repo(repo_id).get_pulls(state='all')

    review_count = 0
    snippets = []
    for pull in pulls:
        pull_request = ReviewedPullRequest(repo_id, pull.number)
        if pull_request.has_valid_review():
            snippets += pull_request.snippets()
            pull_request.save()
            review_count += 1

        if review_count == limit:
            break

    SnippetsTrainer(snippets).train(
        repo_id=repo_id, iterations=iterations, force=True
    )
    return 'Finished training for repository: {0}'.format(repo_id)
