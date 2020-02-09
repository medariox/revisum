from collections import OrderedDict

from .database.review import Review as DataReview, maybe_init


class Review(object):

    def __init__(self, repo_id, pr_number, pr_merged, **kwargs):
        self.repo_id = repo_id
        self.pr_number = pr_number
        self.pr_merged = pr_merged
        self.body = kwargs['body']
        self.comment_id = kwargs['comment_id']
        self.user_id = kwargs['user_id']
        self.user_login = kwargs['user_login']
        self.state = kwargs['state']

    @property
    def rating(self):
        if self.state == 'CLOSED':
            return 1.0
        elif self.state == 'APPROVED' or self.pr_merged:
            return 5.0

        return 1.0

    @property
    def pull_id(self):
        return '{0}-{1}'.format(self.pr_number, self.repo_id)

    def to_json(self):
        review = OrderedDict()
        review['review_id'] = self.comment_id
        review['pull_id'] = self.pull_id
        review['rating'] = self.rating
        review['body'] = self.body

        return review

    @classmethod
    def load_single(cls, repo_id, review_id):
        maybe_init(repo_id)

        review = DataReview.get_or_none(
            DataReview.comment_id == review_id)
        if review:
            rev = cls(review.repo_id, review.pr_number, review.pr_merged,
                      body=review.body, comment_id=review.comment_id,
                      user_id=review.user_id, user_login=review.user_login,
                      state=review.state)
            return rev.to_json()

    @classmethod
    def load(cls, pr_number, repo_id):
        maybe_init(repo_id)

        db_reviews = DataReview.select().where(
            (DataReview.pr_number == pr_number) &
            (DataReview.repo_id == repo_id))

        reviews = []
        for review in db_reviews:
            rev = cls(review.repo_id, review.pr_number, review.pr_merged,
                      body=review.body, comment_id=review.comment_id,
                      user_id=review.user_id, user_login=review.user_login,
                      state=review.state)
            reviews.append(rev)

        return reviews

    @classmethod
    def newest_merged(cls, repo_id):
        maybe_init(repo_id)

        review = (DataReview.select(DataReview.pr_number).where(
            (DataReview.repo_id == repo_id) &
            (DataReview.pr_merged == 1))
            .order_by(DataReview.pr_number.desc())
            .first())

        if review:
            return review.pr_number

    def save(self):
        maybe_init(self.repo_id)

        review = DataReview.get_or_none(comment_id=self.comment_id)
        if review:
            (DataReview
             .update(comment_id=self.comment_id,
                     pr_number=self.pr_number,
                     pr_merged=self.pr_merged,
                     repo_id=self.repo_id,
                     state=self.state,
                     rating=self.rating,
                     user_id=self.user_id,
                     user_login=self.user_login,
                     body=self.body)
             .where(DataReview.comment_id == self.comment_id)
             .execute())
        else:
            (DataReview
             .create(comment_id=self.comment_id,
                     pr_number=self.pr_number,
                     pr_merged=self.pr_merged,
                     repo_id=self.repo_id,
                     state=self.state,
                     rating=self.rating,
                     user_id=self.user_id,
                     user_login=self.user_login,
                     body=self.body))
