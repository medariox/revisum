from ast import parse
from collections import OrderedDict

from cognitive_complexity.api import get_cognitive_complexity
from radon.complexity import cc_visit_ast
from radon.raw import analyze
from sortedcontainers import SortedList

from .database.chunk import maybe_init as maybe_init_chunks, Chunk as DataChunk
from .database.metrics import maybe_init, Metrics as DataMetrics


class MetricsException(Exception):
    pass


class Metrics(object):

    def __init__(self, repo_id, code=None):
        self.repo_id = repo_id
        self._code = code
        self._db_data = {}

        self._metrics = ['sloc', 'complexity', 'cognitive']
        self._thresholds = {'low': 1, 'med': 2, 'high': 3, 'very_high': 4}

        self._sloc = None
        self._complexity = None
        self._cognitive = None
        self._ast_node = None
        self._rating = None

        if code:
            self.sloc
            self.complexity
            self.cognitive

    def to_json(self):
        metrics = OrderedDict()
        metrics['rating'] = self.rating
        metrics['metrics'] = {
            'sloc': self.sloc,
            'complexity': self.complexity,
            'cognitive': self.cognitive
        }

        return metrics

    @property
    def sloc(self):
        if self._sloc is None:
            try:
                raw = analyze(self._code)
                self._sloc = raw.sloc
            except SyntaxError as e:
                raise MetricsException('Error while computing Sloc:\n{0!r}'.format(e))

        return self._sloc

    @sloc.setter
    def sloc(self, value):
        self._sloc = value

    @property
    def complexity(self):
        if self._complexity is None:
            comp = cc_visit_ast(self.ast_node)
            if not comp:
                raise MetricsException('Error while computing Complexity: no result')
            else:
                self._complexity = sum(c.complexity for c in comp)

        return self._complexity

    @complexity.setter
    def complexity(self, value):
        self._complexity = value

    @property
    def cognitive(self):
        if self._cognitive is None:
            cog = self.ast_node
            if not cog:
                raise MetricsException('Error while computing Cognitive complexity: no result')
            else:
                self._cognitive = get_cognitive_complexity(cog.body[0])

        return self._cognitive

    @cognitive.setter
    def cognitive(self, value):
        self._cognitive = value

    @property
    def ast_node(self):
        if not self._ast_node:
            try:
                self._ast_node = parse(self._code)
            except SyntaxError as e:
                raise MetricsException('Error while computing Ast:\n{0!r}'.format(e))

        return self._ast_node

    @property
    def rating(self):
        if self._rating is None:
            self._rating = self.from_db()

        return self._rating

    def risk_profile(self, metric, threshold):
        if not self._db_data:
            self.from_chunks()

        if metric in self._metrics and threshold in self._thresholds:
            metric_len = len(self._db_data[metric])
            th = metric_len / 5 * self._thresholds[threshold]
            return self._db_data[metric][int(th) - 1]

    def from_chunks(self):
        maybe_init_chunks(self.repo_id)

        db_metrics = {}
        data = DataChunk.select(DataChunk.sloc, DataChunk.complexity,
                                DataChunk.cognitive)
        for metric in self._metrics:
            db_metrics[metric] = SortedList(getattr(d, metric) for d in data)

        self._db_data = db_metrics

    def from_db(self):
        maybe_init(self.repo_id)

        query = DataMetrics.select().namedtuples()
        thresholds = OrderedDict()
        for metric in query:
            thresholds[metric.name] = {
                5: metric.low, 4: metric.med,
                3: metric.high, 2: metric.very_high
            }

        metrics_count = len(self._metrics)
        ratings = [1 for m in range(metrics_count)]
        for i, met in enumerate(self._metrics):
            measured = getattr(self, met)
            for rating, threshold in thresholds[met].items():
                if measured <= threshold:
                    ratings[i] = rating
                    break

        return round(sum(ratings) / metrics_count, 2)

    def save(self):
        maybe_init(self.repo_id)
        print('Saving metrics for: {0}...'.format(self.repo_id))

        for metric in self._metrics:
            met = DataMetrics.get_or_none(name=metric)
            if met:
                (DataMetrics
                 .update(name=metric,
                         low=self.risk_profile(metric, 'low'),
                         med=self.risk_profile(metric, 'med'),
                         high=self.risk_profile(metric, 'high'),
                         very_high=self.risk_profile(metric, 'very_high'))
                 .where(DataMetrics.name == metric)
                 .execute())
            else:
                (DataMetrics
                 .create(name=metric,
                         low=self.risk_profile(metric, 'low'),
                         med=self.risk_profile(metric, 'med'),
                         high=self.risk_profile(metric, 'high'),
                         very_high=self.risk_profile(metric, 'very_high')))
