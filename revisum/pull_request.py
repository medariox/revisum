import requests

from unidiff import PatchSet

from .snippet import Snippet
from .review import Review
from .utils import gh_session, norm_path
from .parsers.python_parser import PythonFileParser


class PullRequest(object):
    ignored_bots = ['codecov-io', 'renovate[bot]', 'deepcode[bot]',
                    'coveralls']

    def __init__(self, repo_id, pr_number, repo_name=None, pr_head_sha=None):
        self._pull = None
        self._patch_content = None
        self._valid_reviews = []
        self._snippets = []

        self.repo_id = repo_id
        self.number = pr_number
        self.repo_name = repo_name
        self.head_sha = pr_head_sha

    @staticmethod
    def is_supported(target_file):
        if target_file.endswith('.py'):
            return True
        return False

    def change_url(self, path):
        url = 'https://raw.githubusercontent.com/{0}/{1}/{2}'.format(
            self.repo_name, self.head_sha, path
        )
        return url

    @property
    def snippets(self):
        if not self._snippets:
            self._make_snippets()
        return self._snippets

    @property
    def supported_snippets(self):
        if self.is_concluded and self.snippets:
            print('Found supported snippet(s) for: {0} [{1}]'.format(self.title, self.number))
            return True

        print('No supported snippet found for: {0} [{1}]'.format(self.title, self.number))
        return False

    def _make_snippets(self):
        patch = PatchSet(self.patch_content)

        for file_no, change in enumerate(patch, 1):
            if not self.is_supported(change.target_file):
                continue

            normed_path = norm_path(change.target_file)
            snippet_url = self.change_url(normed_path)
            raw_snippet = requests.get(snippet_url)
            if raw_snippet:
                parser = PythonFileParser(self.number, self.repo_id, normed_path, raw_snippet)

            for hunk_no, hunk in enumerate(change, 1):

                start = hunk.target_start
                stop = start + hunk.target_length - 1
                chunks = parser.parse_single(hunk_no, file_no, start, stop)
                if not chunks:
                    continue

                snippet_id = Snippet.make_id(hunk_no, file_no, self.number, self.repo_id)
                snippet = Snippet(snippet_id, self.merged, chunks, change.source_file, change.target_file)
                self._snippets.append(snippet)

    @property
    def pull(self):
        """
        Get the pull request.

        :return: The pull request.
        :type: PullRequest object
        """
        if not self._pull:
            pull = gh_session().get_repo(self.repo_id).get_pull(self.number)
            self._pull = pull

        return self._pull

    @property
    def patch_content(self):
        """
        Get the content of the pull request patch.

        :return: The content of the patch.
        :type: str
        """
        if not self._patch_content:
            response = requests.get(self.diff_url)
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

    @property
    def title(self):
        return self.pull.title

    @property
    def state(self):
        return self.pull.state

    @property
    def merged(self):
        return self.pull.merged

    @property
    def diff_url(self):
        return self.pull.diff_url

    @property
    def is_concluded(self):
        if self.state == 'closed' or self.merged:
            return True
        return False

    @property
    def valid_reviews(self):
        if not self._valid_reviews:
            self._has_valid_review()

        return self._valid_reviews

    def _has_valid_review(self):
        reviews = self.pull.get_reviews()
        rev_len = reviews.totalCount
        if rev_len > 0:
            for comment in reviews:
                if comment.body != '':
                    self._valid_reviews.append(
                        Review(self.repo_id, self.number,
                               self.merged, comment)
                    )

        if self._valid_reviews or self._closed_with_comment():
            print('Found review or comment for: {0} [{1}]'.format(self.title, self.number))
            return True

        print('No review found for: {0} [{1}]'.format(self.title, self.number))
        return False

    def _closed_with_comment(self):
        if not self.merged and self.state == 'closed':
            comments = self.pull.get_issue_comments()
            com_len = comments.totalCount
            if com_len > 0:
                # Skip comments that were made by these bots
                ignored_bots = PullRequest.ignored_bots
                for comment in comments:
                    if comment.user.login in ignored_bots:
                        continue
                    self._valid_reviews.append(
                        Review(self.repo_id, self.number, self.merged,
                               comment, state='CLOSED')
                    )
                return True

        return False

    def exists(self):
        for snippet in self.snippets:
            if snippet.exists():
                return True

        return False

    def save(self):
        print('Saving snippets for: {0}...'.format(self.repo_id))
        for snippet in self.snippets:
            snippet.save()
            for chunk in snippet.chunks:
                chunk.save(self.repo_id)

        if self.snippets:
            print('Saving reviews for: {0}...'.format(self.repo_id))
            for valid_review in self.valid_reviews:
                valid_review.save()
