import requests

from unidiff import PatchSet

from .snippet import Snippet
from .review import ValidReview
from .utils import gh_session
from .parsers.python_parser import PythonFileParser


class ReviewedPullRequest(object):
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
    def _is_supported(target_file):
        if target_file.endswith('.py'):
            return True
        return False

    @property
    def is_valid(self):
        return self.has_valid_review() and self.has_valid_snippet()

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

    def has_valid_snippet(self):
        return bool(self.snippets)

    def _make_snippets(self):
        patch = PatchSet(self.patch_content)

        for file_no, change in enumerate(patch, 1):
            if not self._is_supported(change.target_file):
                continue

            snippet_url = self.change_url(change.path)
            raw_snippet = requests.get(snippet_url)
            if raw_snippet:
                parser = PythonFileParser(raw_snippet)

            for hunk_no, hunk in enumerate(change, 1):

                start = hunk.target_start
                stop = start + hunk.target_length
                chunks = parser.parse_single(start, stop)
                if not chunks:
                    continue

                snippet_id = '-'.join([str(hunk_no), str(file_no), str(self.number), str(self.repo_id)])
                snippet = Snippet(snippet_id, chunks, change.source_file, change.target_file)
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
    def valid_reviews(self):
        if self._valid_reviews or self.has_valid_review():
            return self._valid_reviews

    def has_valid_review(self):
        reviews = self.pull.get_reviews()
        rev_len = reviews.totalCount
        if rev_len > 0:
            for comment in reviews:
                if comment.body != '':
                    self._valid_reviews.append(
                        ValidReview(self.repo_id, self.number,
                                    self.merged, comment)
                    )

        if not self._valid_reviews and not self._closed_with_comment():
            print('No review for: {0} [{1}]'.format(self.title, self.number))
            return False

        if self._valid_reviews:
            print(
                'Found valid review for: {0} [{1}]'.format(
                    self.title, self.number
                )
            )
            return True

        print('No valid review for: {0} [{1}]'.format(self.title, self.number))
        return False

    def _closed_with_comment(self):
        if not self.merged and self.state == 'closed':
            comments = self.pull.get_issue_comments()
            com_len = comments.totalCount
            if com_len > 0:
                # Skip comments that were made by these bots
                ignored_bots = ReviewedPullRequest.ignored_bots
                for comment in comments:
                    if comment.user.login in ignored_bots:
                        continue
                    self._valid_reviews.append(
                        ValidReview(self.repo_id, self.number, self.merged,
                                    comment, state='CLOSED')
                    )
                return True

        return False

    def save(self):
        if self.valid_reviews:
            for snippet in self._snippets:
                snippet.save()

            for valid_review in self._valid_reviews:
                valid_review.save()
