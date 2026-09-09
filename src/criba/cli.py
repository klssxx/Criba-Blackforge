from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .catalog import currents
from .engine import activate, activate_with_llm, build_prompt
from .model_config import ModelSettings, load_model_settings
from .model_runtime import enhance_criba_packet, enhance_ideas_with_model
from .storage import Storage


def _query(args: argparse.Namespace) -> str:
    """Read the activation query from --query or --file."""
    if args.query:
        return str(args.query)
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    raise ValueError("Indica --query o --file.")


def _run(args: argparse.Namespace, prompt: bool = False) -> int:
    query = _query(args)

    # Construir kwargs para LLM si se especifica
    llm_kwargs = {}
    if getattr(args, "llm_model", None):
        llm_kwargs["model"] = args.llm_model
    if getattr(args, "llm_url", None):
        llm_kwargs["url"] = args.llm_url
    if getattr(args, "llm_api_key", None):
        llm_kwargs["api_key"] = args.llm_api_key

    llm_mode = getattr(args, "llm", "none")

    use_configured_model = bool(getattr(args, "use_configured_model", False))
    if use_configured_model and llm_mode != "none":
        raise ValueError("Elige --use-configured-model o --llm, no ambos.")

    # Contexto para interprete-serendipia (P2): api_key + seed
    ctx: dict[str, Any] = {}
    if getattr(args, "llm_api_key", None):
        ctx["zai_api_key"] = args.llm_api_key
    if getattr(args, "seed", None) is not None:
        ctx["seed"] = args.seed

    if use_configured_model:
        packet = activate(query, args.current, args.mode, args.supporting_methods, context=ctx)
        packet = enhance_criba_packet(packet, _configured_model_settings(args))
    elif llm_mode != "none":
        packet = activate_with_llm(query, args.current, args.mode, args.supporting_methods,
                                   llm_mode=llm_mode, llm_kwargs=llm_kwargs, context=ctx)
    else:
        packet = activate(query, args.current, args.mode, args.supporting_methods, context=ctx)

    store = Storage(args.database)
    store.save(query, packet, {
        "current": args.current,
        "mode": args.mode,
        "supporting_methods": args.supporting_methods,
        "llm_mode": llm_mode,
        "use_configured_model": use_configured_model,
    })
    output = build_prompt(packet) if prompt else json.dumps(packet, ensure_ascii=False, indent=2)
    if getattr(args, "output", None):
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


def _configured_model_settings(args: argparse.Namespace) -> ModelSettings:
    """Load GUI-shared profiles and apply a transient CLI reasoning override."""

    settings = load_model_settings()
    settings.enabled = True
    profile = settings.active_profile()
    reasoning = getattr(args, "reasoning", None)
    if profile is not None and reasoning:
        profile.reasoning = reasoning
    return settings


def _inventar_outcome_store(adaptive: bool) -> Any | None:
    """OutcomeStore para G2 solo cuando --adaptive está activo (opt-in)."""
    if not adaptive:
        return None
    from .intelligence.outcome_store import default_store as _outcome_store

    return _outcome_store()


def _inventar_canon_version(adaptive: bool) -> str | None:
    """Canon vigente para aislar el prior por época (§13.4)."""
    if not adaptive:
        return None
    try:
        from .intelligence.registry import TechniqueRegistry

        return TechniqueRegistry().canon_version
    except Exception:  # noqa: BLE001 — sin canon el store aísla por canon_version=None
        return None


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CRIBA command-line interface and return a process exit code."""
    parser = argparse.ArgumentParser(
        prog="criba",
        description="CRIBA Current Engine - 3 modos de innovación:\n"
                   "  1. activate/run: Selección determinista (original)\n"
                   "  2. lottery: Doble lotería (asociativa + pura)\n"
                   "  3. blackforge: Pipeline BLACKFORGE",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--database", default=None, help="Ruta SQLite (por defecto artifacts/criba.sqlite3)")
    sub = parser.add_subparsers(dest="command", required=True)

    def activation(name: str) -> argparse.ArgumentParser:
        command_parser = sub.add_parser(name)
        command_parser.add_argument("--query")
        command_parser.add_argument("--file")
        command_parser.add_argument("--current", default="auto")
        command_parser.add_argument("--mode", default="balanced")
        command_parser.add_argument("--supporting-methods", type=int, default=8)
        command_parser.add_argument("--llm", choices=["none", "offline", "cloud", "nebius"],
                                   default="none", help="Modo LLM: none (determinista), offline (Ollama), cloud (API), nebius (Token Factory)")
        command_parser.add_argument("--llm-model", default=None, help="Nombre del modelo LLM")
        command_parser.add_argument("--llm-url", default=None, help="URL del servidor LLM (Ollama: http://localhost:11434)")
        command_parser.add_argument("--llm-api-key", default=None, help="API key para modo cloud")
        command_parser.add_argument(
            "--use-configured-model",
            action="store_true",
            help="Usa el perfil GGUF/Ollama guardado en la pestaña Modelos IA",
        )
        command_parser.add_argument(
            "--reasoning",
            choices=["fast", "balanced", "deep"],
            default=None,
            help="Sobrescribe temporalmente el reasoning del perfil configurado",
        )
        return command_parser

    activation("activate").add_argument("--json", action="store_true")
    activation("run")
    build_parser = activation("build-prompt")
    build_parser.add_argument("--output")
    sub.add_parser("list-currents")
    explain_parser = sub.add_parser("explain")
    explain_parser.add_argument("--session", required=True)
    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("--session-a", required=True)
    compare_parser.add_argument("--session-b", required=True)
    blackforge_parser = sub.add_parser("blackforge", help="Ejecuta el pipeline BLACKFORGE determinista")
    blackforge_parser.add_argument("--query", help="Consulta que se incluirá en el packet BLACKFORGE")
    blackforge_parser.add_argument("--seed", type=int, default=1)
    blackforge_parser.add_argument("--session-size", type=int, default=12)
    blackforge_parser.add_argument("--profile", default="hybrid")
    blackforge_parser.add_argument("--session-id", default="blackforge-cli")
    blackforge_parser.add_argument(
        "--use-configured-model",
        action="store_true",
        help="Redacta las ideas con el perfil GGUF/Ollama compartido con la GUI",
    )
    blackforge_parser.add_argument(
        "--enhance-semantics",
        action="store_true",
        help="Sintetiza los resultados con el LLM local (resumen + semillas evolutivas)",
    )
    blackforge_parser.add_argument(
        "--reasoning", choices=["fast", "balanced", "deep"], default=None
    )
    # Hybrid pipeline command
    hybrid_parser = sub.add_parser("hybrid", help="Pipeline híbrido completo (ensemble -> cadena -> adversarial + opcional LLM)")
    hybrid_parser.add_argument("--query", required=True, help="Pregunta o problema a analizar")
    hybrid_parser.add_argument(
        "--enhance-semantics",
        action="store_true",
        help="Sintetiza los resultados con el LLM local (resumen + semillas evolutivas)",
    )
    hybrid_parser.add_argument(
        "--reasoning", choices=["fast", "balanced", "deep"], default=None
    )
    # Lottery command
    lottery_parser = sub.add_parser("lottery", help="Ejecuta la Doble Lotería: Asociativa + Pura")
    lottery_parser.add_argument("--query", help="Consulta para modo asociativo")
    lottery_parser.add_argument("--rounds", type=int, default=20, help="Número de rondas")
    lottery_parser.add_argument("--batch-size", type=int, default=20, help="Métodos por ronda")
    lottery_parser.add_argument("--mode", choices=["optimized", "alternating", "associative", "pure", "stratified"],
                               default="alternating", help="Modo de lotería")
    lottery_parser.add_argument("--seed", type=int, default=42, help="Semilla aleatoria")
    lottery_parser.add_argument("--methods-file", default=None,
                               help="Ruta al archivo de métodos JSON")
    lottery_parser.add_argument(
        "--output-dir",
        default=None,
        help="Directorio de resultados (por defecto, datos locales del usuario)",
    )
    lottery_parser.add_argument(
        "--adaptive", action="store_true",
        help="Memoria compartida (G2): pondera el sorteo por prior UCB del OutcomeStore (opt-in; default congelado)",
    )

    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    sub.add_parser("mcp")
    sub.add_parser("gui")
    sub.add_parser("blackforge-gui", help="Lanza la aplicación de escritorio nativa BLACKFORGE")
    inventar_parser = sub.add_parser(
        "inventar",
        help="Loop completo: lotería estratificada -> juez -> prior-art -> ficha",
    )
    inventar_parser.add_argument("query", help="Problema o dominio de invención")
    inventar_parser.add_argument(
        "--seed", type=int, default=None,
        help="Semilla explícita (reproduce la exploración). Sin ella se genera una nueva con secrets.randbits(64).",
    )
    inventar_parser.add_argument("--rounds", type=int, default=2, help="Rondas de lotería")
    inventar_parser.add_argument("--batch-size", type=int, default=8, help="Métodos por ronda")
    inventar_parser.add_argument("--top", type=int, default=3, help="Ideas a evaluar con prior-art")
    inventar_parser.add_argument(
        "--offline", action="store_true", help="Sin red: juez offline y veredictos UNRESOLVED honestos"
    )
    inventar_parser.add_argument(
        "--dossier", action="store_true",
        help="Prepara dossiers con prueba discriminante (estado SUPRA pendiente, nunca PASS)",
    )
    inventar_parser.add_argument(
        "--adaptive", action="store_true",
        help="Memoria compartida (G2): loteria y selector consumen prior UCB del OutcomeStore (opt-in; default congelado)",
    )
    tecnicas_parser = sub.add_parser(
        "tecnicas",
        help="Router del canon T001-T130: subconjunto mínimo relevante (solo lectura)",
    )
    tecnicas_parser.add_argument("query", help="Tarea o problema a rutear")
    tecnicas_parser.add_argument("--perfil", choices=["CRIBA", "BLACKFORGE"], default="CRIBA")
    tecnicas_parser.add_argument("--max", type=int, default=6, help="Máximo de técnicas ejecutables")
    tecnicas_parser.add_argument("--max-por-familia", type=int, default=2)
    tecnicas_parser.add_argument(
        "--con-red", action="store_true",
        help="Permite técnicas que requieren red (por defecto solo offline)",
    )
    tecnicas_parser.add_argument(
        "--adaptive", action="store_true",
        help="Suma prior UCB del OutcomeStore al score (opt-in; default congelado)",
    )
    tecnicas_parser.add_argument(
        "--ejecutar", default=None, metavar="TXXX",
        help="Ejecuta la técnica indicada (debe estar IMPLEMENTED en el canon)",
    )
    tecnicas_parser.add_argument(
        "--problema", default="", help="Problema/entrada para la técnica ejecutada",
    )
    tecnicas_parser.add_argument(
        "--entrada", default=None,
        help="JSON con parámetros canónicos (dimensions/components/...) y/o "
             "documentos de evidencia para técnicas que los requieren",
    )
    tecnicas_parser.add_argument(
        "--desde-almacen", action="store_true",
        help="Alimenta la técnica con evidencia del almacén local (búsqueda por problema)",
    )
    # retro: canal OBSERVED — registra el resultado observado de una técnica o
    # candidato (dossier SUPRA / veredicto humano) SIN LLM. Cierra el circuito
    # de aprendizaje en entornos offline: la memoria se alimenta de la
    # observación real, no solo del juez automático.
    retro_parser = sub.add_parser(
        "retro",
        help="Registra un outcome OBSERVED (dossier/veredicto humano) en el OutcomeStore",
    )
    retro_parser.add_argument(
        "--tecnica", required=True, metavar="TXXX",
        help="Técnica (T001-T130) o método de lotería al que se le observó resultado",
    )
    retro_parser.add_argument(
        "--familia", required=True,
        help="Clase de pensamiento (perspectiva/generacion/ruptura/escape) o familia",
    )
    retro_parser.add_argument(
        "--resultado", required=True,
        choices=["positivo", "negativo", "indeterminado"],
        help="Resultado observado (etiquetado OBSERVED, nunca mezclado con verdict/judge)",
    )
    retro_parser.add_argument("--perfil", choices=["CRIBA", "BLACKFORGE"], default="CRIBA")
    retro_parser.add_argument(
        "--canon", default=None,
        help="canon_version (por defecto el vigente del registry)",
    )
    retro_parser.add_argument("--run-id", default="", help="run_id origen si se conoce")
    args = parser.parse_args(argv)

    try:
        if args.command in {"activate", "run"}:
            return _run(args)
        if args.command == "build-prompt":
            return _run(args, True)
        if args.command == "list-currents":
            print(json.dumps(currents(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "explain":
            print(json.dumps(Storage(args.database).get(args.session), ensure_ascii=False, indent=2))
            return 0
        if args.command == "compare":
            print(json.dumps(Storage(args.database).compare(args.session_a, args.session_b), ensure_ascii=False, indent=2))
            return 0
        if args.command == "blackforge":
            from .blackforge_pipeline import run_headless

            if args.query is None:
                packet = run_headless(
                    seed=args.seed,
                    session_size=args.session_size,
                    profile=args.profile,
                    session_id=args.session_id,
                )
            else:
                packet = run_headless(
                    query=args.query,
                    seed=args.seed,
                    session_size=args.session_size,
                    profile=args.profile,
                    session_id=args.session_id,
                )
            if args.use_configured_model:
                raw_ideas = packet.get("ideas", [])
                if isinstance(raw_ideas, list):
                    enhanced, semantic = enhance_ideas_with_model(
                        str(packet.get("query") or args.query or ""),
                        [idea for idea in raw_ideas if isinstance(idea, dict)],
                        product="BLACKFORGE",
                        settings=_configured_model_settings(args),
                    )
                    packet["ideas"] = enhanced
                    packet["semantic_generation"] = semantic
            print(json.dumps(packet, ensure_ascii=False, indent=2))
            return 0
        if args.command == "serve":
            from .api import serve

            serve(args.host, args.port, args.database)
            return 0
        if args.command == "mcp":
            from .mcp_server import run_stdio

            run_stdio(args.database)
            return 0
        if args.command == "lottery":
            from .lottery import run_lottery

            methods_file = args.methods_file
            if methods_file is not None and not Path(methods_file).is_file():
                print(f"Error: No se encontró el archivo de métodos: {methods_file}", file=sys.stderr)
                return 1

            run_lottery(
                methods_file=methods_file,
                rounds=args.rounds,
                batch_size=args.batch_size,
                mode=args.mode,
                seed=args.seed,
                query=args.query,
                output_dir=args.output_dir,
                adaptive=args.adaptive,
            )
            return 0

        if args.command == "inventar":
            from .inventar import append_ledger, invent, print_sheet, record_outcomes

            from .intelligence.refresh import default_store

            active_store = _inventar_outcome_store(args.adaptive)
            canon = _inventar_canon_version(args.adaptive)
            sheet = invent(
                args.query,
                seed=args.seed,
                rounds=args.rounds,
                batch_size=args.batch_size,
                top=args.top,
                offline=True if args.offline else None,
                store=default_store(),
                adaptive=args.adaptive,
                outcome_store=active_store,
                canon_version=canon,
            )
            if args.dossier:
                from .supra_dossier import guardar_dossier, preparar_dossier

                dossiers = []
                for entry in sheet["entries"]:
                    if entry.get("estado_interpretacion") != "PROPUESTA":
                        continue
                    dossier = preparar_dossier(
                        entry, sheet["query"],
                        ficha_bloqueo=sheet.get("ficha_bloqueo"))
                    path = guardar_dossier(dossier)
                    dossiers.append(dossier["dossier_id"])
                    print(f"Dossier SUPRA pendiente: {dossier['dossier_id']} -> {path}")
                sheet["dossiers"] = dossiers
            print_sheet(sheet)
            ledger = append_ledger(sheet)
            print(f"Ledger: {ledger}")
            # Cierra el circuito G1: lo que el loop produjo vuelve al store
            # como outcomes (verdict prior-art + score juez, etiquetados).
            # Solo con --adaptive (opt-in): la memoria se alimenta del mismo
            # canal que la consume, nunca del modo congelado.
            if active_store is not None:
                written = record_outcomes(
                    sheet, active_store, profile="CRIBA",
                    canon_version=canon or "")
                print(f"Outcomes registrados en el store: {written}")
            return 0

        if args.command == "retro":
            from .intelligence.outcome_store import (
                CHANNEL_OBSERVED,
                default_store as _outcome_store,
            )

            canon = args.canon
            if canon is None:
                try:
                    from .intelligence.registry import TechniqueRegistry

                    canon = TechniqueRegistry().canon_version or ""
                except Exception:  # noqa: BLE001 — sin canon, etiqueta vacía
                    canon = ""
            outcome_store_retro = _outcome_store()
            rec = outcome_store_retro.record(
                profile=args.perfil,
                family=args.familia,
                technique_id=args.tecnica.strip().upper(),
                channel=CHANNEL_OBSERVED,
                outcome=args.resultado,
                canon_version=canon,
                run_id=args.run_id,
            )
            # agregado de familia para el back-off jerárquico (§12.2.1)
            outcome_store_retro.record_family_outcome(
                profile=args.perfil, family=args.familia,
                channel=CHANNEL_OBSERVED, outcome=args.resultado,
                canon_version=canon, run_id=args.run_id,
            )
            print("Outcome OBSERVED registrado:")
            print(json.dumps(rec, ensure_ascii=False, indent=2))
            return 0

        if args.command == "tecnicas":
            from .intelligence.registry import TechniqueRegistry
            from .intelligence.router import TechniqueRouter

            registry = TechniqueRegistry()
            if args.ejecutar:
                import json as _json
                from pathlib import Path as _Path

                from .intelligence.contracts import EvidenceDocument
                from .intelligence.execution import (
                    ExecutionError,
                    document_from_dict,
                    execute_technique,
                    store_documents,
                )

                params: dict[str, Any] = {}
                documents: list[EvidenceDocument] = []
                if args.entrada:
                    entry_path = _Path(args.entrada)
                    if not entry_path.is_file():
                        print(f"Error: no se encontró la entrada: {args.entrada}", file=sys.stderr)
                        return 2
                    payload = _json.loads(entry_path.read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        params = payload.get("params") or {k: v for k, v in payload.items() if k != "documents"}
                        documents = [document_from_dict(d) for d in payload.get("documents", [])]
                    elif isinstance(payload, list):
                        documents = [document_from_dict(d) for d in payload]
                    else:
                        print("Error: la entrada debe ser un objeto o lista JSON", file=sys.stderr)
                        return 2
                if args.desde_almacen:
                    from .intelligence.refresh import default_store

                    store = default_store()
                    if store is None:
                        print("Error: almacén de evidencia no disponible", file=sys.stderr)
                        return 2
                    documents = store_documents(store, args.problema or args.query) + documents
                try:
                    outcome = execute_technique(
                        registry, args.ejecutar, args.problema or args.query,
                        params=params, documents=documents,
                    )
                except (ExecutionError, ValueError, OSError) as exc:
                    print(f"Error: {exc}", file=sys.stderr)
                    return 2
                print(_json.dumps(outcome, ensure_ascii=False, indent=2))
                return 0

            router = TechniqueRouter(registry)
            outcome_store = None
            if args.adaptive:
                from .intelligence.outcome_store import default_store as _outcome_store

                outcome_store = _outcome_store()
            routing = router.select(
                args.query,
                profile=args.perfil,
                max_techniques=args.max,
                max_per_family=args.max_por_familia,
                offline_only=not args.con_red,
                adaptive=args.adaptive,
                outcome_store=outcome_store,
            )
            print(json.dumps(routing.to_dict(), ensure_ascii=False, indent=2))
            return 0

        if args.command == "gui":
            from .gui import run

            result = run(args.database)
            return result if isinstance(result, int) else 0

        if args.command in {"blackforge-gui", "blackforge_gui"}:
            from .blackforge_gui import run as run_blackforge_gui

            result = run_blackforge_gui()
            return result if isinstance(result, int) else 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"Comando desconocido: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
