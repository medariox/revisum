from .database.review import Review as DataReview, maybe_init


class Review(object):

    def __init__(self, repo_id, pr_number, pr_merged, comment, state=None):
        self.repo_id = repo_id
        self.pr_number = pr_number
        self.pr_merged = pr_merged
        self.body = comment.body
        self.comment_id = comment.id
        self.user_id = comment.user.id
        self.user_login = comment.user.loginsss
        self.state = state or comment.state

    @property
    def rating(self):
        if self.state == 'CLOSED':
            return 1.0
        elif self.state == 'APPROVED' or self.pr_merged:
            return 5.0

        return 1.0

    @classmethod
    def load(cls, pr_number, repo_id):
        maybe_init(repo_id)

        review = DataReview.select().where(
            (DataReview.pr_number == pr_number) &
            (DataReview.repo_id == repo_id))

        if review:
            return review

        return []

    @classmethod
    def newest_accepted(cls, repo_id):
        maybe_init(repo_id)

        review = (DataReview.select(DataReview.pr_number).where(
            (DataReview.repo_id == repo_id) &
            (DataReview.state.in_(['APPROVED', 'CLOSED'])))
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
