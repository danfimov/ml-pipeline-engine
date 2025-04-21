import abc
import typing as t
from dataclasses import dataclass
from uuid import UUID

import networkx as nx

NodeResultT = t.TypeVar('NodeResultT')
NodeResultT_co = t.TypeVar('NodeResultT_co', covariant=True)

AdditionalDataT = t.TypeVar('AdditionalDataT', bound=t.Any)

DigraphT = t.TypeVar('DigraphT', bound=nx.DiGraph)

PipelineId = t.Union[UUID, str]

NodeId: t.TypeAlias = str
ModelName: t.TypeAlias = str
CaseLabel: t.TypeAlias = str
SerializationNodeKind: t.TypeAlias = str
NodeTag: t.TypeAlias = str


class RetryProtocol(t.Protocol[NodeResultT_co]):
    """
    Протокол, описывающий свойства повторного исполнения ноды.
    Предоставляет возможность использовать дефолтное значение в случае ошибки.
    """

    attempts: t.ClassVar[int | None] = None
    delay: t.ClassVar[float | None] = None
    exceptions: t.ClassVar[tuple[t.Type[BaseException], ...] | None] = None
    use_default: t.ClassVar[bool] = False

    def get_default(self, **kwargs: t.Any) -> NodeResultT_co:
        ...


class TagProtocol(t.Protocol):
    """
    Протокол, который позволяет декларировать параметры запуска узла
    """

    tags: t.ClassVar[tuple[NodeTag, ...]] = ()


@dataclass
class Recurrent(t.Generic[AdditionalDataT]):
    data: AdditionalDataT | None


class RecurrentProtocol(t.Protocol):
    """
    Протокол, определяющий поведение узла при повторном исполнении подграфа
    """

    @abc.abstractmethod
    def next_iteration(self, data: AdditionalDataT | None) -> Recurrent:
        """
        Метод для инициализации повторного исполнения подграфа
        """


class NodeBase(RetryProtocol, TagProtocol, t.Protocol[NodeResultT]):
    """
    Basic node interface
    """
    node_type: t.ClassVar[str | None] = None
    name: t.ClassVar[str | None] = None
    verbose_name: t.ClassVar[str | None] = None

    process: t.Callable[..., NodeResultT] | t.Callable[..., t.Awaitable[NodeResultT]]


@dataclass(frozen=True)
class PipelineResult(t.Generic[NodeResultT]):
    """
    Контейнер результата выполнения пайплайна.
    """

    pipeline_id: PipelineId
    value: NodeResultT
    error: Exception | None

    def raise_on_error(self) -> None:
        if self.error is not None:
            raise self.error


@dataclass(frozen=True)
class CaseResult:
    """
    Результат оператора switch-case
    """

    label: CaseLabel
    node_id: NodeId


class PipelineChartLike(t.Protocol[NodeResultT, DigraphT]):
    """
    Определение пайплайна ML-модели

    Этот объект можно хранить в глобальной области. Он является иммутабельным.
    """

    model_name: ModelName
    entrypoint: 'DAGLike[NodeResultT, DigraphT] | None'
    event_managers: list[t.Type['EventManagerLike']]
    artifact_store: t.Type['ArtifactStoreLike'] | None

    async def run(
        self,
        pipeline_id: PipelineId | None = None,
        input_kwargs: dict[str, t.Any] | None = None,
        meta: dict[str, t.Any] | None = None,
    ) -> PipelineResult[NodeResultT]:
        ...


class PipelineContextLike(t.Protocol):
    """
    Контекст выполнения пайплайна

    Создается при запуске пайплайна из чарта пайплайна и хранит состояние выполнения пайплайна, является источником
    событий жизненного цикла пайплайна.
    """

    chart: PipelineChartLike
    pipeline_id: PipelineId
    input_kwargs: dict[str, t.Any]
    meta: dict[str, t.Any]
    artifact_store: 'ArtifactStoreLike'

    async def emit_on_node_start(self, node_id: NodeId) -> t.Any:
        ...

    async def emit_on_node_complete(self, node_id: NodeId, error: BaseException | None) -> t.Any:
        ...

    async def emit_on_pipeline_start(self) -> t.Any:
        ...

    async def emit_on_pipeline_complete(self, result: PipelineResult) -> t.Any:
        ...

    # TODO: Remove it in the future!
    async def save_node_result(self, node_id: NodeId, data: t.Any) -> None:
        ...

    @property
    def model_name(self) -> ModelName:
        ...

    def _get_event_managers(self) -> list['EventManagerLike']:
        ...


class EventManagerLike(t.Protocol):
    """
    Менеджер событий жизненного цикла пайплайна
    """

    async def on_pipeline_start(self, ctx: PipelineContextLike) -> None:
        ...

    async def on_pipeline_complete(self, ctx: PipelineContextLike, result: PipelineResult) -> None:
        ...

    async def on_node_start(self, ctx: PipelineContextLike, node_id: NodeId) -> None:
        ...

    async def on_node_complete(self, ctx: PipelineContextLike, node_id: NodeId, error: Exception | None) -> None:
        ...


class ArtifactStoreLike(t.Protocol[NodeResultT_co]):
    """
    Хранилище артефактов - результатов расчета узлов
    """

    def __init__(self, ctx: PipelineContextLike, *args: t.Any, **kwargs: t.Any) -> None:
        ...

    async def save(self, node_id: NodeId, data: t.Any) -> None:
        ...

    async def load(self, node_id: NodeId) -> NodeResultT_co:
        ...


class RetryPolicyLike(t.Protocol):
    node: t.Type[NodeBase]

    @property
    @abc.abstractmethod
    def delay(self) -> float:
        ...

    @property
    @abc.abstractmethod
    def attempts(self) -> int:
        ...

    @property
    @abc.abstractmethod
    def exceptions(self) -> tuple[t.Type[BaseException], ...]:
        ...


class DAGRunManagerLike(t.Protocol[NodeResultT_co]):
    """
    Менеджер управлением запуска графа
    """

    ctx: PipelineContextLike
    dag: 'DAGLike'

    @abc.abstractmethod
    async def run(self) -> NodeResultT_co:
        ...


class DAGLike(t.Protocol[NodeResultT_co, DigraphT]):
    """
    Граф
    """

    graph: DigraphT
    input_node: NodeId
    output_node: NodeId
    node_map: dict[NodeId, t.Type[NodeBase]]
    run_manager: t.Type[DAGRunManagerLike]
    retry_policy: t.Type[RetryPolicyLike]
    is_process_pool_needed: bool
    is_thread_pool_needed: bool

    @abc.abstractmethod
    async def run(self, ctx: PipelineContextLike) -> NodeResultT_co:
        ...

    def visualize(self, *args: t.Any, **kwargs: t.Any) -> None:
        ...
