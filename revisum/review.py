from database.review import Review, maybe_init


class ValidReview(object):

    def __init__(self, repo_id, pr_number, pr_merged, comment, state=None):
        self.repo_id = repo_id
        self.pr_number = pr_number
        self.pr_merged = pr_merged
        self.body = comment.body
        self.comment_id = comment.id
        self.user_id = comment.user.id
        self.user_login = comment.user.login
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

        review = Review.select().where(
            (Review.pr_number == pr_number) &
            (Review.repo_id == repo_id))

        if review:
            return review

        return []

    @classmethod
    def newest_accepted(cls, repo_id):
        maybe_init(repo_id)

        review = (Review.select(Review.pr_number).where(
            (Review.repo_id == repo_id) &
            (Review.state.in_(['APPROVED', 'CLOSED'])))
            .order_by(Review.pr_number.desc())
            .first())

        if review:
            return review.pr_number

    def save(self):
        maybe_init(self.repo_id)

        review = Review.get_or_none(comment_id=self.comment_id)
        if review:
            (Review
             .update(comment_id=self.comment_id,
                     pr_number=self.pr_number,
                     pr_merged=self.pr_merged,
                     repo_id=self.repo_id,
                     state=self.state,
                     rating=self.rating,
                     user_id=self.user_id,
                     user_login=self.user_login,
                     body=self.body)
             .where(Review.comment_id == self.comment_id)
             .execute())
        else:
            (Review
             .create(comment_id=self.comment_id,
                     pr_number=self.pr_number,
                     pr_merged=self.pr_merged,
                     repo_id=self.repo_id,
                     state=self.state,
                     rating=self.rating,
                     user_id=self.user_id,
                     user_login=self.user_login,
                     body=self.body))
