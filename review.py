
import requests
from github import Github
from unidiff import PatchSet
from snippet import Snippet
from trainer import SnippetsTrainer

from gensim.models.doc2vec import Doc2Vec

g = Github("medariox", "comliebt92")

repo = g.get_repo("requests/requests")
pulls = repo.get_pulls(state='all')


class WeightedReview(object):

    def __init__(self, repo_id, pull):
        self._patch_content = None
        self.repo_id = repo_id
        self.id = pull.id
        self.number = pull.number
        self.title = pull.title
        self.state = pull.state
        self.merged = pull.merged
        self.patch_url = pull.patch_url
        # self.patch_url = 'https://patch-diff.githubusercontent.com/raw/pymedusa/Medusa/pull/5643.patch'
        # self.patch_url = 'https://patch-diff.githubusercontent.com/raw/pymedusa/Medusa/pull/5813.patch'

        print(self.repo_id)

    @staticmethod
    def is_supported(target_file):
        if target_file.endswith('.py'):
            return True
        return False

    def snippets(self):
        patch = PatchSet(self.patch_content)

        self.snippets = []
        for file_no, change in enumerate(patch, 1):
            if not self.is_supported(change.target_file):
                continue

            for hunk_no, hunk in enumerate(change, 1):
                snippet_id = '-'.join([str(file_no), str(hunk_no), str(self.number)])
                snippet = Snippet(snippet_id, hunk, change.source_file, change.target_file)
                self.snippets.append(snippet)

        return self.snippets

    @property
    def patch_content(self):
        """
        Gets the content of the pull request patch.

        :return: The content of the patch.
        :type: str
        """
        if not self._patch_content:
            response = requests.get(self.patch_url)
            self._patch_content = response.text

        return self._patch_content

    @patch_content.setter
    def patch_content(self, content):
        """
        Sets the content of the pull request patch.

        :param content: The content of the patch.
        :type: str
        """
        self._patch_content = content


review_count = 0
snippets = []
for pull in pulls:
    reviews = pull.get_reviews()
    rev_len = reviews.totalCount
    if rev_len == 0:
        print("No reviews for {0}".format(pull.title))
        continue

    weighted_review = WeightedReview(repo.id, pull)
    snippets += weighted_review.snippets()

    review_count += 1
    if review_count == 10:
        break

SnippetsTrainer(snippets).train()


def eval_model():
    model = Doc2Vec.load("d2v.model")

    tokens = "from six import text_type".split()
    new_vector = model.infer_vector(tokens)
    sims = model.docvecs.most_similar([new_vector])

    print(sims)
    print('--------------------------------------')
    print('For {input} matched {result}!'.format(input=tokens, result=sims[0][0]))


eval_model()
