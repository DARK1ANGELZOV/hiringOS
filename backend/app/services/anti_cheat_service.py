from dataclasses import dataclass
from uuid import UUID

from app.models.enums import AntiCheatRiskLevel, AntiCheatSeverity
from app.repositories.interview_repository import InterviewRepository


SEVERITY_WEIGHT = {
    AntiCheatSeverity.LOW: 1.0,
    AntiCheatSeverity.MEDIUM: 2.0,
    AntiCheatSeverity.HIGH: 3.0,
    AntiCheatSeverity.CRITICAL: 4.5,
}

SIGNAL_MULTIPLIER = {
    'focus_blur': 1.0,
    'tab_switch': 1.1,
    'paste_burst': 1.5,
    'typing_anomaly': 1.2,
    'ide_behavior': 1.3,
    'plagiarism': 2.0,
    'session_anomaly': 1.8,
    'voice_anomaly': 1.6,
}


@dataclass
class AntiCheatService:
    repository: InterviewRepository

    async def collect_signal(
        self,
        *,
        session_id: UUID,
        signal_type: str,
        severity: AntiCheatSeverity,
        value_json: dict,
    ):
        signal = await self.repository.create_signal(
            session_id=session_id,
            signal_type=signal_type,
            severity=severity,
            value_json=value_json,
        )
        await self.repository.create_event(
            session_id=session_id,
            event_type='anti_cheat_signal_received',
            payload_json={
                'signal_id': str(signal.id),
                'signal_type': signal_type,
                'severity': severity.value,
                'value_json': value_json,
            },
        )
        return signal

    async def aggregate_signals(self, session_id: UUID) -> tuple[float, AntiCheatRiskLevel]:
        session = await self.repository.get_session(session_id)
        signals = await self.repository.list_signals(session_id, limit=1000)

        total = 0.0
        for signal in signals:
            severity_weight = SEVERITY_WEIGHT.get(signal.severity, 1.0)
            multiplier = SIGNAL_MULTIPLIER.get(signal.signal_type, 1.0)
            total += severity_weight * multiplier

        normalized = min(total / 12.0, 100.0)
        risk = self._risk_level(normalized)

        if session:
            session.anti_cheat_score = round(normalized, 2)
            session.anti_cheat_level = risk
            await self.repository.db.flush()

        return round(normalized, 2), risk

    async def evaluate_risk(self, session_id: UUID) -> list[dict]:
        signals = await self.repository.list_signals(session_id, limit=200)
        flags: list[dict] = []

        for signal in signals[:30]:
            if signal.severity in {AntiCheatSeverity.HIGH, AntiCheatSeverity.CRITICAL}:
                flags.append(
                    {
                        'signal_type': signal.signal_type,
                        'severity': signal.severity.value,
                        'at': signal.created_at.isoformat(),
                        'details': signal.value_json,
                    }
                )

        return flags

    async def attach_risk_to_report(self, session_id: UUID, report_payload: dict) -> dict:
        score, risk_level = await self.aggregate_signals(session_id)
        flags = await self.evaluate_risk(session_id)
        report_payload['anti_cheat'] = {
            'score': score,
            'risk_level': risk_level.value,
            'flags': flags,
        }
        return report_payload

    @staticmethod
    def _risk_level(score: float) -> AntiCheatRiskLevel:
        if score < 25:
            return AntiCheatRiskLevel.LOW
        if score < 50:
            return AntiCheatRiskLevel.MEDIUM
        if score < 75:
            return AntiCheatRiskLevel.HIGH
        return AntiCheatRiskLevel.CRITICAL
