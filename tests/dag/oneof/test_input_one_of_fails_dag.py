import typing as t

from ml_pipeline_engine.dag_builders.annotation.marks import Input
from ml_pipeline_engine.dag_builders.annotation.marks import InputOneOf
from ml_pipeline_engine.node import ProcessorBase
from ml_pipeline_engine.types import PipelineChartLike


class SomeInput(ProcessorBase):
    name = 'input'

    def process(self, base_num: int, other_num: int) -> dict:
        return {
            'base_num': base_num,
            'other_num': other_num,
        }


class ErrorDataSource(ProcessorBase):
    name = 'some_data_source'

    def process(self, _: Input(SomeInput)) -> t.Type[Exception]:
        raise Exception


class ErrorDataSourceSecond(ProcessorBase):
    name = 'some_data_source_second'

    def process(self, _: Input(SomeInput)) -> t.Type[Exception]:
        raise Exception


class SomeFeature(ProcessorBase):
    name = 'some_feature'

    def process(self, ds_value: Input(ErrorDataSource), inp: Input(SomeInput)) -> int:
        return ds_value + inp['other_num'] + 10


class SomeFeatureSecond(ProcessorBase):
    name = 'some_feature_second'

    def process(self, ds_value: Input(ErrorDataSourceSecond), inp: Input(SomeInput)) -> int:
        return ds_value + inp['other_num'] + 10


class FallbackFeature(ProcessorBase):
    name = 'fallback_feature'

    def process(self) -> t.Type[Exception]:
        return Exception


class SomeVectorizer(ProcessorBase):
    name = 'some_vectorizer'

    def process(self, feature_value: InputOneOf([SomeFeature, SomeFeatureSecond, FallbackFeature])) -> int:
        return feature_value + 20


class SomeMLModel(ProcessorBase):
    name = 'some_model'

    def process(self, vec_value: Input(SomeVectorizer)) -> float:
        return (vec_value + 30) / 100


async def test_input_one_of_fails_dag(
    build_chart: t.Callable[..., PipelineChartLike],
) -> None:
    chart = build_chart(input_node=SomeInput, output_node=SomeMLModel)
    result = await chart.run(input_kwargs=dict(base_num=10, other_num=5))

    assert isinstance(result.error, TypeError)
    assert result.value is None
