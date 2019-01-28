from database.review import Review, maybe_init


class ValidReview(object):

    def __init__(self, repo_id, pr_number, review):
        self.body = review.body
        self.repo_id = repo_id
        self.pr_number = pr_number
        self.review_id = review.id
        self.state = review.state

    def save(self):
        maybe_init(self.repo_id)

        review = Review.get_or_none(review_id=self.review_id)
        if review:
            (Review
             .update(review_id=self.review_id,
                     pr_number=self.pr_number,
                     repo_id=self.repo_id,
                     state=self.state,
                     body=self.body)
             .where(Review.review_id == self.review_id)
             .execute())
        else:
            (Review
             .create(review_id=self.review_id,
                     pr_number=self.pr_number,
                     repo_id=self.repo_id,
                     state=self.state,
                     body=self.body))
