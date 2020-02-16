import hug

from revisum.pull_request import PullRequest
from revisum.trainer import SnippetTrainer
from revisum.collector import SnippetCollector
from revisum.snippet import Snippet
from revisum.review import Review
from revisum.chunk import Chunk


@hug.get('/snippets/{snippet_id}')
def retrieve_snippet(snippet_id: hug.types.text):
    snippet = Snippet.load(snippet_id)

    return snippet.to_json()


@hug.get('/snippets/{snippet_id}/reviews')
def retrieve_reviews(snippet_id: hug.types.text):
    snippet = Snippet.load(snippet_id)

    return snippet.to_json()['reviews']


@hug.get('/chunks/{chunk_id}')
def retrieve_chunk(chunk_id: hug.types.text):
    chunk = Chunk.load(chunk_id)

    return chunk.to_json()


@hug.get('/chunks/{chunk_id}/compare/{other_chunk_id}')
def compare_chunk(chunk_id: hug.types.text, other_chunk_id: hug.types.text):
    chunk = Chunk.compare(chunk_id, other_chunk_id)

    return chunk


@hug.get('/repos/{repo_id}/reviews/{pull_id}')
def retrieve_review(repo_id: hug.types.number, pull_id: hug.types.number):
    db_review = Review.load_single(repo_id, pull_id)

    return db_review


@hug.get('/repos/{repo_id}/snippets')
def evaluate_snippet(repo_id: hug.types.number, snippet_url: hug.types.text,
                     threshold: float = 0.75):
    snippet = SnippetCollector(repo_id).from_remote(snippet_url)
    if not snippet:
        return []

    return SnippetTrainer(repo_id, [snippet]).evaluate(
        threshold=threshold
    )


@hug.get('/repos/{repo_id}/pulls/{pull_number}')
def evaluate_pull(repo_id: hug.types.number, pull_number: hug.types.number,
                  threshold: float = 0.75):
    snippets = PullRequest(repo_id, pull_number).snippets

    return SnippetTrainer(repo_id, snippets).evaluate(
        threshold=threshold
    )


@hug.put('/repos/{repo_id}/collect')
def collect(repo_id: hug.types.number, limit: hug.types.number = 10, iterations: hug.types.number = 20):
    SnippetCollector(repo_id).collect(limit=limit)
    SnippetTrainer(repo_id).train(iterations=iterations)

    return 'Finished collecting and training for repository: {0}'.format(repo_id)


@hug.put('/repos/{repo_id}/train')
def train(repo_id: hug.types.number, iterations: hug.types.number = 20):
    SnippetTrainer(repo_id).train(iterations=iterations)

    return 'Finished training for repository: {0}'.format(repo_id)
