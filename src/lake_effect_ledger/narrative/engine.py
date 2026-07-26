"""Pure rule engine for decisions, typed effects, and delayed events."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta, timezone

from lake_effect_ledger.accounting.models import JournalEntry
from lake_effect_ledger.learning.models import TrajectoryTag
from lake_effect_ledger.narrative.models import (
    AddInboxEffect,
    ChoiceDefinition,
    ContentBundle,
    Effect,
    PostJournalEffect,
    RecordCommunicationEffect,
    RelationshipDeltaEffect,
    ResourceDeltaEffect,
    ScheduleEventEffect,
    SetChapterFieldEffect,
    SetChapterFlagEffect,
    SetCommodityFieldEffect,
    SetFlagEffect,
    TrajectoryDeltaEffect,
)
from lake_effect_ledger.state import GameState, InboxItem, ScheduledEvent
from lake_effect_ledger.trading.models import ExceptionNotificationRecord
from lake_effect_ledger.treasury.models import CommunicationRecord


class NarrativeEngine:
    def __init__(self, content: ContentBundle) -> None:
        self.content = content

    def choose(self, state: GameState, scene_id: str, choice_id: str) -> ChoiceDefinition:
        if scene_id == "december_difference" and state.completed:
            raise ValueError("the December Difference day is already complete")
        if scene_id == "hedge_documentation" and state.hedge_book is None:
            raise ValueError("a hedge position must exist before documenting it")
        scene = self.content.scene(scene_id)
        if choice_id in state.decisions:
            raise ValueError(f"choice has already been applied: {choice_id}")
        prior_scene_choices = {item.id for item in scene.choices if item.id in state.decisions}
        if prior_scene_choices:
            raise ValueError(
                f"scene {scene_id} already has a durable choice: "
                f"{', '.join(sorted(prior_scene_choices))}"
            )
        try:
            choice = next(item for item in scene.choices if item.id == choice_id)
        except StopIteration as error:
            raise ValueError(f"unknown choice {choice_id} for scene {scene_id}") from error
        if not all(self._condition_met(state, item) for item in choice.conditions):
            raise ValueError(f"choice conditions are not met: {choice_id}")

        state.decisions.append(choice.id)
        if state.eleventh_contract is not None and scene.chapter == "The Eleventh Contract":
            state.eleventh_contract.decisions.append(choice.id)
        for objective in choice.learning_objectives:
            if objective not in state.learning_objectives:
                state.learning_objectives.append(objective)
        state.record(
            phase="decision",
            event_type="decision_made",
            source_id=choice.id,
            message=choice.text,
            changes={"scene_id": scene_id, "choice_id": choice.id},
        )
        self._apply_effects(state, choice.effects, choice.id, phase="immediate")
        return choice

    def available_choices(self, state: GameState, scene_id: str) -> list[ChoiceDefinition]:
        scene = self.content.scene(scene_id)
        return [
            choice
            for choice in scene.choices
            if all(self._condition_met(state, item) for item in choice.conditions)
        ]

    def resolved_scene_text(self, state: GameState, scene_id: str) -> str:
        scene = self.content.scene(scene_id)
        paragraphs = [scene.text]
        paragraphs.extend(
            item.text
            for item in scene.conditional_paragraphs
            if all(self._condition_met(state, condition) for condition in item.conditions)
        )
        return "\n\n".join(paragraphs)

    def process_end_of_day(self, state: GameState) -> None:
        due = sorted(
            (item for item in state.scheduled_events if item.due_day <= state.day_number),
            key=lambda item: (item.due_day, item.event_id),
        )
        for scheduled in due:
            event = self.content.event(scheduled.event_id)
            state.record(
                phase="end_of_day",
                event_type="scheduled_event_fired",
                source_id=event.id,
                message=event.title,
                changes={"scheduled_by": scheduled.scheduled_by},
            )
            self._apply_effects(state, event.effects, event.id, phase="end_of_day")
            state.end_of_day_messages.append(f"{event.title}: {event.text}")
            state.scheduled_events.remove(scheduled)
        state.completed = True
        state.record(
            phase="system",
            event_type="day_completed",
            source_id="episode_01_day_01",
            message="The one-day vertical slice is complete.",
        )

    def _apply_effects(
        self,
        state: GameState,
        effects: list[Effect],
        source_id: str,
        *,
        phase: str,
    ) -> None:
        for effect in effects:
            if isinstance(effect, ResourceDeltaEffect):
                self._apply_resource_delta(state, effect, source_id, phase)
            elif isinstance(effect, SetFlagEffect):
                old_value = state.flags.get(effect.target)
                state.flags[effect.target] = effect.value
                state.record(
                    phase=phase,
                    event_type=effect.type,
                    source_id=source_id,
                    message=f"Flag {effect.target} set to {effect.value}.",
                    changes={"old": old_value, "new": effect.value},
                )
            elif isinstance(effect, PostJournalEffect):
                self._post_journal(state, effect, source_id, phase)
            elif isinstance(effect, ScheduleEventEffect):
                if any(item.event_id == effect.event_id for item in state.scheduled_events):
                    raise ValueError(f"event already scheduled: {effect.event_id}")
                scheduled = ScheduledEvent(
                    event_id=effect.event_id,
                    due_day=state.day_number + effect.due_in_days,
                    scheduled_by=source_id,
                )
                state.scheduled_events.append(scheduled)
                state.record(
                    phase=phase,
                    event_type=effect.type,
                    source_id=source_id,
                    message=f"Scheduled {effect.event_id} for day {scheduled.due_day}.",
                    changes={
                        "event_id": effect.event_id,
                        "due_day": scheduled.due_day,
                    },
                )
            elif isinstance(effect, AddInboxEffect):
                if any(item.item_id == effect.item_id for item in state.inbox):
                    raise ValueError(f"inbox item already exists: {effect.item_id}")
                state.inbox.append(
                    InboxItem(
                        item_id=effect.item_id,
                        sender=effect.sender,
                        subject=effect.subject,
                        urgent=effect.urgent,
                    )
                )
                state.record(
                    phase=phase,
                    event_type=effect.type,
                    source_id=source_id,
                    message=f"Inbox item added from {effect.sender}.",
                    changes={"item_id": effect.item_id},
                )
            elif isinstance(effect, SetCommodityFieldEffect):
                if state.hedge_book is None:
                    raise ValueError("commodity effect requires an active Hedge Book")
                if effect.target == "documentation_quality":
                    old_value = state.hedge_book.documentation_quality
                    state.hedge_book.documentation_quality = effect.value
                    state.record(
                        phase=phase,
                        event_type=effect.type,
                        source_id=source_id,
                        message=f"Hedge documentation set to {effect.value.value}.",
                        changes={
                            "field": effect.target,
                            "old": old_value.value,
                            "new": effect.value.value,
                        },
                    )
            elif isinstance(effect, TrajectoryDeltaEffect):
                state.career_trajectory.record(source_id, effect.target, effect.amount)
                state.record(
                    phase=phase,
                    event_type=effect.type,
                    source_id=source_id,
                    message="A durable career tendency shifted.",
                    changes={"tag": effect.target.value, "amount": effect.amount},
                )
            elif isinstance(effect, RecordCommunicationEffect):
                if any(item.record_id == effect.record_id for item in state.evidence_log):
                    raise ValueError(f"communication already recorded: {effect.record_id}")
                record_timezone = (
                    timezone(timedelta(hours=-6), name="CST")
                    if state.eleventh_contract is not None
                    else UTC
                )
                record_timestamp = datetime.combine(
                    state.current_date,
                    time(hour=9),
                    tzinfo=record_timezone,
                )
                state.evidence_log.append(
                    CommunicationRecord(
                        record_id=effect.record_id,
                        timestamp=record_timestamp,
                        channel=effect.channel,
                        sender_id=effect.sender_id,
                        recipient_ids=effect.recipient_ids,
                        subject=effect.subject,
                        body_summary=effect.body_summary,
                        accuracy=effect.accuracy,
                        linked_decision_ids=[source_id],
                    )
                )
                if state.eleventh_contract is not None:
                    chapter = state.eleventh_contract
                    chapter.communication_record_ids.append(effect.record_id)
                    if source_id == "ec_notify_evelyn_formally":
                        if chapter.reconciliation is None:
                            from lake_effect_ledger.trading.engine import (
                                EleventhContractEngine,
                            )

                            EleventhContractEngine(self.content).ensure_reconciliation(state)
                        chapter.notification_record_ids.append(effect.record_id)
                        chapter.notifications.append(
                            ExceptionNotificationRecord(
                                notification_id="notification_ec_formal_exception",
                                notified_at=record_timestamp,
                                decision_id=source_id,
                                recipient_ids=list(effect.recipient_ids),
                                communication_record_id=effect.record_id,
                                reconciliation_id=chapter.reconciliation.reconciliation_id,
                                status_at_notification=chapter.reconciliation.current_status,
                            )
                        )
                state.record(
                    phase=phase,
                    event_type=effect.type,
                    source_id=source_id,
                    message=f"Communication record {effect.record_id} preserved.",
                    changes={"record_id": effect.record_id, "accuracy": effect.accuracy.value},
                )
            elif isinstance(effect, SetChapterFieldEffect):
                chapter = state.eleventh_contract
                if chapter is None:
                    raise ValueError("chapter field effect requires The Eleventh Contract")
                old_value = getattr(chapter, effect.target)
                setattr(chapter, effect.target, effect.value)
                state.record(
                    phase=phase,
                    event_type=effect.type,
                    source_id=source_id,
                    message=f"Chapter field {effect.target} was set.",
                    changes={
                        "field": effect.target,
                        "old": (old_value.value if hasattr(old_value, "value") else old_value),
                        "new": effect.value,
                    },
                )
            elif isinstance(effect, SetChapterFlagEffect):
                chapter = state.eleventh_contract
                if chapter is None:
                    raise ValueError("chapter flag effect requires The Eleventh Contract")
                old_value = chapter.chapter_flags.get(effect.target)
                chapter.chapter_flags[effect.target] = effect.value
                state.record(
                    phase=phase,
                    event_type=effect.type,
                    source_id=source_id,
                    message=f"Chapter flag {effect.target} was set.",
                    changes={"old": old_value, "new": effect.value},
                )
            elif isinstance(effect, RelationshipDeltaEffect):
                chapter = state.eleventh_contract
                if chapter is None:
                    raise ValueError("relationship effect requires The Eleventh Contract")
                old_value = chapter.relationships.get(effect.target, 0)
                new_value = max(-10, min(10, old_value + effect.amount))
                chapter.relationships[effect.target] = new_value
                state.record(
                    phase=phase,
                    event_type=effect.type,
                    source_id=source_id,
                    message=f"Relationship with {effect.target} changed.",
                    changes={
                        "character": effect.target,
                        "old": old_value,
                        "new": new_value,
                        "requested_delta": effect.amount,
                    },
                )
            else:  # pragma: no cover - discriminated validation makes this unreachable
                raise TypeError(f"unsupported effect: {type(effect).__name__}")

    @staticmethod
    def _condition_met(state: GameState, condition) -> bool:
        if condition.kind == "decision_made":
            return condition.target in state.decisions
        if condition.kind == "decision_not_made":
            return condition.target not in state.decisions
        if condition.kind == "chapter_flag":
            chapter = state.eleventh_contract
            return (
                chapter is not None
                and chapter.chapter_flags.get(condition.target) == condition.value
            )
        if condition.kind == "trajectory_min":
            try:
                tag = TrajectoryTag(condition.target)
            except ValueError:
                return False
            return state.career_trajectory.tag_weights.get(tag, 0) >= int(condition.value)
        if condition.kind == "treasury_notification":
            return (
                state.treasury is not None
                and state.treasury.notification_choice is not None
                and state.treasury.notification_choice.value == condition.target
            )
        if condition.kind == "treasury_funding":
            return (
                state.treasury is not None
                and state.treasury.funding_decision is not None
                and state.treasury.funding_decision.choice.value == condition.target
            )
        if condition.kind == "game_mode":
            return state.game_mode.value == condition.target
        if condition.kind == "physical_outcome":
            chapter = state.eleventh_contract
            return (
                chapter is not None
                and chapter.physical_forecast.revealed
                and chapter.physical_forecast.outcome.value == condition.target
            )
        return False

    @staticmethod
    def _apply_resource_delta(
        state: GameState,
        effect: ResourceDeltaEffect,
        source_id: str,
        phase: str,
    ) -> None:
        name = effect.target.value
        old_value = getattr(state.resources, name)
        new_value = old_value + effect.amount
        if not 0 <= new_value <= 100:
            raise ValueError(f"resource effect would exceed bounds: {name} -> {new_value}")
        setattr(state.resources, name, new_value)
        state.record(
            phase=phase,
            event_type=effect.type,
            source_id=source_id,
            message=f"{name} changed by {effect.amount:+d}.",
            changes={"resource": name, "old": old_value, "new": new_value},
        )

    def _post_journal(
        self,
        state: GameState,
        effect: PostJournalEffect,
        source_id: str,
        phase: str,
    ) -> None:
        template = self.content.journal_template(effect.template_id)
        entry = JournalEntry(
            transaction_id=f"txn_{template.id}",
            entry_date=state.current_date,
            description=template.description,
            source_id=source_id,
            lines=template.lines,
        )
        state.ledger.post(entry, self.content.valid_accounts)
        state.record(
            phase=phase,
            event_type=effect.type,
            source_id=source_id,
            message=f"Posted balanced entry {entry.transaction_id}.",
            changes={
                "transaction_id": entry.transaction_id,
                "debits": str(entry.total_debits),
                "credits": str(entry.total_credits),
            },
        )
