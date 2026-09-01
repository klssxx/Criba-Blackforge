from __future__ import annotations

import json

from criba import model_runtime
from criba.model_config import ModelProfile, ModelSettings
from criba.model_runtime import (
    MAX_SEMANTIC_CANDIDATES,
    SEMANTIC_BATCH_SIZE,
    ModelRuntimeError,
    build_semantic_prompt,
    enhance_ideas_with_model,
    ensure_profile_available,
)


def _settings(reasoning: str = "balanced") -> ModelSettings:
    profile = ModelProfile(name="Test GGUF", reasoning=reasoning)  # type: ignore[arg-type]
    return ModelSettings(
        enabled=True,
        active_profile_id=profile.id,
        profiles=[profile],
    )


def _ideas() -> list[dict[str, object]]:
    return [
        {
            "id": "I01",
            "title": "Método A x Método B",
            "description": "Combinar familia_a + familia_b",
            "method1": "Prueba progresiva",
            "method2": "Control de fraude",
            "convergence": {"value_score": 0.82, "novelty": 0.75},
        },
        {
            "id": "I02",
            "title": "Método C x Método D",
            "description": "Combinar familia_c + familia_d",
            "method1": "Segmentación",
            "method2": "Reversibilidad",
            "convergence": {"value_score": 0.71, "novelty": 0.67},
        },
    ]


def _response(suffix: str = "") -> str:
    return json.dumps(
        {
            "ideas": [
                {
                    "candidate_id": "I01",
                    "title": f"Autenticación adaptativa por riesgo{suffix}",
                    "description": "Eleva la verificación solo cuando la señal de fraude supera un umbral.",
                    "mechanism": "Segmenta sesiones por riesgo y conserva el flujo simple para casos normales.",
                    "experiment": "Prueba con un 5 % del tráfico y mide fraude y abandono durante una semana.",
                },
                {
                    "candidate_id": "I02",
                    "title": f"Revisión reversible de operaciones dudosas{suffix}",
                    "description": "Retiene temporalmente operaciones anómalas sin bloquear clientes legítimos.",
                    "mechanism": "Usa una cola reversible con evidencia y límites de tiempo explícitos.",
                    "experiment": "Simula cien operaciones y compara falsos positivos con la regla actual.",
                },
            ]
        },
        ensure_ascii=False,
    )


def _healthy_runtime(*args, **kwargs) -> dict[str, object]:
    return {"data": [{"id": "criba-local"}]}


def test_prompt_binds_problem_and_candidate_ids() -> None:
    prompt, ids = build_semantic_prompt(
        "Reducir fraude sin empeorar la experiencia",
        _ideas(),
        product="CRIBA",
        reasoning="balanced",
    )
    decoded = json.loads(prompt)
    assert decoded["problem"] == "Reducir fraude sin empeorar la experiencia"
    assert ids == ["I01", "I02"]
    assert [row["candidate_id"] for row in decoded["candidates"]] == ids
    assert "solo JSON" in " ".join(decoded["quality_rules"])


def test_prompt_batch_is_bounded_for_small_local_models() -> None:
    templates = _ideas()
    source = [dict(templates[index % len(templates)]) for index in range(16)]
    for index, idea in enumerate(source):
        idea["id"] = f"I{index:02d}"

    prompt, ids = build_semantic_prompt(
        "Reducir fraude", source, product="CRIBA", reasoning="fast"
    )

    assert len(ids) == SEMANTIC_BATCH_SIZE
    assert len(json.loads(prompt)["candidates"]) == SEMANTIC_BATCH_SIZE


def test_overlong_model_text_is_normalized_before_strict_validation() -> None:
    response = json.dumps(
        {
            "ideas": [
                {
                    "candidate_id": "I01",
                    "title": "Título " * 40,
                    "description": "Descripción concreta y válida para la propuesta.",
                    "mechanism": "Mecanismo causal concreto y verificable.",
                    "experiment": "Compara un piloto reversible con la referencia.",
                }
            ]
        }
    )

    batch = model_runtime._validated_semantic_response(response, ["I01"])

    assert len(batch.ideas[0].title) == 120
    assert batch.ideas[0].candidate_id == "I01"


def test_bare_json_array_from_llama_is_accepted_and_validated() -> None:
    response = json.dumps(json.loads(_response())["ideas"])

    batch = model_runtime._validated_semantic_response(response, ["I01", "I02"])

    assert [idea.candidate_id for idea in batch.ideas] == ["I01", "I02"]


def test_semantic_layer_rewrites_language_but_preserves_scores(monkeypatch) -> None:
    monkeypatch.setattr(model_runtime, "_runtime_status", _healthy_runtime)
    monkeypatch.setattr(
        model_runtime,
        "_generate_once",
        lambda profile, system, prompt: _response(),
    )
    original = _ideas()

    enhanced, metadata = enhance_ideas_with_model(
        "Reducir fraude sin empeorar la experiencia",
        original,
        product="CRIBA",
        settings=_settings(),
    )

    assert metadata["status"] == "ok"
    assert metadata["enhanced_count"] == 2
    assert enhanced[0]["title"] == "Autenticación adaptativa por riesgo"
    assert enhanced[0]["semantic_source"] == "local_model"
    assert enhanced[0]["convergence"] == original[0]["convergence"]
    assert original[0]["title"] == "Método A x Método B"


def test_deep_reasoning_runs_revision_and_keeps_valid_revision(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(model_runtime, "_runtime_status", _healthy_runtime)

    def generate(profile, system, prompt):
        calls.append(prompt)
        return _response(" revisada" if len(calls) == 2 else "")

    monkeypatch.setattr(model_runtime, "_generate_once", generate)
    enhanced, metadata = enhance_ideas_with_model(
        "Reducir fraude",
        _ideas(),
        product="CRIBA",
        settings=_settings("deep"),
    )

    assert len(calls) == 2
    assert metadata["reasoning"] == "deep"
    assert enhanced[0]["title"].endswith("revisada")


def test_unavailable_model_returns_explicit_deterministic_fallback(monkeypatch) -> None:
    def unavailable(profile, *, start=True):
        raise ModelRuntimeError("runtime ausente")

    monkeypatch.setattr(model_runtime, "ensure_profile_available", unavailable)
    original = _ideas()
    enhanced, metadata = enhance_ideas_with_model(
        "Reducir fraude",
        original,
        product="BLACKFORGE",
        settings=_settings(),
    )

    assert metadata["status"] == "fallback"
    assert "runtime ausente" in metadata["error"]
    assert enhanced == original


def test_semantic_layer_bounds_large_criba_batches_and_preserves_remainder(
    monkeypatch,
) -> None:
    ideas = [
        {
            "id": f"I{index:03d}",
            "title": f"Mecánica {index}",
            "description": "Descripción determinista extensa",
            "convergence": {"value_score": 1.0 - index / 1000},
        }
        for index in range(75)
    ]
    monkeypatch.setattr(model_runtime, "_runtime_status", _healthy_runtime)

    def generate(profile, system, prompt):
        del profile, system
        candidates = json.loads(prompt)["candidates"]
        return json.dumps(
            {
                "ideas": [
                    {
                        "candidate_id": item["candidate_id"],
                        "title": f"Idea coherente {item['candidate_id']}",
                        "description": "Explica una acción concreta para resolver el problema indicado.",
                        "mechanism": "Conecta una intervención acotada con un resultado observable.",
                        "experiment": "Ejecuta un piloto reversible y compara el resultado con la base.",
                    }
                    for item in candidates
                ]
            }
        )

    monkeypatch.setattr(model_runtime, "_generate_once", generate)
    enhanced, metadata = enhance_ideas_with_model(
        "Reducir fraude sin perjudicar a clientes legítimos",
        ideas,
        product="CRIBA",
        settings=_settings(),
    )

    assert metadata["requested_count"] == MAX_SEMANTIC_CANDIDATES
    assert metadata["enhanced_count"] == MAX_SEMANTIC_CANDIDATES
    assert metadata["candidate_count"] == 75
    assert enhanced[MAX_SEMANTIC_CANDIDATES - 1]["semantic_source"] == "local_model"
    assert "semantic_source" not in enhanced[MAX_SEMANTIC_CANDIDATES]
    assert [idea["convergence"] for idea in enhanced] == [
        idea["convergence"] for idea in ideas
    ]


def test_incomplete_valid_response_is_marked_as_explicit_partial(monkeypatch) -> None:
    ideas = [
        {
            "id": f"I{index:02d}",
            "title": "Mecánica",
            "description": "Descripción determinista",
        }
        for index in range(8)
    ]
    monkeypatch.setattr(model_runtime, "_runtime_status", _healthy_runtime)

    def generate(profile, system, prompt):
        del profile, system
        candidates = json.loads(prompt)["candidates"][: len(ideas) // 2]
        return json.dumps(
            {
                "ideas": [
                    {
                        "candidate_id": item["candidate_id"],
                        "title": f"Idea {item['candidate_id']}",
                        "description": "Una descripción concreta vinculada al problema indicado.",
                        "mechanism": "Una intervención específica modifica una señal observable.",
                        "experiment": "Compara un piloto reversible con el proceso de referencia.",
                    }
                    for item in candidates
                ]
            }
        )

    monkeypatch.setattr(model_runtime, "_generate_once", generate)
    enhanced, metadata = enhance_ideas_with_model(
        "Reducir fraude", ideas, product="CRIBA", settings=_settings()
    )

    assert metadata["status"] == "partial"
    assert metadata["enhanced_count"] == len(ideas) // 2
    assert metadata["deterministic_remainder"] == len(ideas) // 2
    assert enhanced[0]["semantic_source"] == "local_model"
    assert "semantic_source" not in enhanced[-1]


def test_runtime_rejects_non_loopback_endpoint() -> None:
    profile = ModelProfile(endpoint="https://example.com:8080")

    try:
        ensure_profile_available(profile, start=False)
    except ModelRuntimeError as exc:
        assert "endpoint HTTP local" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("A remote endpoint must be rejected")


def test_runtime_rejects_a_different_loaded_model(monkeypatch) -> None:
    monkeypatch.setattr(
        model_runtime,
        "_runtime_status",
        lambda *args, **kwargs: {"data": [{"id": "otro-modelo"}]},
    )

    try:
        ensure_profile_available(ModelProfile(), start=False)
    except ModelRuntimeError as exc:
        assert "no tiene cargado 'criba-local'" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("A mismatched model alias must be rejected")


def test_llama_request_uses_schema_and_fast_reasoning_controls(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def http(url, *, payload=None, timeout=8.0):
        seen["url"] = url
        seen["payload"] = payload
        seen["timeout"] = timeout
        return {"choices": [{"message": {"content": _response()}}]}

    monkeypatch.setattr(model_runtime, "_http_json", http)
    profile = ModelProfile(reasoning="fast")
    result = model_runtime._generate_once(profile, "system", "prompt")
    payload = seen["payload"]

    assert result == _response()
    assert seen["url"] == "http://127.0.0.1:8080/v1/chat/completions"
    assert seen["timeout"] == 300.0
    assert isinstance(payload, dict)
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert payload["reasoning_effort"] == "none"


def test_ollama_retries_without_think_for_non_thinking_model(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []

    def http(url, *, payload=None, timeout=8.0):
        del url, timeout
        assert isinstance(payload, dict)
        payloads.append(dict(payload))
        if len(payloads) == 1:
            raise ModelRuntimeError("HTTP 400: model does not support think")
        return {"message": {"content": _response()}}

    monkeypatch.setattr(model_runtime, "_http_json", http)
    profile = ModelProfile(
        backend="ollama",
        endpoint="http://127.0.0.1:11434",
        reasoning="balanced",
    )

    assert model_runtime._generate_once(profile, "system", "prompt") == _response()
    assert payloads[0]["think"] == "medium"
    assert "think" not in payloads[1]
