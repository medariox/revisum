import os
import shutil
import zipfile
from pathlib import Path

import requests

from .metrics import Metrics
from .pull_request import PullRequest
from .review import Review
from .snippet import Snippet
from .utils import get_project_root, gh_session
from .parsers.python_parser import PythonFileParser


class SnippetCollector(object):

    def __init__(self, repo):
        self._gh_session = gh_session()
        self._repo = self._gh_session.get_repo(repo)
        self._tmp_dir = os.path.join(get_project_root(), 'data', 'tmp')

        self.repo_name = self._repo.raw_data['full_name']
        self.repo_id = self._repo.raw_data['id']
        self.branch = self._repo.default_branch

    def collect(self, limit):
        snippets = []

        if self._is_first_run():
            self._download_branch()
            self._unpack_branch()
            snippets += self.from_branch()

        snippets += self.from_pulls(limit=limit)

        if snippets:
            Metrics(self.repo_id).save()

        return snippets

    def _is_first_run(self):
        db_dir = os.path.join(get_project_root(), 'data', str(self.repo_id))
        if not os.path.isdir(db_dir):
            return True
        return False

    def _download_branch(self):
        url = 'https://codeload.github.com/{0}/zip/{1}'.format(self.repo_name, self.branch)
        response = requests.get(url, stream=True)

        file_name = '{0}.zip'.format(self.repo_id)
        file_path = os.path.join(self._tmp_dir, file_name)

        print('Downloading branch {0} for {1}...'.format(self.branch, self.repo_name))
        with open(file_path, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)

        print('Download completed!')
        del response

    def _unpack_branch(self):
        file_name = '{0}.zip'.format(self.repo_id)
        source = os.path.join(self._tmp_dir, file_name)
        dest = os.path.join(self._tmp_dir, str(self.repo_id))

        print('Unpacking file {0} for {1}...'.format(file_name, self.repo_name))
        with zipfile.ZipFile(source, 'r') as zip_ref:
            zip_ref.extractall(dest)

        print('Unpack completed!')
        os.remove(source)

    def from_branch(self, delete=True):
        path = Path(os.path.join(self._tmp_dir, str(self.repo_id)))

        snippets = []

        files = list(path.rglob('*.py'))
        for file_no, f in enumerate(files, 1):
            parser = PythonFileParser(0, self.repo_id, f)
            chunks = parser.parse(file_no=file_no)
            if not chunks:
                continue

            snippet_id = Snippet.make_id(0, file_no, 0, self.repo_id)
            snippet = Snippet(snippet_id, True, chunks, f, f)
            snippets.append(snippet)

        print('Saving snippets for: {0}...'.format(self.repo_id))
        for snippet in snippets:
            snippet.save()
            for chunk in snippet.chunks:
                chunk.save(self.repo_id)

        if delete:
            print('Deleting branch folder {0}...'.format(self.repo_id))
            shutil.rmtree(path)

        return snippets

    def from_remote(self, snippet_url):
        raw_snippet = requests.get(snippet_url)
        if raw_snippet:
            parser = PythonFileParser(0, self.repo_id, snippet_url, raw_snippet)
            chunks = parser.parse()
            if not chunks:
                return

            snippet_id = Snippet.make_id(0, 0, 0, self.repo_id)
            snippet = Snippet(snippet_id, False, chunks, snippet_url, snippet_url)
            return snippet

    def from_pulls(self, update=True, limit=None):
        pulls = self._repo.get_pulls(state='all', sort='updated', direction='desc')
        newest_review = Review.newest_merged(self._repo.id) if update else None
        limit = limit or 200

        snippets_count = 0
        snippets = []

        for pull in pulls:

            if update and newest_review and newest_review == pull.number:
                print('Reached newest review ({0})!'.format(newest_review))
                break

            pull_request = PullRequest(self._repo.id, pull.number, self._repo.full_name, pull.head.sha)
            if pull_request.supported_snippets:

                if update and pull_request.merged and pull_request.exists():
                    print('Reached newest pull request ({0})!'.format(pull.number))
                    break

                snippets += pull_request.snippets
                pull_request.save()
                snippets_count += 1

                print('Total collected pull requests: [{count}/{limit}]'.format(count=snippets_count, limit=limit))

            if snippets_count == limit:
                print('Reached pull requests limit ({0})!'.format(limit))
                break

        return snippets
