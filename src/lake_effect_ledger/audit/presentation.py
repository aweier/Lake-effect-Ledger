"""Rich terminal views for the No Surprises walkthrough."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lake_effect_ledger.audit.models import AuditSceneDefinition
from lake_effect_ledger.audit.report import InternalAuditWalkthroughReport
from lake_effect_ledger.state import GameState


def render_audit_scene(
    console: Console,
    state: GameState,
    scene: AuditSceneDefinition,
) -> None:
    text = scene.text
    audit = state.no_surprises
    chapter = state.eleventh_contract
    if scene.id == "ns_walkthrough_style" and audit is not None:
        if audit.package_strategy and audit.package_strategy.value == "evelyn_review_first":
            text += (
                "\n\nNoah notes that the initial response omitted conditional records. "
                "He starts with the records received and reserves follow-up."
            )
        elif audit.package_strategy and audit.package_strategy.value == "complete_linked_chain":
            text += "\n\nNoah has already followed the links in the complete package."
    if scene.id == "ns_volume_source" and chapter is not None:
        if chapter.chapter_flags.get("accepted_cal_explanation"):
            text += "\n\nNoah has the limited email that adopted Cal's expected-supply wording."
        if chapter.physical_forecast.support_document_ids:
            text += "\n\nMarisol reminds the room that Friday support was not Monday support."
    if scene.id == "ns_supplement_package" and audit is not None:
        omitted = [
            item
            for item in audit.evidence_request.requested_items
            if item.available and not item.included_initially
        ]
        if not omitted:
            text += "\n\nThe request list shows no available requested record omitted initially."
    console.print(Panel(text, title=f"Day {scene.day} · {scene.title}", border_style="cyan"))


def render_audit_request_list(console: Console, state: GameState) -> None:
    audit = state.no_surprises
    if audit is None:
        raise ValueError("No Surprises has not started")
    table = Table(title="Audit Request List", header_style="bold cyan")
    table.add_column("Requested record")
    table.add_column("Stable ID")
    table.add_column("Type")
    table.add_column("Available")
    table.add_column("Initial")
    table.add_column("Created")
    table.add_column("Provided")
    table.add_column("Transaction")
    table.add_column("Timing")
    for item in audit.evidence_request.requested_items:
        table.add_row(
            item.requested_record,
            item.stable_record_id,
            item.record_type,
            "yes" if item.available else "missing",
            "yes" if item.included_initially else "no",
            item.date_created.isoformat(timespec="minutes") if item.date_created else "not stored",
            item.date_provided.isoformat(timespec="minutes") if item.date_provided else "—",
            item.related_transaction,
            (
                "contemporaneous"
                if item.contemporaneous
                else "later-created"
                if item.contemporaneous is False
                else "unknown"
            ),
        )
    console.print(table)


def render_walkthrough_timeline(
    console: Console,
    state: GameState,
    *,
    debug: bool = False,
) -> None:
    audit = state.no_surprises
    if audit is None or audit.chronology is None:
        raise ValueError("build the audit chronology before rendering")
    table = Table(title="Walkthrough Timeline", header_style="bold cyan")
    table.add_column("Timestamp")
    table.add_column("Event")
    table.add_column("Record")
    table.add_column("Observation")
    if debug:
        table.add_column("Resolved type")
    received_ids = {
        item.stable_record_id
        for item in audit.evidence_request.requested_items
        if item.response_status in {"provided", "supplemented"}
    }
    received_ids.update(
        record_id
        for response in audit.package_responses
        for record_id in [response.response_id, *response.additional_record_ids]
    )
    visible_entries = [
        entry for entry in audit.chronology.entries if debug or entry.record_id in received_ids
    ]
    for entry in visible_entries:
        row = [
            entry.timestamp.isoformat(timespec="minutes") if entry.timestamp else "time not stored",
            entry.event_label,
            entry.record_id,
            entry.observation,
        ]
        if debug:
            row.append(entry.record_type)
        table.add_row(*row)
    console.print(table)
    visible_contradictions = list(audit.chronology.contradictions)
    if not debug:
        if "final_nomination_additional_10000" not in received_ids:
            visible_contradictions = [
                item
                for item in visible_contradictions
                if not item.startswith("Additional physical support arrived")
            ]
        if "offset_eleventh_contract" not in received_ids:
            visible_contradictions = [
                item
                for item in visible_contradictions
                if not item.startswith("The offset remediated")
            ]
    if visible_contradictions:
        console.print(
            Panel(
                "\n".join(f"• {item}" for item in visible_contradictions),
                title="Record differences",
                border_style="yellow",
            )
        )
    if not debug and len(visible_entries) != len(audit.chronology.entries):
        console.print(
            "[dim]Normal view shows records received by audit. "
            "Debug view exposes resolution details for verification.[/dim]"
        )


def render_control_results(console: Console, state: GameState) -> None:
    audit = state.no_surprises
    if audit is None:
        raise ValueError("No Surprises has not started")
    table = Table(title="Internal Audit Control Testing", header_style="bold cyan")
    table.add_column("Objective")
    table.add_column("Result")
    table.add_column("Design")
    table.add_column("Operation")
    table.add_column("Evidence")
    for result in audit.control_results:
        table.add_row(
            result.control_objective_id,
            result.rating.value.replace("_", " "),
            "effective" if result.design_effective else "gap",
            "effective" if result.operating_effective else "exception",
            ", ".join(result.evidence_record_ids),
        )
    console.print(table)


def render_preliminary_findings(console: Console, state: GameState) -> None:
    audit = state.no_surprises
    if audit is None:
        raise ValueError("No Surprises has not started")
    if not audit.findings:
        console.print(Panel("No reportable findings.", title="Preliminary findings"))
        return
    text = "\n\n".join(
        (
            f"[bold]{finding.title}[/bold] "
            f"([yellow]{finding.severity.value.title()}[/yellow])\n"
            f"{finding.rationale}\nEvidence: {', '.join(finding.evidence_record_ids)}"
        )
        for finding in audit.findings
    )
    console.print(Panel(text, title="Preliminary findings", border_style="yellow"))


def render_internal_audit_report(
    console: Console,
    report: InternalAuditWalkthroughReport,
) -> None:
    console.print(
        Panel(
            f"[bold]{report.outcome.value.replace('_', ' ').title()}[/bold]\n\n"
            f"{report.engagement_objective}\n\n"
            f"Prior case outcome: {report.prior_transaction_outcome.value}\n"
            f"Findings: {len(report.findings)} · Exceptions: {len(report.exceptions)} · "
            f"Supplemental responses: {len(report.supplemental_responses)}\n"
            f"Record reconciliation: "
            f"{'complete' if report.reconciled_to_preserved_records else 'failed'}",
            title=report.title,
            border_style="green",
        )
    )
    findings = Table(title="Findings and Management Response", header_style="bold cyan")
    findings.add_column("Finding")
    findings.add_column("Severity")
    findings.add_column("Status")
    findings.add_column("Response")
    response_by_finding = {item.finding_id: item for item in report.management_responses}
    for finding in report.findings:
        response = response_by_finding.get(finding.finding_id)
        findings.add_row(
            finding.title,
            finding.severity.value.title(),
            finding.status.value.replace("_", " "),
            (f"{response.agreement.value}; {response.root_cause.value}" if response else "pending"),
        )
    console.print(findings)
    if report.remediation_plans:
        remediation = report.remediation_plans[0]
        console.print(
            Panel(
                f"{remediation.proposed_action}\n\n"
                f"Owner: {remediation.owner.role} ({remediation.owner.person_id})\n"
                f"Target: {remediation.target_date.isoformat()}\n"
                f"Interim: {remediation.interim_control}\n"
                f"Residual risk: {remediation.residual_risk}",
                title=f"Remediation · {remediation.kind.value.replace('_', ' ')}",
                border_style="cyan",
            )
        )
