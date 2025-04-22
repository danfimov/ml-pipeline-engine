import typing as t

import pytest_mock

from ml_pipeline_engine.dag_builders.annotation.marks import Input
from ml_pipeline_engine.node import ProcessorBase
from ml_pipeline_engine.types import PipelineChartLike


class ExternalDatasource:
    @staticmethod
    def external_func() -> float:
        return 0.1


class SomeNode(ProcessorBase):
    def process(self):  # noqa
        return ExternalDatasource().external_func()


class InvertNumber(ProcessorBase):
    def process(self, num: float) -> float:
        return -num


class AddConst(ProcessorBase):
    def process(self, num: Input(InvertNumber), const: Input(SomeNode)) -> float:
        return num + const


class DoubleNumber(ProcessorBase):
    def process(self, num: Input(AddConst)) -> float:
        return num * 2


async def test_dag_retry__error(
    build_chart: t.Callable[..., PipelineChartLike],
    mocker: pytest_mock.MockerFixture,
) -> None:
    collect_spy = mocker.spy(SomeNode, 'process')
    external_func_patch = mocker.patch.object(
        ExternalDatasource,
        'external_func',
        side_effect=[
            Exception,
            Exception,
            Exception('CustomError'),
        ],
    )

    chart = build_chart(input_node=InvertNumber, output_node=DoubleNumber)
    result = await chart.run(input_kwargs=dict(num=2.5))

    assert isinstance(result.error, Exception)
    assert result.error.args == ('CustomError',)
    assert result.value is None

    assert external_func_patch.call_count == 3
    assert collect_spy.call_count == 3
