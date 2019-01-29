import os.path

from gensim.models.doc2vec import Doc2Vec
from github import Github
from pull_request import ReviewedPullRequest
from trainer import SnippetsTrainer
from snippet import Snippet
from utils import get_project_root

g = Github("medariox", "comliebt92")

repo = g.get_repo("requests/requests")
pulls = repo.get_pulls(state='all')


review_count = 0
snippets = []

for pull in pulls:

    pull_request = ReviewedPullRequest(repo.id, pull)
    if pull_request.has_valid_review():
        snippets += pull_request.snippets()
        pull_request.save()
        review_count += 1

    if review_count == 10:
        break

SnippetsTrainer(snippets).train()


def eval_model():
    path = get_project_root()
    model_path = os.path.join(path, 'data', 'd2v.model')
    model = Doc2Vec.load(model_path)

    tokens = Snippet.tokenize('assert normalize_percent_encode(p.url) == expected')
    print(tokens)
    new_vector = model.infer_vector(tokens)
    sims = model.docvecs.most_similar([new_vector])

    print(sims)
    snippet_id = sims[0][0]
    print('--------------------------------------')
    print('For {input} matched {result}!'.format(input=tokens,
                                                 result=snippet_id))
    print(Snippet.load(snippet_id))


eval_model()
