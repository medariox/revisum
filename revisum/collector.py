import os
import shutil
import zipfile
from pathlib import Path

import requests

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
            snippet = Snippet(snippet_id, chunks, f, f)
            snippets.append(snippet)

        for snippet in snippets:
            snippet.save()
            for chunk in snippet.chunks:
                chunk.save(0, self.repo_id)

        if delete:
            print('Deleting brach folder {0}...'.format(self.repo_id))
            shutil.rmtree(path)

        return snippets

    def from_pulls(self, update=True, limit=None):
        pulls = self._repo.get_pulls(state='all', sort='updated', direction='desc')
        newest_review = Review.newest_accepted(self._repo.id) if update else None
        limit = limit or 200

        review_count = 0
        snippets = []

        for pull in pulls:

            if newest_review and newest_review == pull.number:
                print('Reached newest review ({0})!'.format(newest_review))
                break

            pull_request = PullRequest(self._repo.id, pull.number, self._repo.full_name, pull.head.sha)
            if pull_request.is_valid:
                for snippet in pull_request.snippets:
                    print('-----------------------------------------------------------')
                    print(str(snippet))
                    print('-----------------------------------------------------------')

                snippets += pull_request.snippets
                pull_request.save()
                review_count += 1

                print('Total reviews: [{count}/{limit}]'.format(count=review_count, limit=limit))

            if review_count == limit:
                print('Reached reviews limit ({0})!'.format(limit))
                break

        return snippets
