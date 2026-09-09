"""Runtime execution resolver: canon → operador accesible desde el producto.

Eslabón final de la cadena canónica (§77/§82):

    gen_registry.py → technique_registry.yaml → TechniqueRegistry
    → TechniqueRouter → execution (este módulo) → operador concreto.

El canon decide qué es ejecutable (status); este módulo solo resuelve y
ejecuta lo que el canon autoriza — jamás confiere estado por sí mismo.
Entradas por input_contracts declarados del canon; sin adaptador = error
honrado (no se ejecuta a ciegas).
"""
from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .contracts import EvidenceDocument, EvidenceFragment
from .registry import Technique, TechniqueRegistry


class ExecutionError(ValueError):
    """Error controlado de ejecución (canon no autoriza, entrada inválida...)."""


def expand_implementation(implementation: str) -> list[str]:
    """Referencias del canon → rutas punteadas resolubles.

    Formatos históricos del generador: 'pkg.mod.func', 'pkg.mod.f1/f2'
    (el segmento sin punto hereda el prefijo del anterior) y
    'pkg.{m1,m2}' (módulos con prefijo común).
    """
    refs: list[str] = []
    for part in implementation.split("/"):
        part = part.strip()
        if not part:
            continue
        if "{" in part:
            prefix, rest = part.split("{", 1)
            for piece in rest.rstrip("}").split(","):
                refs.append(prefix + piece.strip())
        elif "." not in part and refs:
            refs.append(refs[-1].rsplit(".", 1)[0] + "." + part)
        else:
            refs.append(part)
    return refs


def resolve_callable(dotted: str) -> Callable[..., Any]:
    """'pkg.mod.func' → objeto vivo. Falla con ExecutionError si está roto."""
    parts = dotted.split(".")
    for i in range(len(parts) - 1, 0, -1):
        try:
            module = importlib.import_module(".".join(parts[:i]))
        except ModuleNotFoundError:
            continue
        obj: Any = module
        for segment in parts[i:]:
            obj = getattr(obj, segment, None)
            if obj is None:
                break
        if callable(obj):
            resolved: Callable[..., Any] = obj
            return resolved
    raise ExecutionError(f"referencia no ejecutable: {dotted}")


def document_from_dict(raw: Mapping[str, Any]) -> EvidenceDocument:
    """Adaptador almacén/JSON → EvidenceDocument (campos conocidos only)."""
    fragments: list[EvidenceFragment] = [
        EvidenceFragment(**f) if isinstance(f, Mapping) else EvidenceFragment(text=str(f))
        for f in raw.get("fragments") or []
    ]
    return EvidenceDocument(
        doc_id=str(raw.get("doc_id", "")),
        source_id=str(raw.get("source_id", "")),
        title=str(raw.get("title", "")),
        kind=str(raw.get("kind", "document")),
        published=str(raw.get("published", "")),
        url=str(raw.get("url", "")),
        language=str(raw.get("language", "en")),
        abstract=str(raw.get("abstract", "")),
        fragments=fragments,
        metadata=dict(raw.get("metadata") or {}),
    )


# Adaptadores de entrada por técnica: el contrato canónico (input_contracts)
# decide la forma de la llamada. Cada adaptador recibe (problema, params del
# usuario, documentos) y produce (args, kwargs) para el operador principal.
# params claves canónicas: dimensions/components/component_functions/
# premise_implications/constraint_inversions/known_combinations/temporal_map.
InputAdapter = Callable[[str, Mapping[str, Any], list[EvidenceDocument]], tuple[tuple[Any, ...], dict[str, Any]]]


def _problem_only(keys: tuple[str, ...] = ()) -> InputAdapter:
    def adapter(problem: str, params: Mapping[str, Any], _docs: list[EvidenceDocument]):
        missing = [k for k in keys if k not in params]
        if missing:
            raise ExecutionError(f"faltan parámetros canónicos: {', '.join(missing)}")
        return (problem, *(params[k] for k in keys)), {}
    return adapter


def _evidence_first(param: str = "concepts") -> InputAdapter:
    def adapter(problem: str, params: Mapping[str, Any], docs: list[EvidenceDocument]):
        return (docs,), {}
    return adapter


def _topic_observations(params: Mapping[str, Any]) -> list[Any]:
    """params['observations'] (dicts) → TopicObservation ordenables por periodo."""
    from .contracts import TopicObservation

    out = []
    for raw in params.get("observations") or []:
        if isinstance(raw, TopicObservation):
            out.append(raw)
        elif isinstance(raw, Mapping):
            out.append(TopicObservation(
                topic=str(raw.get("topic", "")),
                period=str(raw.get("period", "")),
                frequency=int(raw.get("frequency") or 0),
                source_diversity=int(raw.get("source_diversity") or 0),
                metadata=dict(raw.get("metadata") or {}),
            ))
    return out


def _dynamics_method(method: str) -> InputAdapter:
    def adapter(problem: str, params: Mapping[str, Any], _docs: list[EvidenceDocument]):
        from .signals.dynamics import TopicDynamics

        topic = str(params.get("topic", ""))
        if not topic:
            raise ExecutionError("falta el parámetro canónico: topic")
        # el resolver devuelve el método NO ligado: se le pasa la instancia
        return (TopicDynamics(_topic_observations(params)), topic), {}
    return adapter


def _detector_call(class_path: str) -> InputAdapter:
    """Detectores: el resolver devuelve el método no ligado → (instancia, serie)."""
    def adapter(problem: str, params: Mapping[str, Any], _docs: list[EvidenceDocument]):
        from importlib import import_module

        module_name, class_name = class_path.rsplit(".", 1)
        detector = getattr(import_module(module_name), class_name)()
        return (detector, _topic_observations(params)), {"topic": params.get("topic")}
    return adapter


def _weak_signal_instance() -> Any:
    from .signals.weak_signals import WeakSignalAggregator

    return WeakSignalAggregator()


def _lead_lag_instance() -> Any:
    from .signals.lead_lag import LeadLagAnalyzer

    return LeadLagAnalyzer()


def _graph_call(class_path: str, *, required: tuple[str, ...] = (),
                optional: dict[str, Any] | None = None) -> InputAdapter:
    """Operadores de grafo: instancia sobre IntelligenceStore (db_path opcional)."""
    def adapter(problem: str, params: Mapping[str, Any], _docs: list[EvidenceDocument]):
        import os
        from importlib import import_module
        from pathlib import Path as _Path

        module_name, class_name = class_path.rsplit(".", 1)
        db_path = params.get("db_path") or (
            _Path(os.environ.get("LOCALAPPDATA") or __import__("pathlib").Path.home())
            / "CRIBA-Blackforge" / "intelligence.sqlite3"
        )
        from .graph.store import SQLiteKnowledgeGraphStore

        graph_store = SQLiteKnowledgeGraphStore(str(db_path))
        operator = getattr(import_module(module_name), class_name)(graph_store)
        missing = [k for k in required if k not in params]
        if missing:
            raise ExecutionError(f"faltan parámetros canónicos: {', '.join(missing)}")
        args: list[Any] = [params[k] for k in required]
        kwargs = {k: params[k] for k in (optional or {})
                  if k in params and k not in required}
        if "entity_ids" in params:
            kwargs["entity_ids"] = params["entity_ids"]
        args = [operator] + list(args)
        return (tuple(args), kwargs)
    return adapter




_INPUT_ADAPTERS: dict[str, tuple[str, InputAdapter]] = {
    "T053": ("criba.intelligence.invention.rare_combinations.detect_rare_combinations",
             _evidence_first()),
    "T055": ("criba.intelligence.invention.cross_domain.detect_cross_domain_analogies",
             _evidence_first()),
    "T057": ("criba.intelligence.invention.triz.list_principles",
             lambda problem, params, docs: ((), {})),
    "T059": ("criba.intelligence.invention.morphology.generate_morphological_hypotheses",
             _problem_only(("dimensions",))),
    "T060": ("criba.intelligence.invention.scamper.generate_scamper_hypotheses",
             _problem_only(("components",))),
    "T062": ("criba.intelligence.invention.functions.decompose_functional_hypotheses",
             _problem_only(("component_functions",))),
    "T063": ("criba.intelligence.invention.functions.search_function_to_mechanism_hypotheses",
             lambda problem, params, docs: ((problem, list(params.get("functions", [])), docs), {})),
    "T064": ("criba.intelligence.invention.first_principles.decompose_first_principles_hypotheses",
             _problem_only(("premise_implications",))),
    "T065": ("criba.intelligence.invention.inversion.generate_constraint_inversion_hypotheses",
             _problem_only(("constraint_inversions",))),
    "T116": ("criba.intelligence.invention.adjacent_possible.generate_adjacent_possible_hypotheses",
             lambda problem, params, docs: (
                 (problem, list(params.get("capabilities", []))),
                 {"known_combinations": [list(k) for k in params.get("known_combinations", [])]},
             )),
    "T129": ("composite:t129",
             lambda problem, params, docs: ((problem or "",), dict(params))),
    # -- slice 2: gaps (evidencia primero) --------------------------------
    "T067": ("criba.intelligence.gaps.contradictions.analyze_contradictions",
             lambda problem, params, docs: (
                 (_claims_from(docs), docs), {})),
    "T068": ("criba.intelligence.gaps.research.extract_research_gaps",
             lambda problem, params, docs: ((docs,), {"topic": str(params.get("topic", ""))})),
    "T069": ("criba.intelligence.gaps.limitations.extract_limitations",
             lambda problem, params, docs: ((docs,), {"scope": str(params.get("scope", ""))})),
    "T070": ("criba.intelligence.gaps.failures.extract_failures",
             lambda problem, params, docs: ((docs,), {"topic": str(params.get("topic", ""))})),
    "T071": ("criba.intelligence.gaps.resurrection.extract_resurrection_candidates",
             lambda problem, params, docs: ((docs,), {"topic": str(params.get("topic", ""))})),
    "T086": ("criba.intelligence.gaps.white_space.analyze_white_spaces",
             lambda problem, params, docs: (
                 (docs,), {"space_type": str(params.get("space_type", "")),
                           "topic": str(params.get("topic", ""))})),
    "T128": ("composite:t128",
             lambda problem, params, docs: ((docs,), dict(params))),
    # -- slice 2: signals (series/params) ----------------------------------
    "T019": ("criba.intelligence.signals.dynamics.TopicDynamics.acceleration",
             _dynamics_method("acceleration")),
    "T048": ("criba.intelligence.signals.dynamics.TopicDynamics.velocity",
             _dynamics_method("velocity")),
    "T049": ("criba.intelligence.signals.dynamics.TopicDynamics.acceleration",
             _dynamics_method("acceleration")),
    "T096": ("criba.intelligence.signals.bursts.BurstDetector.detect",
             _detector_call("criba.intelligence.signals.bursts.BurstDetector")),
    "T097": ("criba.intelligence.signals.changepoints.ChangePointDetector.detect",
             _detector_call("criba.intelligence.signals.changepoints.ChangePointDetector")),
    "T098": ("criba.intelligence.signals.anomaly.AnomalyDetector.detect",
             _detector_call("criba.intelligence.signals.anomaly.AnomalyDetector")),
    "T099": ("criba.intelligence.signals.weak_signals.WeakSignalAggregator.aggregate",
             lambda problem, params, docs: (
                 (_weak_signal_instance(), _weak_signals(params)), {})),
    "T101": ("criba.intelligence.signals.lead_lag.LeadLagAnalyzer.analyze",
             lambda problem, params, docs: (
                 (_lead_lag_instance(), _topic_observations(params)),
                 {"leader_topic": str(params.get("leader_topic", "")),
                  "follower_topic": str(params.get("follower_topic", ""))})),
    # -- slice 3: graph (sobre IntelligenceStore, no store paralelo) -------
    "T091": ("criba.intelligence.graph.link_prediction.LinkPredictionInterface.predict",
             _graph_call("criba.intelligence.graph.link_prediction.LinkPredictionInterface",
                         required=("source",), optional={"limit": 10})),
    "T094": ("criba.intelligence.graph.communities.CommunityDetector.detect",
             _graph_call("criba.intelligence.graph.communities.CommunityDetector")),
    "T095": ("criba.intelligence.graph.bridges.BridgeNodeAnalyzer.articulation_points",
             _graph_call("criba.intelligence.graph.bridges.BridgeNodeAnalyzer")),
}





def _claims_from(docs: list[EvidenceDocument]) -> list[Any]:
    from .claims import extract_claims_from_fragments

    claims = []
    for doc in docs:
        claims.extend(extract_claims_from_fragments(doc))
    return claims


def _weak_signals(params: Mapping[str, Any]) -> list[Any]:
    from .contracts import WeakSignal

    out = []
    for raw in params.get("signals") or []:
        if isinstance(raw, WeakSignal):
            out.append(raw)
        elif isinstance(raw, Mapping):
            out.append(WeakSignal(**dict(raw)))
    return out


_COMPOSITE_T128: tuple[tuple[str, str, str], ...] = (
    # (módulo, función, kwarg propio) — cada operador recibe SOLO su contrato
    ("criba.intelligence.gaps.patent_expiration", "analyze_patent_expirations", "*"),
    ("criba.intelligence.gaps.dormant", "detect_dormant_papers", "*"),
    ("criba.intelligence.gaps.sleeping_beauty", "detect_sleeping_beauties", "*"),
    ("criba.intelligence.gaps.resurrection", "extract_resurrection_candidates", "*"),
)

_COMPOSITE_T129: tuple[tuple[str, str, str], ...] = (
    ("criba.intelligence.invention.counterfactual", "generate_counterfactual_hypotheses", "scenario_outcomes"),
    ("criba.intelligence.invention.future_back", "generate_future_back_hypotheses", "future_steps"),
    ("criba.intelligence.invention.bottlenecks", "generate_bottleneck_mapping_hypotheses", "bottleneck_probes"),
    ("criba.intelligence.invention.nth_order", "generate_nth_order_effect_hypotheses", "intervention_chains"),
)


def _run_composite(ref: str, args: tuple, kwargs: dict[str, Any]) -> list[Any]:
    """T128: ejecuta los 4 operadores canon-declarados y etiqueta procedencia.

    Cada operador recibe solo los kwargs de su contrato (el compuesto no
    colapsa contratos); no añade lógica de técnica.
    """
    table = {"composite:t128": _COMPOSITE_T128, "composite:t129": _COMPOSITE_T129}
    if ref not in table:
        raise ExecutionError(f"compuesto desconocido: {ref}")
    merged: list[Any] = []
    for module_name, func_name, own_kwarg in table[ref]:
        func = getattr(importlib.import_module(module_name), func_name)
        if own_kwarg == "*":
            # estilo T128: documentos + solo kwargs que la firma acepta
            documents = args[0] if args else []
            accepted = set(inspect.signature(func).parameters) - {"documents"}
            op_kwargs = {k: v for k, v in kwargs.items() if k in accepted}
            results = func(documents, **op_kwargs) if op_kwargs else func(documents)
        else:
            # estilo T129: (problema, mapeo propio del contrato del módulo)
            problem = args[0] if args else ""
            mapping = kwargs.get(own_kwarg) or {}
            results = func(problem, mapping)
        for item in results:
            if hasattr(item, "to_dict"):
                item = {**item.to_dict(), "composite_module": module_name.rsplit(".", 1)[-1]}
            merged.append(item)
    return merged


def execute_technique(
    registry: TechniqueRegistry,
    technique_id: str,
    problem: str,
    *,
    params: Mapping[str, Any] | None = None,
    documents: Sequence[EvidenceDocument] | None = None,
) -> dict[str, Any]:
    """Ejecuta una técnica canónica autorizada y devuelve salida trazable.

    Guardrails de canon: PLANNED/DISABLED → error (el canon no autoriza);
    requires_credentials → error; sin adaptador de entrada → error honrado.
    """
    try:
        technique = registry.get(technique_id)
    except KeyError as exc:
        raise ExecutionError(f"técnica desconocida: {technique_id}") from exc
    if not technique.status.startswith("IMPLEMENTED"):
        raise ExecutionError(
            f"{technique_id} no es ejecutable: estado canónico {technique.status} "
            "(el canon, no la disponibilidad de código, decide)"
        )
    if technique.requires_credentials:
        raise ExecutionError(f"{technique_id} requiere credenciales: no ejecutable")
    adapter = _INPUT_ADAPTERS.get(technique_id)
    if adapter is None:
        raise ExecutionError(
            f"{technique_id}: sin adaptador de entrada para sus input_contracts; "
            "usar la API Python del operador"
        )
    operator_ref, adapt = adapter
    args, kwargs = adapt(problem or "", params or {}, list(documents or []))
    if operator_ref.startswith("composite:"):
        output = _run_composite(operator_ref, args, kwargs)
    else:
        output = resolve_callable(operator_ref)(*args, **kwargs)
    # salida contractual: lista de items o escalar (p. ej. LeadLagResult)
    items_raw = list(output) if isinstance(output, (list, tuple)) else [output]
    items = [item.to_dict() if hasattr(item, "to_dict") else item for item in items_raw]
    return {
        "technique": technique_id,
        "name": technique.name,
        "canon_version": registry.canon_version,
        "problem": problem,
        "operator": operator_ref,
        "evidence_doc_ids": [d.doc_id for d in documents or []],
        "results": items,
    }


def store_documents(
    store: Any,
    query: str,
    limit: int = 20,
) -> list[EvidenceDocument]:
    """Evidencia local del almacén → EvidenceDocument para operadores."""
    raw_docs = store.search_documents(query, limit=limit) or []
    docs: list[EvidenceDocument] = []
    for raw in raw_docs:
        if isinstance(raw, EvidenceDocument):
            docs.append(raw)
        elif isinstance(raw, Mapping):
            docs.append(document_from_dict(raw))
    return docs
