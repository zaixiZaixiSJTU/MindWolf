from __future__ import annotations

from ..models.enums import Role, Faction, Phase, WEREWOLF_ROLES
from ..models.schemas import Player, GameState

TERMINOLOGY = """
【狼人杀术语】
- 金水 = 预言家查验出的好人
- 查杀 = 预言家查验出的狼人
- 银水 = 女巫救起的人
- 悍跳 = 狼人伪装成神职（通常是伪装预言家）
- 对跳 = 两名玩家声称同一神职
- 退水 = 声明放弃之前声称的身份
- 倒钩狼 = 攻击队友以洗白自己的狼人
- 深水狼 = 全程低调的狼人
- 表水 = 被怀疑时解释自己的行为
"""

ROLE_GOALS = {
    Role.WEREWOLF: "消灭所有神职或所有村民。伪装成好人，避免被投票出局。夜晚与狼队友协商刀杀目标。",
    Role.SEER: "每晚查验一名玩家的阵营。将查验结果（金水/查杀）传达给好人，引导投票。",
    Role.WITCH: "你有一瓶解药和一瓶毒药。解药可救活夜间死者，毒药可毒杀任意玩家。合理用药帮助好人阵营。",
    Role.HUNTER: "你死亡时可以开枪带走一名玩家（被毒杀则不能开枪）。找出狼人并引导投票。",
    Role.IDIOT: "你没有夜间技能。被投票出局时可以亮明身份继续发言但失去投票权。帮助好人找出狼人。",
    Role.VILLAGER: "你没有特殊技能。仔细聆听发言，找出逻辑漏洞，投票放逐狼人。",
    Role.GUARD: "每晚守护一名玩家免于狼刀（不可连续守同一人）。保护关键神职。",
    Role.WHITE_WOLF: "你是狼人阵营。被放逐时可自爆带走一名玩家。与狼队友配合。",
}


class PromptBuilder:
    def __init__(self):
        self.terminology = TERMINOLOGY

    def build_system_prompt(
        self, player: Player, state: GameState, memory_text: str = "",
    ) -> str:
        role_goal = ROLE_GOALS.get(player.role, "找出狼人并投票放逐他们。")

        parts = [
            f"# 角色扮演",
            f"你是 {player.name} (ID: {player.id})。你的身份是 **{player.role.value}**。",
            f"你的阵营是 **{player.faction.value}**。",
            f"你的目标：{role_goal}",
            "",
            f"# 术语知识",
            self.terminology,
            "",
            f"# 当前局面",
            f"第 {state.round} 轮 | 当前阶段：{state.phase.value}",
            f"存活玩家：{state.get_alive_ids()}",
            f"警长：{state.sheriff_id or '无'}",
            self._format_night_results(state),
            "",
            f"# 记忆",
            memory_text or "[无重要记忆]",
            "",
            f"# 你的活着的队友",
            self._format_teammates(player, state),
        ]

        if player.role in WEREWOLF_ROLES:
            parts.append(self._lying_hint(player))

        if player.role == Role.SEER:
            parts.append(self._seer_hint())
        elif player.role == Role.WITCH:
            parts.append(self._witch_hint(player))

        parts.extend([
            "",
            "# 输出格式 (必须严格遵守，每个标签都必须包含)",
            "<thinking>",
            "1. 局面分析",
            "2. 他人动机推理",
            "3. 策略选择与理由",
            "4. 概率估计: {玩家ID: \"70% Wolf\", ...}",
            "</thinking>",
            "<speak>你的公开发言</speak>",
            "<vote>目标玩家ID，如 8。在投票阶段必须投票，不能填 NONE。</vote>",
            "<action>技能名:目标ID 或 NONE</action>",
            "",
            "重要提醒：",
            "- 投票阶段（DAY_VOTE）必须选择一名存活玩家投票，<vote>标签内只能填数字ID（如 8），不可填 NONE。",
            "- 如果跳了预言家，<speak>中必须包含\"我是预言家，昨晚查验了X号，结果是金水/查杀\"。",
        ])

        return "\n".join(parts)

    def _format_night_results(self, state: GameState) -> str:
        """Public night announcement — only reveals who died, not cause.
        (Wolves/witch/seer get their private knowledge via extra_info.)"""
        if not state.night_results:
            return "尚无夜间结果。"
        last = state.night_results[-1]

        # Collect actual deaths (wolf kill not saved, or poison)
        dead_ids: list[int] = []
        if last.killed_player and last.killed_player != last.saved_player:
            dead_ids.append(last.killed_player)
        if last.poisoned_player:
            dead_ids.append(last.poisoned_player)

        if not dead_ids:
            return "昨夜是平安夜，无人死亡。"
        names = "、".join(f"{pid}号" for pid in dead_ids)
        return f"昨夜{names}玩家死亡。（死因不明，可能是狼刀或毒杀。）"

    def _format_teammates(self, player: Player, state: GameState) -> str:
        if player.role in WEREWOLF_ROLES:
            mates = [
                p.id for p in state.players
                if p.is_alive and p.role in WEREWOLF_ROLES and p.id != player.id
            ]
            return f"狼队友: {mates}" if mates else "你是最后一只狼。"
        return "你与所有好人是队友。确认的神职信息会在发言中公开。"

    def _lying_hint(self, player: Player) -> str:
        return (
            "\n# 谎言策略提示\n"
            "作为狼人，你可以选择以下策略：\n"
            "- **悍跳预言家 (SEER_CLAIM)**: 冒充预言家，给狼队友发金水或给好人发查杀\n"
            "- **倒钩 (DEEP_COVER)**: 攻击狼队友来洗白自己\n"
            "- **煽动 (INSTIGATE)**: 煽动好人之间互相怀疑\n"
            "- **深水 (SILENT_DEEP)**: 保持低调，不引人注目\n"
            "- **穿神衣服 (ROLE_CLAIM)**: 声称自己是女巫/猎人等神职\n"
            "注意：你的谎言必须前后一致！曾经声称过的事情不要轻易推翻。"
        )

    def _seer_hint(self) -> str:
        return "\n# 查验建议\n你必须在发言中如实公布查验结果。用术语：查验为好人是'金水'，查验为狼人是'查杀'。"

    def _witch_hint(self, player: Player) -> str:
        skills = player.skill_available
        hints = ["\n# 女巫技能状态"]
        if skills.get("antidote"):
            hints.append("- 解药可用：可以救活夜间狼刀死者")
        else:
            hints.append("- 解药已使用")
        if skills.get("poison"):
            hints.append("- 毒药可用：可以毒杀任意玩家（被毒者直接死亡）")
        else:
            hints.append("- 毒药已使用")
        return "\n".join(hints)
