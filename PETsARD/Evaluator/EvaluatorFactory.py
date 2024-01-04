from .Anonymeter.AnonymeterFactory import AnonymeterFactory


class EvaluatorFactory:
    def __init__(self, **kwargs):
        evaluating_method = kwargs.get('evaluating_method', None)

        if evaluating_method.startswith('anonymeter'):
            self.Evaluator = AnonymeterFactory(**kwargs).create_evaluator()
        else:
            raise ValueError(
                f"Evaluator - EvaluatorFactory: evaluating_method"
                f" {evaluating_method} didn't support."
            )

    def create_evaluator(self):
        return self.Evaluator
