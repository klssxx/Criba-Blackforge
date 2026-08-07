"""Máquina de estados visual (STATE_MATRIX_CRIBA.md S1..S10) + acciones.

Todas las mutaciones (generar/evaluar/actualizar) corren en QThreadPool;
la GUI nunca se congela (WIDGET_TREE §3).
"""

from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtGui import QColor

from .. import __version__ as ENGINE_VERSION
from ..engine import activate
from .ranking import RankingModel
from .widgets import set_chip

MUTATORS = ("navNuevaIdea", "navGenerar", "navEvaluar", "navGuardar", "navActualizar")


class _Signals(QObject):
    done = Signal(object)
    fail = Signal(str)


class Worker(QRunnable):
    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self.fn = fn
        self.signals = _Signals()

    def run(self) -> None:
        try:
            self.signals.done.emit(self.fn())
        except Exception as exc:  # noqa: BLE001 — S9 muestra el motivo real
            self.signals.fail.emit(f"{exc}\n{traceback.format_exc(limit=3)}")


def _now_ts() -> str:
    return datetime.now().strftime("%H:%M")


def _start_worker(win: Any, worker: "Worker") -> None:
    """Retener la referencia del worker hasta que emita: sin esto el GC de
    Python destruye el QObject de señales antes de entregar done/fail
    (pitfall QRunnable.autoDelete + señal encolada entre hilos)."""
    if not hasattr(win, "_live_workers"):
        win._live_workers = []
    win._live_workers.append(worker)

    def _release(*_a: Any) -> None:
        try:
            win._live_workers.remove(worker)
        except ValueError:
            pass

    worker.signals.done.connect(_release)
    worker.signals.fail.connect(_release)
    worker.setAutoDelete(False)
    win.pool.start(worker)


def _activity(win: Any, kind: str, text: str) -> None:
    from .panels import add_activity

    add_activity(win.t, win.refs, _now_ts(), kind, text)


def _set_buttons(win: Any, enabled: dict[str, bool]) -> None:
    for key, on in enabled.items():
        win.nav[key].setEnabled(on)


def _suggest(win: Any, key: str | None) -> None:
    for k in MUTATORS + ("navHistorial", "navBlackforge"):
        win.nav[k].set_suggested(k == key)


def _lock_mutators(win: Any) -> None:
    for k in MUTATORS:
        win.nav[k].setEnabled(False)


def _session_badge(win: Any, active: bool) -> None:
    color = win.t.success if active else win.t.text_muted
    win.sessionDot.setStyleSheet(f"color:{color}; background:transparent;")
    win.sessionLabel.setText("Sesión activa" if active else "Sin sesión")


# ---------------------------------------------------------------------------
# S1 — SIN SESIÓN
# ---------------------------------------------------------------------------
def enter_s1(win: Any) -> None:
    from ..model_config import active_model_label

    _session_badge(win, False)
    win.greetingSub.setText("Crea una nueva idea para empezar")
    r = win.refs
    r["ideaTitle"].setText("Ninguna idea activa")
    r["ideaSummary"].setText("Pulsa Nueva idea para definir el problema base")
    set_chip(r["ideaEstadoChip"], "Sin sesión", "exploracion")
    r["scoreGauge"].hide()
    r["mOperadores"].set_value("0/16")
    r["mIdeas"].set_value("0")
    r["mConvergencia"].set_value("—")
    r["mBestScore"].set_value("—")
    for stage in r["stages"].values():
        stage.set_state("pending")
    for conn in r["connectors"]:
        conn.set_lit(False)
    r["rankingTable"].hide()
    r["rankingEmpty"].show()
    r["scoreHistogram"].set_bins([])
    r["catDonut"].set_segments([])
    r["catDonut"].set_center("0", "ideas totales")
    win.footerSegs["fsModelo"].set_value(
        f"CRIBA {ENGINE_VERSION} · {active_model_label()}"
    )
    win.footerSegs["fsSesion"].set_value("—")
    win.footerSegs["fsIdeas"].set_value("0")
    win.footerSegs["fsConvergencia"].set_value("—")
    win.footerSegs["fsUltima"].set_value("—")
    refresh_sources_freshness(win)
    _set_buttons(
        win,
        {
            "navNuevaIdea": True,
            "navGenerar": False,
            "navEvaluar": False,
            "navGuardar": False,
            "navActualizar": True,
            "navHistorial": True,
            "navBlackforge": True,
        },
    )
    _suggest(win, "navNuevaIdea")


# ---------------------------------------------------------------------------
# S2 — NUEVA IDEA SIN EVALUAR
# ---------------------------------------------------------------------------
def on_nueva_idea(win: Any) -> None:
    from .dialogs import ask_problem

    problem = ask_problem(win)
    win.nav["navNuevaIdea"].setChecked(False)
    if not problem:
        return
    _apply_new_problem(win, problem)


def on_nueva_idea_no_dialog(win: Any, problem: str) -> None:
    """Non-interactive variant: apply a problem without a modal dialog.

    Used by automated GUI regression tests (offscreen). Mirrors the real
    on_nueva_idea path exactly, minus the QDialog.
    """
    win.nav["navNuevaIdea"].setChecked(False)
    if not problem:
        return
    _apply_new_problem(win, problem)


def _apply_new_problem(win: Any, problem: str) -> None:
    win.problem = problem
    win.packet = None
    r = win.refs
    _session_badge(win, True)
    win.greetingSub.setText("Listo para transformar ideas en impacto")
    r["stages"]["stageProblema"].set_state("done")
    r["connectors"][0].set_lit(True)
    r["stages"]["stageGenerar"].set_state("active")
    for key in ("stageEvaluar", "stageGuardar", "stageEvolucionar"):
        r["stages"][key].set_state("pending")
    for conn in r["connectors"][1:]:
        conn.set_lit(False)
    r["ideaTitle"].setText(problem if len(problem) <= 120 else problem[:117] + "…")
    r["ideaSummary"].setText(
        "Problema base capturado. Genera ideas con los 16 operadores."
    )
    set_chip(r["ideaEstadoChip"], "Sin evaluar", "exploracion")
    r["scoreGauge"].show()
    r["scoreGauge"].set_score(0.0, animate=False)
    r["scoreGauge"].set_percentile("Pendiente")
    r["mOperadores"].set_value("0/16")
    r["mIdeas"].set_value("0")
    r["mConvergencia"].set_value("—")
    r["mBestScore"].set_value("—")
    _activity(win, "cyan", f"Problema base definido: {problem[:60]}")
    _set_buttons(
        win,
        {
            "navNuevaIdea": True,
            "navGenerar": True,
            "navEvaluar": False,
            "navGuardar": False,
            "navActualizar": True,
            "navHistorial": True,
            "navBlackforge": True,
        },
    )
    _suggest(win, "navGenerar")


# ---------------------------------------------------------------------------
# S3 — GENERANDO  (activate() genera Y evalúa; la fase visual se divide)
# ---------------------------------------------------------------------------
def _generate_criba_packet(problem: str) -> dict[str, Any]:
    """Run deterministic CRIBA and its optional semantic language layer."""

    from ..model_runtime import enhance_criba_packet

    return enhance_criba_packet(activate(problem))


def on_generar(win: Any) -> None:
    win.nav["navGenerar"].setChecked(False)
    if not win.problem:
        show_error(win, "Generar", "Define primero el problema base (Nueva idea).")
        return
    r = win.refs
    _lock_mutators(win)
    _suggest(win, None)
    win.nav["navGenerar"].set_state("running", "Ejecutando operadores...")
    r["stages"]["stageGenerar"].set_state("active", spinning=True)
    _activity(win, "blue", "Generación iniciada (16 operadores)")
    worker = Worker(lambda: _generate_criba_packet(win.problem))
    worker.signals.done.connect(lambda packet: _on_generated(win, packet))
    worker.signals.fail.connect(
        lambda msg: on_operation_error(win, "navGenerar", "stageGenerar", msg)
    )
    _start_worker(win, worker)


def _on_generated(win: Any, packet: dict[str, Any]) -> None:
    win.packet = packet
    r = win.refs
    ideas = packet["innovation"]["ideas"]
    win.nav["navGenerar"].set_state("done")
    r["stages"]["stageGenerar"].set_state("done")
    r["connectors"][1].set_lit(True)
    r["stages"]["stageEvaluar"].set_state("active")
    r["mOperadores"].set_value("16/16")
    r["mIdeas"].set_value(str(len(ideas)))
    _activity(
        win,
        "blue",
        f"{len(ideas)} ideas generadas "
        f"({packet['innovation']['real_divergent_count']} divergencia real)",
    )
    semantic = packet.get("semantic_generation", {})
    if semantic.get("status") in {"ok", "partial"}:
        enhanced_count = int(semantic.get("enhanced_count", 0))
        candidate_count = int(semantic.get("candidate_count", len(ideas)))
        suffix = " · respuesta parcial" if semantic.get("status") == "partial" else ""
        _activity(
            win,
            "orange" if semantic.get("status") == "partial" else "cyan",
            f"{enhanced_count}/{candidate_count} ideas prioritarias redactadas por "
            f"{semantic.get('model', 'modelo local')} "
            f"({semantic.get('reasoning', 'balanced')}){suffix}",
        )
        win.footerSegs["fsModelo"].set_value(
            str(semantic.get("model") or "Modelo local")
        )
    elif semantic.get("status") == "fallback":
        _activity(
            win, "orange", f"Modelo no disponible: {semantic.get('error', 'fallback')}"
        )
        win.footerSegs["fsModelo"].set_value("Determinista · fallback LLM")
    _set_buttons(
        win,
        {
            "navNuevaIdea": True,
            "navGenerar": True,
            "navEvaluar": True,
            "navGuardar": False,
            "navActualizar": True,
            "navHistorial": True,
            "navBlackforge": True,
        },
    )
    _suggest(win, "navEvaluar")


# ---------------------------------------------------------------------------
# S4 -> S5 — EVALUANDO -> RANKING LISTO
# ---------------------------------------------------------------------------
def on_evaluar(win: Any) -> None:
    win.nav["navEvaluar"].setChecked(False)
    if not win.packet:
        show_error(win, "Evaluar", "Genera ideas antes de evaluar.")
        return
    r = win.refs
    _lock_mutators(win)
    _suggest(win, None)
    win.nav["navEvaluar"].set_state("running", "Midiendo convergencia...")
    r["stages"]["stageEvaluar"].set_state("active", spinning=True)
    packet = win.packet
    worker = Worker(lambda: _build_ranking_rows(packet))
    worker.signals.done.connect(lambda rows: _on_evaluated(win, rows))
    worker.signals.fail.connect(
        lambda msg: on_operation_error(win, "navEvaluar", "stageEvaluar", msg)
    )
    _start_worker(win, worker)


def _build_ranking_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, idea in enumerate(packet["innovation"]["ideas"], start=1):
        conv = idea.get("convergence", {})
        rows.append(
            {
                "rank": i,
                "id": idea.get("id", ""),
                "titulo": idea.get("title") or idea.get("description", ""),
                "descripcion": idea.get("description", ""),
                "value_score": float(conv.get("value_score", 0.0)),
                "convergencia": float(conv.get("novelty", 0.0)),
                "estado": "candidata"
                if i <= 3
                else ("eval" if i <= 6 else "exploracion"),
            }
        )
    return rows


def _on_evaluated(win: Any, rows: list[dict[str, Any]]) -> None:
    r = win.refs
    packet = win.packet
    win.nav["navEvaluar"].set_state("done")
    r["stages"]["stageEvaluar"].set_state("done")
    r["connectors"][2].set_lit(True)
    r["stages"]["stageGuardar"].set_state("active")
    r["rankingModel"].set_rows(rows)
    r["rankingEmpty"].hide()
    r["rankingTable"].show()
    r["rankingTabs"].setCurrentIndex(0)
    if rows:
        best = rows[0]
        r["ideaTitle"].setText(best["titulo"][:120])
        r["ideaSummary"].setText(best["descripcion"][:240])
        set_chip(r["ideaEstadoChip"], "En evaluación", "eval")
        r["scoreGauge"].show()
        r["scoreGauge"].set_score(best["value_score"])
        pct = max(1, round(100 / max(1, len(rows))))
        r["scoreGauge"].set_percentile(f"Alto impacto · Top {pct}% del set")
        r["mBestScore"].set_value(f"{best['value_score']:.2f}")
        r["rankingTable"].selectRow(0)
    mean = packet["innovation"].get("mean_value_score", 0.0)
    conv_global = packet["metrics"].get("divergence", 0)
    r["mConvergencia"].set_value(f"{conv_global}%")
    _update_charts(win, rows)
    win.footerSegs["fsSesion"].set_value(f"CRB-{packet['activation_id'][:8].upper()}")
    win.footerSegs["fsIdeas"].set_value(str(len(rows)))
    win.footerSegs["fsConvergencia"].set_value(f"{conv_global}%")
    win.footerSegs["fsUltima"].set_value(datetime.now().strftime("%d/%m %H:%M"))
    _activity(
        win,
        "blue",
        f"Idea evaluada: {rows[0]['titulo'][:60]} (score {rows[0]['value_score']:.2f})"
        if rows
        else "Evaluación sin ideas",
    )
    _set_buttons(
        win,
        {
            "navNuevaIdea": True,
            "navGenerar": True,
            "navEvaluar": True,
            "navGuardar": True,
            "navActualizar": True,
            "navHistorial": True,
            "navBlackforge": True,
        },
    )
    _suggest(win, "navGuardar")


def _update_charts(win: Any, rows: list[dict[str, Any]]) -> None:
    r = win.refs
    t = win.t
    if not rows:
        return
    scores = [row["value_score"] for row in rows]
    lo, hi = min(scores), max(scores)
    span = (hi - lo) or 1.0
    nbins = 6
    bins = []
    for i in range(nbins):
        edge = lo + span * (i + 0.5) / nbins
        count = sum(
            1
            for s in scores
            if lo + span * i / nbins <= s <= lo + span * (i + 1) / nbins
        )
        bins.append((edge, count))
    r["scoreHistogram"].set_bins(bins)
    # donut por familia de operador (datos reales del packet)
    from collections import Counter

    fams = Counter(i.get("family", "otros") for i in win.packet["innovation"]["ideas"])
    top = fams.most_common(4)
    rest = sum(fams.values()) - sum(c for _, c in top)
    segs = []
    while r["donutLegend"].count():
        item = r["donutLegend"].takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    from .widgets import LegendRow

    total = sum(fams.values()) or 1
    for idx, (name, count) in enumerate(top, start=1):
        color = QColor(t.chart(idx))
        segs.append((name, float(count), color))
        r["donutLegend"].addWidget(
            LegendRow(t.chart(idx), name, f"{round(100 * count / total)}%")
        )
    if rest > 0:
        segs.append(("Otros", float(rest), QColor(t.chart(5))))
        r["donutLegend"].addWidget(
            LegendRow(t.chart(5), "Otros", f"{round(100 * rest / total)}%")
        )
    r["catDonut"].set_segments(segs)
    r["catDonut"].set_center(str(len(rows)), "ideas totales")


# ---------------------------------------------------------------------------
# S6 — GUARDADO COMPLETADO
# ---------------------------------------------------------------------------
def on_guardar(win: Any) -> None:
    win.nav["navGuardar"].setChecked(False)
    if not win.packet:
        show_error(win, "Guardar", "No hay evaluación que guardar.")
        return
    r = win.refs
    try:
        ident = win.store.save(
            win.packet["original_query"],
            win.packet,
            {"gui": True, "screen": "innovacion"},
        )
    except Exception as exc:  # noqa: BLE001
        on_operation_error(win, "navGuardar", "stageGuardar", str(exc))
        return
    win.saved_ids.add(ident)
    win.nav["navGuardar"].set_state("done")
    r["stages"]["stageGuardar"].set_state("done")
    r["connectors"][3].set_lit(True)
    r["stages"]["stageEvolucionar"].set_state("active")
    set_chip(r["ideaEstadoChip"], "Guardada en catálogo", "guardada")
    model: RankingModel = r["rankingModel"]
    model.mark_saved(0)
    title = r["ideaTitle"].text()
    _activity(win, "success", f"Idea guardada en catálogo: {title[:60]}")
    win.nav["navGuardar"].setEnabled(False)  # OFF† hasta cambiar selección
    _suggest(win, None)


# ---------------------------------------------------------------------------
# S7 — HISTORIAL
# ---------------------------------------------------------------------------
def on_historial(win: Any) -> None:
    win.nav["navHistorial"].setChecked(True)
    from .dialogs import show_history

    try:
        loaded = show_history(win)
    finally:
        win.nav["navHistorial"].setChecked(False)
    if loaded:
        packet = loaded["packet"]
        # Blackforge sessions use a different packet shape (ideas at top level,
        # selected_current.id == 'blackforge'); route them to the BF screen
        # instead of the CRIBA evaluator, which expects innovation.ideas.
        sc = packet.get("selected_current", {})
        if isinstance(sc, dict) and sc.get("id") == "blackforge":
            win.show_blackforge_page(history_packet=packet)
            return
        win.packet = packet
        win.problem = packet.get("original_query", "")
        r = win.refs
        _session_badge(win, True)
        r["stages"]["stageProblema"].set_state("done")
        r["connectors"][0].set_lit(True)
        r["stages"]["stageGenerar"].set_state("done")
        r["connectors"][1].set_lit(True)
        rows = _build_ranking_rows(win.packet)
        r["mOperadores"].set_value("16/16")
        r["mIdeas"].set_value(str(len(rows)))
        _activity(win, "cyan", f"Sesión cargada del historial: {win.problem[:50]}")
        _on_evaluated(win, rows)


# ---------------------------------------------------------------------------
# S8 — FUENTES (frescura + actualización bajo demanda, sin red: refresco local)
# ---------------------------------------------------------------------------
def on_actualizar(win: Any) -> None:
    win.nav["navActualizar"].setChecked(False)
    r = win.refs
    _lock_mutators(win)
    win.nav["navActualizar"].set_state("running", "Actualizando fuentes...")
    r["actualizarFuentesBtn"].setEnabled(False)
    r["actualizarFuentesBtn"].setText("Actualizando fuentes...")

    def _job() -> dict[str, int]:
        # Fuentes deterministas: derivadas del catálogo local (sin red por
        # defecto — security.no_network_by_default del contrato del engine).
        from ..catalog import currents, methods

        cs, ms = currents(), methods()
        fam = {}
        names = [
            "Tecnología emergente",
            "Tendencias de negocio",
            "Investigación científica",
            "Diseño & experiencia",
            "Comunidad & open source",
        ]
        for i, name in enumerate(names):
            fam[name] = min(100, 40 + (len(ms) * (i + 3)) % 55 + len(cs))
        return fam

    worker = Worker(_job)
    worker.signals.done.connect(lambda fam: _on_sources_updated(win, fam))
    worker.signals.fail.connect(
        lambda msg: on_operation_error(win, "navActualizar", None, msg)
    )
    _start_worker(win, worker)


def _on_sources_updated(win: Any, fam: dict[str, int]) -> None:
    r = win.refs
    win.sources_updated_at = datetime.now()
    for name, pct in fam.items():
        if name in r["sourceBars"]:
            r["sourceBars"][name].set_percent(pct)
    win.nav["navActualizar"].set_state("done")
    r["actualizarFuentesBtn"].setEnabled(True)
    r["actualizarFuentesBtn"].setText("Actualizar innovaciones")
    r["actualizarFuentesBtn"].setProperty("freshness", "")
    r["actualizarFuentesBtn"].style().polish(r["actualizarFuentesBtn"])
    r["staleBand"].hide()
    _activity(win, "cyan", "Nuevas tendencias incorporadas")
    refresh_sources_freshness(win)
    _restore_buttons_after_op(win)


def refresh_sources_freshness(win: Any) -> None:
    seg = win.footerSegs["fsFuentes"]
    r = win.refs
    if win.sources_updated_at is None:
        seg.set_value("Sin actualizar")
        seg.set_freshness("stale")
        r["staleBand"].show()
        return
    mins = int((datetime.now() - win.sources_updated_at).total_seconds() // 60)
    if mins < 60:
        seg.set_value(f"Hace {mins} min")
        seg.set_freshness("ok")
        r["staleBand"].hide()
    else:
        seg.set_value(f"Hace {mins // 60} h")
        seg.set_freshness("warn")
        r["staleBand"].show()


# ---------------------------------------------------------------------------
# S9 — ERROR DE OPERACIÓN
# ---------------------------------------------------------------------------
def show_error(win: Any, op: str, msg: str) -> None:
    win.errorBannerText.setText(f"Fallo en {op}: {msg.splitlines()[0][:160]}")
    win.errorBanner.show()


def on_operation_error(win: Any, nav_key: str, stage_key: str | None, msg: str) -> None:
    first = msg.splitlines()[0][:60]
    win.nav[nav_key].set_state("error", f"Error: {first}")
    if stage_key:
        win.refs["stages"][stage_key].set_state("error")
    show_error(win, win.nav[nav_key].text() or nav_key, msg)
    _activity(win, "error", f"Fallo en operación: {first}")
    _restore_buttons_after_op(win)


def _restore_buttons_after_op(win: Any) -> None:
    has_problem = bool(win.problem)
    has_packet = win.packet is not None
    _set_buttons(
        win,
        {
            "navNuevaIdea": True,
            "navGenerar": has_problem,
            "navEvaluar": has_packet,
            "navGuardar": has_packet,
            "navActualizar": True,
            "navHistorial": True,
            "navBlackforge": True,
        },
    )


# ---------------------------------------------------------------------------
# S10 — BLACKFORGE (aplicación especializada independiente)
# ---------------------------------------------------------------------------
def on_blackforge(win: Any) -> None:
    win.nav["navBlackforge"].setChecked(False)
    win.show_blackforge_page()


def on_modelos(win: Any) -> None:
    """Open the shared local-model profile manager."""

    from ..model_config import active_model_label
    from .model_settings_dialog import open_model_settings

    win.nav["navModelos"].setChecked(False)
    if open_model_settings(win):
        win.footerSegs["fsModelo"].set_value(
            f"CRIBA {ENGINE_VERSION} · {active_model_label()}"
        )
        _activity(win, "cyan", f"Modelo activo: {active_model_label()}")


# ---------------------------------------------------------------------------
# ranking helpers
# ---------------------------------------------------------------------------
def on_tab_changed(win: Any, index: int) -> None:
    modes = ["", "top", "eval", "exploracion"]
    win.refs["rankingProxy"].set_mode(modes[index] if index < len(modes) else "")


def on_ver_todas(win: Any) -> None:
    win.refs["rankingTabs"].setCurrentIndex(0)
    win.refs["rankingProxy"].set_mode("")
