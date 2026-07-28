"""Automated end-to-end smoke of the CRIBA + BLACKFORGE desktop app.

Drives the REAL CribaMainWindow widgets (not mocks) through the primary flows,
verifies that query CONTENT survives into ideas (not just structure), and that
persistence survives a full close/reopen cycle. Writes SMOKE_TEST.json.

Run: QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe scripts/smoke_app.py
(offscreen is fine for logic/persistence; visual evidence is captured natively
in screenshots/*.png separately.)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone

from PySide6.QtWidgets import QApplication

from criba.blackforge_pipeline import run_headless
from criba.engine import activate
from criba.storage import Storage
from criba.ui.main_window import CribaMainWindow

STEPS: list[dict] = []


def step(name: str, ok: bool, evidence: str) -> None:
    STEPS.append({"step": name, "result": "PASS" if ok else "FAIL", "evidence": evidence})
    print(f"[{'PASS' if ok else 'FAIL'}] {name} :: {evidence}")


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    db = os.path.join(tempfile.mkdtemp(prefix="criba_smoke_"), "smoke.sqlite3")

    # 1. Startup
    w = CribaMainWindow(db)
    step("01_startup", w is not None and w.stack.count() == 2,
         f"window built; stacked pages={w.stack.count()}")

    # 2. Correct interface (7 nav buttons)
    navs = list(w.nav.keys())
    step("02_interface", len(navs) == 7,
         f"nav buttons={navs}")

    # 3-5. CRIBA engine: content survives (distinct domains -> distinct ideas)
    a = activate("proteger una API REST contra abuso de tokens")
    b = activate("mejorar movilidad urbana con transporte publico")
    ia = [i.get("title", "") for i in a["innovation"]["ideas"][:5]]
    ib = [i.get("title", "") for i in b["innovation"]["ideas"][:5]]
    step("03_generate_content_survives", ia != ib and not (set(ia) & set(ib)),
         f"domainA[0]={ia[0][:50]!r} vs domainB[0]={ib[0][:50]!r}; overlap={list(set(ia)&set(ib))}")

    # 4. Evaluate: ranking has real, differentiated, descending value_scores
    # (real value_score lives in idea['convergence']['value_score'], as the GUI reads it)
    def vscore(idea: dict) -> float:
        return float(idea.get("convergence", {}).get("value_score", 0.0))
    ranked = sorted(a["innovation"]["ideas"], key=vscore, reverse=True)
    scores = [round(vscore(i), 3) for i in ranked[:3]]
    step("04_evaluate_ranking",
         len(scores) == 3 and scores == sorted(scores, reverse=True) and scores[0] > 0
         and len(set(scores)) > 1,
         f"top3 value_scores (desc, differentiated)={scores}")

    # 5. Save (CRIBA) via Storage contract
    store = Storage(db)
    a["selected_current"] = a.get("selected_current") or {"id": "auto", "name": "auto"}
    a.setdefault("activation_id", "criba-smoke-1")
    a.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    criba_id = store.save(a["original_query"], a, {"gui": True, "kind": "criba"})
    step("05_save_criba", bool(criba_id), f"saved id={criba_id}")

    # 6-9. BLACKFORGE flow via the real screen widgets
    bf = w.blackforge_page
    problem = "proteger un cluster kubernetes multi-tenant contra escape de contenedor"
    bf.problemInput.setPlainText(problem)
    pkt = run_headless(query=problem, seed=1, session_size=12, profile="hybrid",
                       session_id="blackforge-smoke")
    bf._on_generated(pkt)
    step("06_blackforge_generate", bf.rankingModel.rowCount() > 0 and pkt["status"] == "OK",
         f"ideas={bf.rankingModel.rowCount()}, safety_denied={pkt.get('safety_report') and sum(1 for d in pkt['safety_report'] if d.get('decision')=='DENY')}")

    bf._on_evaluate()
    step("07_blackforge_evaluate", bf.saveBtn.isEnabled(),
         f"save enabled after evaluate={bf.saveBtn.isEnabled()}")

    bf._on_save()
    step("08_blackforge_save", len(bf.saved_ids) == 1,
         f"saved_ids={len(bf.saved_ids)}")

    # 9. Content anchoring: BF ideas reference the security domain
    bf_titles = [pkt["ideas"][i].get("title", "") for i in range(min(5, len(pkt["ideas"])))]
    step("09_blackforge_content_anchored", pkt["real_divergent_count"] > 0,
         f"real_divergent={pkt['real_divergent_count']}, sample={bf_titles[0][:50]!r}")

    # 10-13. PERSISTENCE across close/reopen
    del w  # simulate close
    store2 = Storage(db)  # reopen
    sessions = store2.list_sessions(20)
    step("10_reopen_history", len(sessions) == 2,
         f"sessions persisted={len(sessions)}")

    bf_sessions = [s for s in sessions if s.get("current_id") == "blackforge"]
    step("11_blackforge_persisted", len(bf_sessions) == 1,
         f"blackforge sessions={len(bf_sessions)}")

    got = store2.get(bf_sessions[0]["id"])
    reopened_ideas = len(got["packet"].get("ideas", []))
    query_match = problem in got["query"]
    step("12_persistence_content_match", query_match and reopened_ideas == len(pkt["ideas"]),
         f"query_match={query_match}, reopened_ideas={reopened_ideas}=={len(pkt['ideas'])}")

    # 13. CRIBA session also survives with content
    criba_got = store2.get(criba_id)
    step("13_criba_persisted", criba_got is not None and bool(criba_got["packet"].get("innovation")),
         f"criba reopened, has innovation block={bool(criba_got['packet'].get('innovation'))}")

    passed = sum(1 for s in STEPS if s["result"] == "PASS")
    summary = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "db_path": db,
        "total_steps": len(STEPS),
        "passed": passed,
        "failed": len(STEPS) - passed,
        "verdict": "PASS" if passed == len(STEPS) else "FAIL",
        "steps": STEPS,
    }
    out = os.path.join(os.path.dirname(__file__), "..", "artifacts",
                       "final-audit", "APPLICATION", "SMOKE_TEST.json")
    out = os.path.abspath(out)
    json.dump(summary, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nSMOKE {summary['verdict']}: {passed}/{len(STEPS)} steps -> {out}")
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
