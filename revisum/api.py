import hug
import requests

from revisum.pull_request import PullRequest
from revisum.trainer import SnippetTrainer
from revisum.collector import SnippetCollector
from revisum.snippet import Snippet
from revisum.review import Review
from revisum.utils import gh_session


@hug.get('/snippets/{snippet_id}')
def retrieve(snippet_id: hug.types.text):
    snippet = Snippet.load(snippet_id)

    if snippet:
        reviews = Review.load(Snippet.pr_number(snippet_id),
                              Snippet.repo_id(snippet_id))

        revs = [{'rating': review.rating, 'body': review.body}
                for review in reviews]

        return {
            'snippet_id': snippet_id,
            'reviews': revs,
            'tokens': snippet.to_tokens()
        }


@hug.get('/repos/{repo_id}/snippets')
def evaluate_code(repo_id: hug.types.number, snippet_url: hug.types.text,
                  threshold: float = 0.75):
    snippet = SnippetCollector(repo_id).from_remote(snippet_url)

    return SnippetTrainer(repo_id, snippet).evaluate(
        threshold=threshold
    )


@hug.get('/repos/{repo_id}/pulls/{pull_number}')
def evaluate_snippet(repo_id: hug.types.number, pull_number: hug.types.number,
                     threshold: float = 0.75):
    snippets = PullRequest(repo_id, pull_number).snippets

    return SnippetTrainer(repo_id, snippets).evaluate(
        threshold=threshold
    )


@hug.put('/repos/{repo_id}/train')
def train(repo_id: hug.types.number, limit: hug.types.number = 10, iterations: hug.types.number = 100):
    snippets = SnippetCollector(repo_id).from_pulls(limit=limit)

    SnippetTrainer(repo_id, snippets).train(iterations=iterations, force=True)
    return 'Finished training for repository: {0}'.format(repo_id)
