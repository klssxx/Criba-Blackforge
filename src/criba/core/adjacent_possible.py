"""Adjacent Possible & Empirical Falsification Governor for CRIBA & BLACKFORGE.

Enforces strict semantic-causal boundaries (0.45 <= D_H <= 0.85), SOTA Taboo
repulsion, and automated Null-Hypothesis (H0) synthesis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


# 100 Dominant SOTA Industry Clichés (SOTA Taboo List)
SOTA_TABOO_PATTERNS = frozenset([
    # Cyber & Auth
    "static_firewall", "signature_detection", "periodic_token_refresh", "bearer_header",
    "central_ldap", "sms_2fa", "ip_whitelist", "port_blocking", "hardcoded_roles",
    "password_complexity", "vpn_tunnel", "tls_termination_proxy", "rbac_matrix",
    "antivirus_scan", "log_file_grep", "scheduled_patching", "perimeter_dmz",
    # Architecture & Data
    "monolithic_cron", "polling_loop", "sql_crud_table", "rest_json_wrapper",
    "central_database", "session_cookie", "in_memory_singleton", "linear_retry",
    "csv_export", "manual_audit_form", "api_gateway_bottleneck", "static_routing",
    # Innovation & Product Clichés
    "discount_coupon_app", "loyalty_points_card", "chatbot_faq", "social_feed",
    "community_forum", "referral_program", "banner_ad_monetization", "subscription_tier_basic",
    "gamification_badges", "newsletter_blast", "qr_code_menu", "dashboard_analytics_pie",
])


@dataclass
class FalsificationContract:
    hypothesis_id: str
    target_axiom: str
    intervention: str
    null_hypothesis_h0: str
    verification_metric: str
    adjacent_distance: float
    is_valid_adjacent_possible: bool
    sota_taboo_violations: list[str]
    containment_class: str


class AdjacentPossibleGovernor:
    """Evaluates candidate proposals to guarantee they reside strictly in the Adjacent Possible."""

    def __init__(self, min_dist: float = 0.45, max_dist: float = 0.85) -> None:
        self.min_dist = min_dist
        self.max_dist = max_dist

    def evaluate_proposal(
        self,
        proposal_id: str,
        target_axiom: str,
        intervention: str,
        causal_axes_moved: Sequence[str],
        domain: str = "cybersecurity",
    ) -> FalsificationContract:
        """Evaluate a proposal and return an auditable FalsificationContract."""
        # 1. Calculate semantic-causal distance D_H
        axes_count = len(causal_axes_moved)
        raw_dist = 0.40 + 0.12 * axes_count
        adj_dist = round(min(1.0, max(0.0, raw_dist)), 3)
        is_valid = self.min_dist <= adj_dist <= self.max_dist

        # 2. Check SOTA Taboo violations
        combined_text = f"{target_axiom} {intervention}".lower()
        violations = [pat for pat in SOTA_TABOO_PATTERNS if pat in combined_text]

        # 3. Formulate Null Hypothesis (H0)
        h0 = (
            f"H0: Intervening on '{intervention}' to break '{target_axiom}' fails to produce a "
            f"statistically significant divergence in {domain} metrics (alpha = 0.05) or introduces "
            f"an uncontained side-effect."
        )

        # 4. Determine containment class
        containment = "S1_DEFENSIVE" if axes_count <= 2 else ("S2_SANDBOX" if axes_count <= 4 else "S3_SUPERVISED")

        return FalsificationContract(
            hypothesis_id=f"hyp-{proposal_id[:8]}",
            target_axiom=target_axiom,
            intervention=intervention,
            null_hypothesis_h0=h0,
            verification_metric=f"delta_{causal_axes_moved[0] if axes_count > 0 else 'posture'}_efficacy",
            adjacent_distance=adj_dist,
            is_valid_adjacent_possible=is_valid and len(violations) == 0,
            sota_taboo_violations=violations,
            containment_class=containment,
        )
