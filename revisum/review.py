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

    @classmethod
    def load(cls, pr_number, repo_id):
        maybe_init(repo_id)

        review = Review.get_or_none(pr_number=pr_number,
                                    repo_id=repo_id)
        if review:
            return review.body

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
                     user_id=self.user_id,
                     user_login=self.user_login,
                     body=self.body))
