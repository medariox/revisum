from gensim.models.doc2vec import Doc2Vec
from github import Github
from pull_request import ReviewedPullRequest
from trainer import SnippetsTrainer


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
    model = Doc2Vec.load("d2v.model")

    tokens = "param_ordered_dict = collections.OrderedDict((('z', 1), ('a', 1), ('k', 1), ('d', 1)))".split()
    new_vector = model.infer_vector(tokens)
    sims = model.docvecs.most_similar([new_vector])

    print(sims)
    print('--------------------------------------')
    print('For {input} matched {result}!'.format(input=tokens, result=sims[0][0]))


eval_model()
