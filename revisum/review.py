
import requests
from snippet import Snippet
from unidiff import PatchSet


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
        Get the content of the pull request patch.

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
        Set the content of the pull request patch.

        :param content: The content of the patch.
        :type: str
        """
        self._patch_content = content
