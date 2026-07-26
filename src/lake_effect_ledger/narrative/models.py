"""Pydantic schemas for all editable YAML content."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, Field, TypeAdapter, model_validator

from lake_effect_ledger.accounting.models import AccountDefinition, JournalLine
from lake_effect_ledger.audit.models import AuditLearningFile, AuditScenario
from lake_effect_ledger.commodity.models import (
    DocumentationQuality,
    FuturesContractSpec,
    MarketPricePath,
    PositionSide,
)
from lake_effect_ledger.learning.models import (
    GameMode,
    GameModeDefinition,
    GameModeFile,
    GlossaryFile,
    GlossaryTerm,
    KnowledgeCheckDefinition,
    PrologueFile,
    SourceReference,
    SourceReferenceFile,
    TrajectoryTag,
)
from lake_effect_ledger.state import Background, ResourceName, SkillProfile
from lake_effect_ledger.trading.models import (
    ChapterLearningFile,
    EleventhContractScenario,
    HedgeRecommendation,
    OrderType,
    RiskEmphasis,
    VolumeTreatment,
)
from lake_effect_ledger.treasury.models import (
    CharacterDefinition,
    CommunicationAccuracy,
    TreasuryScenarioDefinition,
)


class ResourceDeltaEffect(BaseModel):
    type: Literal["resource_delta"]
    target: ResourceName
    amount: int


class SetFlagEffect(BaseModel):
    type: Literal["set_flag"]
    target: str = Field(min_length=1)
    value: bool


class PostJournalEffect(BaseModel):
    type: Literal["post_journal"]
    template_id: str = Field(min_length=1)


class ScheduleEventEffect(BaseModel):
    type: Literal["schedule_event"]
    event_id: str = Field(min_length=1)
    due_in_days: int = Field(ge=0)


class AddInboxEffect(BaseModel):
    type: Literal["add_inbox"]
    item_id: str
    sender: str
    subject: str
    urgent: bool = False


class SetCommodityFieldEffect(BaseModel):
    type: Literal["set_commodity_field"]
    target: Literal["documentation_quality"]
    value: DocumentationQuality


class TrajectoryDeltaEffect(BaseModel):
    type: Literal["trajectory_delta"]
    target: TrajectoryTag
    amount: int = Field(ge=-3, le=3)

    @model_validator(mode="after")
    def reject_no_op(self) -> TrajectoryDeltaEffect:
        if self.amount == 0:
            raise ValueError("trajectory changes cannot be zero")
        return self


class RecordCommunicationEffect(BaseModel):
    type: Literal["record_communication"]
    record_id: str = Field(pattern=r"^[a-z0-9_]+$")
    channel: Literal["email", "phone", "teams", "none"]
    sender_id: str = Field(min_length=1)
    recipient_ids: list[str] = Field(min_length=1)
    subject: str = Field(min_length=1)
    body_summary: str = Field(min_length=1)
    accuracy: CommunicationAccuracy


class SetChapterFieldEffect(BaseModel):
    type: Literal["set_chapter_field"]
    target: Literal[
        "brief_volume_treatment",
        "brief_hedge_recommendation",
        "brief_risk_emphasis",
        "brief_asked_marisol",
        "recommended_order_type",
    ]
    value: str | bool

    @model_validator(mode="after")
    def validate_value(self) -> SetChapterFieldEffect:
        expected = {
            "brief_volume_treatment": {item.value for item in VolumeTreatment},
            "brief_hedge_recommendation": {item.value for item in HedgeRecommendation},
            "brief_risk_emphasis": {item.value for item in RiskEmphasis},
            "brief_asked_marisol": {True, False},
            "recommended_order_type": {item.value for item in OrderType},
        }[self.target]
        if self.value not in expected:
            raise ValueError(f"invalid value for chapter field {self.target}")
        return self


class SetChapterFlagEffect(BaseModel):
    type: Literal["set_chapter_flag"]
    target: str = Field(pattern=r"^[a-z0-9_]+$")
    value: bool


class RelationshipDeltaEffect(BaseModel):
    type: Literal["relationship_delta"]
    target: str = Field(pattern=r"^[a-z0-9_]+$")
    amount: int = Field(ge=-3, le=3)

    @model_validator(mode="after")
    def reject_no_op(self) -> RelationshipDeltaEffect:
        if self.amount == 0:
            raise ValueError("relationship changes cannot be zero")
        return self


Effect = Annotated[
    ResourceDeltaEffect
    | SetFlagEffect
    | PostJournalEffect
    | ScheduleEventEffect
    | AddInboxEffect
    | SetCommodityFieldEffect
    | TrajectoryDeltaEffect
    | RecordCommunicationEffect
    | SetChapterFieldEffect
    | SetChapterFlagEffect
    | RelationshipDeltaEffect,
    Field(discriminator="type"),
]
EFFECT_ADAPTER = TypeAdapter(Effect)


class ChoiceCondition(BaseModel):
    kind: Literal[
        "decision_made",
        "decision_not_made",
        "chapter_flag",
        "trajectory_min",
        "treasury_notification",
        "treasury_funding",
        "game_mode",
        "physical_outcome",
    ]
    target: str = Field(min_length=1)
    value: str | bool | int


class ChoiceDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    text: str = Field(min_length=1)
    effects: list[Effect]
    learning_objectives: list[str] = Field(min_length=1)
    retryable: Literal[False] = False
    conditions: list[ChoiceCondition] = Field(default_factory=list)


class ConditionalParagraph(BaseModel):
    text: str = Field(min_length=1)
    conditions: list[ChoiceCondition] = Field(min_length=1)


class DiscrepancyDefinition(BaseModel):
    metered_mmbtu: int = Field(gt=0)
    settlement_mmbtu: int = Field(gt=0)
    difference_mmbtu: int = Field(gt=0)
    index_price: Decimal = Field(gt=0)
    exposure: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def validate_reconciliation_math(self) -> DiscrepancyDefinition:
        if self.metered_mmbtu - self.settlement_mmbtu != self.difference_mmbtu:
            raise ValueError("discrepancy volume does not reconcile")
        if Decimal(self.difference_mmbtu) * self.index_price != self.exposure:
            raise ValueError("discrepancy exposure does not equal volume times index price")
        return self


class SceneDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    chapter: str
    speaker: str
    title: str
    text: str
    discrepancy: DiscrepancyDefinition | None = None
    conditional_paragraphs: list[ConditionalParagraph] = Field(default_factory=list)
    choices: list[ChoiceDefinition] = Field(min_length=1)


class SceneFile(BaseModel):
    schema_version: Literal[1]
    scenes: list[SceneDefinition]


class BackgroundDefinition(BaseModel):
    id: Background
    label: str
    description: str
    skills: SkillProfile
    personal_cash: Decimal = Field(ge=0)
    resource_adjustments: dict[ResourceName, int]


class CharacterFile(BaseModel):
    schema_version: Literal[1]
    backgrounds: list[BackgroundDefinition]
    people: list[CharacterDefinition] = Field(default_factory=list)


class JournalTemplate(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    description: str
    lines: list[JournalLine] = Field(min_length=2)


class JournalPattern(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    description: str
    debit_account: str = Field(pattern=r"^\d{4}$")
    credit_account: str = Field(pattern=r"^\d{4}$")


class JournalTemplateFile(BaseModel):
    schema_version: Literal[1]
    templates: list[JournalTemplate]
    patterns: list[JournalPattern] = Field(default_factory=list)


class ChartFile(BaseModel):
    schema_version: Literal[1]
    accounts: list[AccountDefinition]


class EventDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str
    text: str
    effects: list[Effect]


class EventFile(BaseModel):
    schema_version: Literal[1]
    events: list[EventDefinition]


class LessonDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    category: Literal["accounting", "controls", "natural_gas", "series_3"]
    title: str
    explanation: str


class LessonFile(BaseModel):
    schema_version: Literal[1]
    lessons: list[LessonDefinition]


class MarketScenario(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    label: str
    fictional: Literal[True]
    game_date: date
    henry_hub_base: Decimal = Field(gt=0)
    henry_hub_jitter_cents: int = Field(ge=0)
    chicago_basis_base: Decimal
    chicago_basis_jitter_cents: int = Field(ge=0)
    margin_due: Decimal = Field(ge=0)


class MarketFile(BaseModel):
    schema_version: Literal[1]
    scenarios: list[MarketScenario]


class CommodityContractFile(BaseModel):
    schema_version: Literal[1]
    contracts: list[FuturesContractSpec]


class CommodityPricePathFile(BaseModel):
    schema_version: Literal[1]
    price_paths: list[MarketPricePath]


class HedgeLevelDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    label: str
    hedge_ratio: Decimal = Field(ge=0)
    description: str


class HedgeScenarioDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    contract_id: str
    price_path_id: str
    price_path_ids: list[str] = Field(default_factory=list)
    physical_exposure_id: str = Field(pattern=r"^[a-z0-9_]+$")
    physical_quantity_mmbtu: Decimal = Field(gt=0)
    physical_direction: Literal["long"]
    regional_hub: str
    trade_date: date
    physical_settlement_date: date
    contract_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    futures_side: PositionSide
    initial_margin_per_contract: Decimal = Field(gt=0)
    maintenance_margin_per_contract: Decimal = Field(gt=0)
    minimum_operating_reserve: Decimal = Field(ge=0)
    hedge_levels: list[HedgeLevelDefinition] = Field(min_length=4)
    journal_patterns: dict[
        Literal[
            "initial_margin",
            "futures_gain",
            "futures_loss",
            "margin_call",
            "margin_release",
        ],
        str,
    ]
    learning_objectives: list[str] = Field(min_length=1)
    simplified_assumptions: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scenario_values(self) -> HedgeScenarioDefinition:
        if self.maintenance_margin_per_contract >= self.initial_margin_per_contract:
            raise ValueError("maintenance margin must be below initial margin")
        ratios = [level.hedge_ratio for level in self.hedge_levels]
        if len(ratios) != len(set(ratios)):
            raise ValueError("hedge levels contain duplicate ratios")
        if set(ratios) != {
            Decimal("0"),
            Decimal("0.5"),
            Decimal("1"),
            Decimal("1.5"),
        }:
            raise ValueError("hedge levels must provide 0%, 50%, 100%, and 150%")
        if self.price_path_ids and self.price_path_id not in self.price_path_ids:
            raise ValueError("default price path must be one of the selectable price paths")
        if len(self.price_path_ids) != len(set(self.price_path_ids)):
            raise ValueError("hedge scenario contains duplicate selectable price paths")
        return self

    @property
    def selectable_price_path_ids(self) -> list[str]:
        return self.price_path_ids or [self.price_path_id]


class HedgeScenarioFile(BaseModel):
    schema_version: Literal[1]
    scenarios: list[HedgeScenarioDefinition]


class HedgeBriefingScene(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    speaker: str
    title: str
    text: str


class HedgeNarrativeFile(BaseModel):
    schema_version: Literal[1]
    briefings: list[HedgeBriefingScene] = Field(min_length=3)
    documentation_scene: SceneDefinition


class TreasuryScenarioFile(BaseModel):
    schema_version: Literal[1]
    scenarios: list[TreasuryScenarioDefinition]


def _read_yaml(path: Path) -> object:
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


class ContentBundle:
    """Validated content plus cross-file reference checks."""

    def __init__(
        self,
        *,
        characters: CharacterFile,
        scenes: SceneFile,
        chart: ChartFile,
        journals: JournalTemplateFile,
        events: EventFile,
        lessons: LessonFile,
        markets: MarketFile,
        commodity_contracts: CommodityContractFile,
        commodity_price_paths: CommodityPricePathFile,
        hedge_scenarios: HedgeScenarioFile,
        hedge_narrative: HedgeNarrativeFile,
        treasury_scenarios: TreasuryScenarioFile,
        game_modes: GameModeFile,
        sources: SourceReferenceFile,
        glossary: GlossaryFile,
        prologue: PrologueFile,
        first_rotation: SceneFile,
        eleventh_scenario: EleventhContractScenario,
        eleventh_learning: ChapterLearningFile,
        eleventh_narrative: SceneFile,
        audit_scenario: AuditScenario,
        audit_learning: AuditLearningFile,
    ) -> None:
        self.characters = characters
        self.scenes = scenes
        self.chart = chart
        self.journals = journals
        self.events = events
        self.lessons = lessons
        self.markets = markets
        self.commodity_contracts = commodity_contracts
        self.commodity_price_paths = commodity_price_paths
        self.hedge_scenarios = hedge_scenarios
        self.hedge_narrative = hedge_narrative
        self.treasury_scenarios = treasury_scenarios
        self.game_modes = game_modes
        self.sources = sources
        self.glossary = glossary
        self.prologue = prologue
        self.first_rotation = first_rotation
        self.eleventh_scenario = eleventh_scenario
        self.eleventh_learning = eleventh_learning
        self.eleventh_narrative = eleventh_narrative
        self.audit_scenario = audit_scenario
        self.audit_learning = audit_learning
        self._validate_references()

    @classmethod
    def load(cls, root: Path) -> ContentBundle:
        return cls(
            characters=CharacterFile.model_validate(_read_yaml(root / "characters.yaml")),
            scenes=SceneFile.model_validate(_read_yaml(root / "chapters" / "episode_01.yaml")),
            chart=ChartFile.model_validate(
                _read_yaml(root / "accounting" / "chart_of_accounts.yaml")
            ),
            journals=JournalTemplateFile.model_validate(
                _read_yaml(root / "accounting" / "journal_templates.yaml")
            ),
            events=EventFile.model_validate(_read_yaml(root / "events" / "episode_01.yaml")),
            lessons=LessonFile.model_validate(_read_yaml(root / "lessons" / "episode_01.yaml")),
            markets=MarketFile.model_validate(
                _read_yaml(root / "market_scenarios" / "episode_01.yaml")
            ),
            commodity_contracts=CommodityContractFile.model_validate(
                _read_yaml(root / "commodity" / "contracts.yaml")
            ),
            commodity_price_paths=CommodityPricePathFile.model_validate(
                _read_yaml(root / "commodity" / "price_paths.yaml")
            ),
            hedge_scenarios=HedgeScenarioFile.model_validate(
                _read_yaml(root / "commodity" / "hedge_scenarios.yaml")
            ),
            hedge_narrative=HedgeNarrativeFile.model_validate(
                _read_yaml(root / "chapters" / "hedge_book.yaml")
            ),
            treasury_scenarios=TreasuryScenarioFile.model_validate(
                _read_yaml(root / "treasury" / "episode_01.yaml")
            ),
            game_modes=GameModeFile.model_validate(_read_yaml(root / "education" / "modes.yaml")),
            sources=SourceReferenceFile.model_validate(
                _read_yaml(root / "education" / "sources.yaml")
            ),
            glossary=GlossaryFile.model_validate(_read_yaml(root / "education" / "glossary.yaml")),
            prologue=PrologueFile.model_validate(
                _read_yaml(root / "education" / "first_rotation.yaml")
            ),
            first_rotation=SceneFile.model_validate(
                _read_yaml(root / "chapters" / "first_rotation.yaml")
            ),
            eleventh_scenario=EleventhContractScenario.model_validate(
                _read_yaml(root / "trading" / "eleventh_contract.yaml")
            ),
            eleventh_learning=ChapterLearningFile.model_validate(
                _read_yaml(root / "education" / "eleventh_contract.yaml")
            ),
            eleventh_narrative=SceneFile.model_validate(
                _read_yaml(root / "chapters" / "eleventh_contract.yaml")
            ),
            audit_scenario=AuditScenario.model_validate(
                _read_yaml(root / "audit" / "no_surprises.yaml")
            ),
            audit_learning=AuditLearningFile.model_validate(
                _read_yaml(root / "education" / "no_surprises.yaml")
            ),
        )

    @staticmethod
    def _unique(values: list[str], label: str) -> None:
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate {label} ID")

    def _validate_references(self) -> None:
        account_ids = [item.number for item in self.chart.accounts]
        template_ids = [item.id for item in self.journals.templates]
        pattern_ids = [item.id for item in self.journals.patterns]
        event_ids = [item.id for item in self.events.events]
        lesson_ids = [item.id for item in self.lessons.lessons]
        scene_ids = [
            *[item.id for item in self.scenes.scenes],
            self.hedge_narrative.documentation_scene.id,
            *[item.id for item in self.first_rotation.scenes],
            *[item.id for item in self.eleventh_narrative.scenes],
        ]
        background_ids = [item.id.value for item in self.characters.backgrounds]
        market_ids = [item.id for item in self.markets.scenarios]
        contract_ids = [item.id for item in self.commodity_contracts.contracts]
        price_path_ids = [item.id for item in self.commodity_price_paths.price_paths]
        hedge_scenario_ids = [item.id for item in self.hedge_scenarios.scenarios]
        briefing_ids = [item.id for item in self.hedge_narrative.briefings]
        person_ids = [item.id for item in self.characters.people]
        treasury_scenario_ids = [item.id for item in self.treasury_scenarios.scenarios]
        source_ids = [item.id for item in self.sources.sources]
        glossary_ids = [item.id for item in self.glossary.terms]
        prologue_check_ids = [item.id for item in self.prologue.checks]
        check_ids = [
            *prologue_check_ids,
            *[item.id for item in self.eleventh_learning.checks],
            *[item.id for item in self.audit_learning.checks],
        ]

        for values, label in (
            (account_ids, "account"),
            (template_ids, "journal template"),
            (pattern_ids, "journal pattern"),
            (event_ids, "event"),
            (lesson_ids, "lesson"),
            (scene_ids, "scene"),
            (background_ids, "background"),
            (market_ids, "market scenario"),
            (contract_ids, "commodity contract"),
            (price_path_ids, "commodity price path"),
            (hedge_scenario_ids, "hedge scenario"),
            (briefing_ids, "hedge briefing"),
            (person_ids, "character"),
            (treasury_scenario_ids, "treasury scenario"),
            (source_ids, "source"),
            (glossary_ids, "glossary term"),
            (check_ids, "knowledge check"),
        ):
            self._unique(values, label)

        valid_accounts = set(account_ids)
        valid_templates = set(template_ids)
        valid_patterns = set(pattern_ids)
        valid_events = set(event_ids)
        valid_lessons = set(lesson_ids)

        for template in self.journals.templates:
            unknown = {line.account for line in template.lines} - valid_accounts
            if unknown:
                raise ValueError(f"template {template.id} references unknown accounts: {unknown}")
            debits = sum((line.debit for line in template.lines), Decimal("0"))
            credits = sum((line.credit for line in template.lines), Decimal("0"))
            if debits != credits:
                raise ValueError(f"journal template {template.id} is unbalanced")

        for pattern in self.journals.patterns:
            unknown = {pattern.debit_account, pattern.credit_account} - valid_accounts
            if unknown:
                raise ValueError(
                    f"journal pattern {pattern.id} references unknown accounts: {unknown}"
                )
            if pattern.debit_account == pattern.credit_account:
                raise ValueError(f"journal pattern {pattern.id} uses the same account twice")

        choices = [
            *[choice for scene in self.scenes.scenes for choice in scene.choices],
            *self.hedge_narrative.documentation_scene.choices,
            *[choice for scene in self.first_rotation.scenes for choice in scene.choices],
            *[choice for scene in self.eleventh_narrative.scenes for choice in scene.choices],
        ]
        self._unique([choice.id for choice in choices], "choice")
        for choice in choices:
            missing_lessons = set(choice.learning_objectives) - valid_lessons
            if missing_lessons:
                raise ValueError(
                    f"choice {choice.id} references unknown lessons: {missing_lessons}"
                )
            self._validate_effects(choice.effects, choice.id, valid_templates, valid_events)
        audit_choices = [choice for scene in self.audit_scenario.scenes for choice in scene.choices]
        self._unique([choice.id for choice in audit_choices], "audit choice")
        for choice in audit_choices:
            missing_lessons = set(choice.learning_objective_ids) - valid_lessons
            if missing_lessons:
                raise ValueError(
                    f"audit choice {choice.id} references unknown lessons: {missing_lessons}"
                )
            unknown_people = set(choice.effect.relationship_deltas) - set(person_ids)
            if unknown_people:
                raise ValueError(
                    f"audit choice {choice.id} references unknown people: {unknown_people}"
                )
        communication_effects = [
            effect
            for choice in choices
            for effect in choice.effects
            if isinstance(effect, RecordCommunicationEffect)
        ]
        self._unique([item.record_id for item in communication_effects], "communication record")
        valid_people = set(person_ids)
        for effect in communication_effects:
            unknown_people = {
                effect.sender_id,
                *effect.recipient_ids,
            } - valid_people
            if unknown_people:
                raise ValueError(
                    f"communication {effect.record_id} references people {unknown_people}"
                )
        for choice in choices:
            for effect in choice.effects:
                if (
                    isinstance(effect, RelationshipDeltaEffect)
                    and effect.target not in valid_people
                ):
                    raise ValueError(
                        f"choice {choice.id} references unknown relationship target {effect.target}"
                    )
            for condition in choice.conditions:
                if condition.kind == "trajectory_min":
                    try:
                        TrajectoryTag(condition.target)
                    except ValueError as error:
                        raise ValueError(
                            f"choice {choice.id} references unknown career tag {condition.target}"
                        ) from error
        for scene in self.eleventh_narrative.scenes:
            for paragraph in scene.conditional_paragraphs:
                for condition in paragraph.conditions:
                    if condition.kind == "trajectory_min":
                        try:
                            TrajectoryTag(condition.target)
                        except ValueError as error:
                            raise ValueError(
                                f"scene {scene.id} references unknown career tag {condition.target}"
                            ) from error

        valid_sources = set(source_ids)
        valid_glossary = set(glossary_ids)
        valid_checks = set(check_ids)
        for term in self.glossary.terms:
            missing_lessons = set(term.learning_objective_ids) - valid_lessons
            missing_sources = set(term.source_ids) - valid_sources
            if missing_lessons or missing_sources:
                raise ValueError(
                    f"glossary term {term.id} has invalid references: "
                    f"lessons={missing_lessons}, sources={missing_sources}"
                )
        for check in [
            *self.prologue.checks,
            *self.eleventh_learning.checks,
            *self.audit_learning.checks,
        ]:
            missing_lessons = set(check.learning_objective_ids) - valid_lessons
            if missing_lessons or check.source_id not in valid_sources:
                raise ValueError(
                    f"knowledge check {check.id} has invalid learning/source references"
                )
            if check.calculation is not None:
                contract_id = check.calculation.contract_id
                if contract_id is not None and contract_id not in contract_ids:
                    raise ValueError(
                        f"knowledge check {check.id} references unknown contract {contract_id}"
                    )
        prologue_day_ids: list[str] = []
        for day in self.prologue.prologue.days:
            missing_checks = set(day.check_ids) - valid_checks
            if missing_checks:
                raise ValueError(f"prologue day {day.id} references checks {missing_checks}")
            prologue_day_ids.extend(day.check_ids)
            for panel in day.concept_panels:
                if set(panel.learning_objective_ids) - valid_lessons:
                    raise ValueError(f"concept panel {panel.id} references unknown lessons")
                if set(panel.glossary_ids) - valid_glossary:
                    raise ValueError(f"concept panel {panel.id} references unknown glossary terms")
            if day.story_scene_id is not None and day.story_scene_id not in scene_ids:
                raise ValueError(f"prologue day {day.id} references unknown story scene")
        if len(prologue_day_ids) != len(set(prologue_day_ids)):
            raise ValueError("a prologue check appears in more than one day")
        if set(prologue_day_ids) != set(prologue_check_ids):
            raise ValueError("every prologue check must appear in exactly one day")
        if self.prologue.prologue.episode_1_transition_scene_id not in scene_ids:
            raise ValueError("prologue transition references an unknown scene")
        if "eleventh_episode_transition" not in scene_ids:
            raise ValueError("missing Episode 1 to Episode 2 transition")
        if len(self.audit_scenario.scenes) < 10:
            raise ValueError("No Surprises requires at least ten durable decisions")
        durable_chapter_scenes = [
            scene
            for scene in self.eleventh_narrative.scenes
            if scene.id != "eleventh_episode_transition"
        ]
        if len(durable_chapter_scenes) < 8:
            raise ValueError("The Eleventh Contract requires at least eight decisions")
        if self.eleventh_scenario.contract_id not in contract_ids:
            raise ValueError(
                f"Eleventh Contract references unknown contract "
                f"{self.eleventh_scenario.contract_id}"
            )
        valid_people = set(person_ids)
        if {
            self.eleventh_scenario.approver_id,
            self.eleventh_scenario.transmitting_user_id,
        } - valid_people:
            raise ValueError("Eleventh Contract references unknown authorized people")
        if self.audit_scenario.id != "no_surprises":
            raise ValueError("missing transition from The Eleventh Contract to No Surprises")
        if any(
            item.stable_record_id not in self.audit_expected_record_ids
            for item in self.audit_scenario.request_specs
        ):
            raise ValueError("audit request references a nonexistent Eleventh Contract record")

        for event in self.events.events:
            self._validate_effects(event.effects, event.id, valid_templates, valid_events)

        contracts = {item.id: item for item in self.commodity_contracts.contracts}
        price_paths = {item.id: item for item in self.commodity_price_paths.price_paths}
        for scenario in self.hedge_scenarios.scenarios:
            if scenario.contract_id not in contracts:
                raise ValueError(
                    f"hedge scenario {scenario.id} references unknown contract "
                    f"{scenario.contract_id}"
                )
            for path_id in scenario.selectable_price_path_ids:
                if path_id not in price_paths:
                    raise ValueError(
                        f"hedge scenario {scenario.id} references unknown price path {path_id}"
                    )
                path = price_paths[path_id]
                if scenario.trade_date != path.initial_market.settlement_date:
                    raise ValueError(f"hedge scenario {scenario.id} trade date does not match path")
                if scenario.physical_settlement_date != path.settlements[-1].settlement_date:
                    raise ValueError(
                        f"hedge scenario {scenario.id} physical date does not "
                        "match final settlement"
                    )
            missing_patterns = set(scenario.journal_patterns.values()) - valid_patterns
            if missing_patterns:
                raise ValueError(
                    f"hedge scenario {scenario.id} references unknown journal patterns: "
                    f"{missing_patterns}"
                )
            missing_lessons = set(scenario.learning_objectives) - valid_lessons
            if missing_lessons:
                raise ValueError(
                    f"hedge scenario {scenario.id} references unknown lessons: {missing_lessons}"
                )
            contract = contracts[scenario.contract_id]
            for level in scenario.hedge_levels:
                contracts_required = (
                    scenario.physical_quantity_mmbtu
                    * level.hedge_ratio
                    / contract.contract_size_mmbtu
                )
                if contracts_required != contracts_required.to_integral_value():
                    raise ValueError(
                        f"hedge level {level.id} does not produce a whole contract count"
                    )

        for scenario in self.treasury_scenarios.scenarios:
            referenced_patterns = {
                *scenario.journal_patterns.values(),
                *(item.journal_pattern_id for item in scenario.obligations),
            }
            missing_patterns = referenced_patterns - valid_patterns
            if missing_patterns:
                raise ValueError(
                    f"treasury scenario {scenario.id} references unknown journal patterns: "
                    f"{missing_patterns}"
                )
            missing_lessons = set(scenario.learning_objectives) - valid_lessons
            if missing_lessons:
                raise ValueError(
                    f"treasury scenario {scenario.id} references unknown lessons: {missing_lessons}"
                )
            required_people = {
                *scenario.facility.required_approver_ids,
                *(
                    person_id
                    for option in scenario.notification_options
                    for person_id in [option.sender_id, *option.recipient_ids]
                ),
            }
            missing_people = required_people - valid_people
            if missing_people:
                raise ValueError(
                    f"treasury scenario {scenario.id} references unknown characters: "
                    f"{missing_people}"
                )

    @staticmethod
    def _validate_effects(
        effects: list[Effect],
        source_id: str,
        valid_templates: set[str],
        valid_events: set[str],
    ) -> None:
        for effect in effects:
            if isinstance(effect, PostJournalEffect) and effect.template_id not in valid_templates:
                raise ValueError(
                    f"{source_id} references unknown journal template {effect.template_id}"
                )
            if isinstance(effect, ScheduleEventEffect) and effect.event_id not in valid_events:
                raise ValueError(f"{source_id} references unknown event {effect.event_id}")

    def background(self, background: Background) -> BackgroundDefinition:
        return next(item for item in self.characters.backgrounds if item.id == background)

    def scene(self, scene_id: str) -> SceneDefinition:
        if self.hedge_narrative.documentation_scene.id == scene_id:
            return self.hedge_narrative.documentation_scene
        return next(
            item
            for item in [
                *self.scenes.scenes,
                *self.first_rotation.scenes,
                *self.eleventh_narrative.scenes,
            ]
            if item.id == scene_id
        )

    def journal_template(self, template_id: str) -> JournalTemplate:
        return next(item for item in self.journals.templates if item.id == template_id)

    def journal_pattern(self, pattern_id: str) -> JournalPattern:
        return next(item for item in self.journals.patterns if item.id == pattern_id)

    def event(self, event_id: str) -> EventDefinition:
        return next(item for item in self.events.events if item.id == event_id)

    def lesson(self, lesson_id: str) -> LessonDefinition:
        return next(item for item in self.lessons.lessons if item.id == lesson_id)

    def hedge_scenario(self, scenario_id: str) -> HedgeScenarioDefinition:
        return next(item for item in self.hedge_scenarios.scenarios if item.id == scenario_id)

    def commodity_contract(self, contract_id: str) -> FuturesContractSpec:
        return next(item for item in self.commodity_contracts.contracts if item.id == contract_id)

    def commodity_price_path(self, path_id: str) -> MarketPricePath:
        return next(item for item in self.commodity_price_paths.price_paths if item.id == path_id)

    def treasury_scenario(self, scenario_id: str) -> TreasuryScenarioDefinition:
        return next(item for item in self.treasury_scenarios.scenarios if item.id == scenario_id)

    def game_mode(self, game_mode: GameMode) -> GameModeDefinition:
        return next(item for item in self.game_modes.modes if item.id == game_mode)

    def knowledge_check(self, check_id: str) -> KnowledgeCheckDefinition:
        return next(
            item
            for item in [
                *self.prologue.checks,
                *self.eleventh_learning.checks,
                *self.audit_learning.checks,
            ]
            if item.id == check_id
        )

    def audit_scene(self, scene_id: str):
        return next(item for item in self.audit_scenario.scenes if item.id == scene_id)

    def glossary_term(self, term_id: str) -> GlossaryTerm:
        return next(item for item in self.glossary.terms if item.id == term_id)

    def source(self, source_id: str) -> SourceReference:
        return next(item for item in self.sources.sources if item.id == source_id)

    @property
    def valid_accounts(self) -> set[str]:
        return {item.number for item in self.chart.accounts}

    @property
    def audit_expected_record_ids(self) -> set[str]:
        """Stable IDs the audit request may resolve from a completed v5 chapter."""
        return {
            "forecast_live_week_2028",
            "brief_live_week_2028",
            "recommendation_live_week",
            "auth_live_week_ten_short",
            "order_live_week_ten_short",
            "execution_live_week_eleven",
            "fcm_confirmation_live_week_eleven",
            "blotter_eleventh_contract",
            "reconciliation_eleventh_contract",
            "txn_eleventh_initial_margin",
            "comm_ec_formal_exception",
            "approval_offset_eleventh_contract",
            "offset_eleventh_contract",
            "final_nomination_additional_10000",
            "comm_eleventh_market_brief",
            "analyst_case_file_eleventh_contract",
        }
