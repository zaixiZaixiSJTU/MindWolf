from ..models.memory import MemoryPool as Pool, MemoryUnit
from ..agent.lying_engine import LieLedgerManager


class MemoryPool(Pool):
    """Extended MemoryPool with integration hooks for lie ledger."""
    def __init__(self):
        super().__init__()
        self._lie_ledger: LieLedgerManager | None = None

    def set_lie_ledger(self, ledger: LieLedgerManager) -> None:
        self._lie_ledger = ledger

    def check_contradictions(self, player_id: int, new_units: list[MemoryUnit]) -> int:
        """Cross-check new events against lie ledger. Returns contradiction count."""
        if self._lie_ledger is None:
            return 0
        count = 0
        for unit in new_units:
            if unit.event_type == "claim_role":
                claimed = unit.content
                existing_claims = self._lie_ledger.get_claimed_role(player_id)
                if existing_claims and str(existing_claims.value) not in claimed:
                    contras = self._lie_ledger.check_contradiction(
                        player_id, {"claimed_role": claimed}
                    )
                    if contras:
                        self.mark_contradiction(unit.id)
                        count += 1
        return count

    def get_recent_events(self, n: int = 10) -> list[MemoryUnit]:
        return sorted(self.units, key=lambda u: (u.round, u.current_weight), reverse=True)[:n]
