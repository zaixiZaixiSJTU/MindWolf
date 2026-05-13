这份文档是专门为 **Cursor / Windsurf / GitHub Copilot** 等 AI 编程助手设计的"工程实施指令集"。它将你的构思转化为机器可理解的模块化任务，并定义了严格的数据结构，以防止 AI 在编写过程中出现逻辑漂移。

---

# 🐺 AI 狼人杀·多智能体博弈系统 (SJM-Werewolf) 开发规约

## 1. 项目概况

### 1.1 核心命题

构建一个基于 **多 Agent 协作框架（Agent Team）** 的狼人杀博弈系统。每个 Agent 根据其扮演角色（狼人、预言家、女巫等）拥有**独立的目标、策略与行动空间**，在**严格信息隔离**的约束下进行推理、发言与决策。

核心挑战在于**多智能体的协作/对抗与交互机制设计**：
- **信息不对称**：狼人互知身份，好人对他人一无所知；每个 Agent 仅能观测到公开发言和自身夜间行动结果
- **策略欺骗**：狼人 Agent 必须学会伪装、悍跳、倒钩等欺骗行为；好人 Agent 需从发言中识别谎言
- **动态博弈**：每局的角色分配、发言顺序、投票结果均在变化，Agent 无法依赖固定策略
- **思维链可视化**：所有 Agent 的推理过程（`<thinking>`）需实时外显，构成系统的核心竞争力

### 1.2 运行模式

| 模式 | 描述 |
|------|------|
| **纯 AI 对战** | 12名 Agent 全部由 LLM 驱动，全自动完成一局对弈 |
| **人机混战** | 人类玩家通过 Web UI 加入对局，与 AI Agent 同台竞技 |
| **观战模式** | 人类以旁观者身份观看纯 AI 对战，实时查看所有角色身份和思维链 |

### 1.3 参考项目与论文

- [KylJin/Werewolf](https://github.com/KylJin/Werewolf) — RL-instructed LLM Agent 框架，含信念建模与策略选择
- [Mai0313/LLMWereWolf](https://github.com/Mai0313/LLMWereWolf) — 模块化 Mixin 架构，支持20+角色与多LLM后端
- [MiniMax-OpenPlatform/minimax-werewolf](https://github.com/MiniMax-OpenPlatform/minimax-werewolf) — MiniMax AI 驱动狼人杀框架
- [nejumi/LLM_Werewolf_Game](https://github.com/nejumi/LLM_Werewolf_Game) — LLM狼人杀参考
- 学术论文: *WOLF: Werewolf-based Observations for LLM Deception and Falsehoods* (arXiv:2512.09187)
- 学术论文: *WereWolf-Plus: An Update of Werewolf Game setting Based on DSGBench* (arXiv:2506.12841)
- 学术论文: *Learning Strategic Language Agents in the Werewolf Game with Iterative Latent Space Policy Optimization* (ICML 2025)

### 1.4 三大进阶方向（三选一）

| 方向 | 核心目标 | 关键技术点 |
|------|----------|-----------|
| **① 通用 Agent — 自演化系统** | 探索"读懂自己→修改自己→运行自己"的闭环，从通用 Agent 演化为狼人杀多角色专家 Agent | Prompt 自优化、策略代码自生成、Sandbox 安全执行 |
| **② 评测 + 复盘 + Leaderboard** | 构建多维可量化评测体系，支持任意游戏复盘归因，产出不同版本/模型 Agent 的竞技排行榜 | 结果评测（胜率、存活轮次等）+ 过程评测（逻辑一致性、谎言收益等）；自动复盘报告生成；ELO/Glicko 排名 |
| **③ 自进化 Agent** | 实现"对局→分析→优化→再对局"自进化循环，使各角色 Agent 在多局迭代中持续提升胜率 | 对局经验记忆库、失败归因分析、Prompt/策略自动调优、A/B 对照测试 |

## 2. 技术栈约束

* **后端**: Python 3.10+ / FastAPI (异步优先)
* **通信**: WebSocket (实现实时发言流)
* **大模型**: OpenAI 兼容协议 (DeepSeek-V3 / 豆包 / GPT-4o / Qwen)
* **前端**: React + Tailwind CSS + Lucide Icons
* **数据结构**: Pydantic (后端) + TypeScript Interfaces (前端)

---

## 3. 狼人杀游戏规则与术语 (Domain Knowledge)

### 3.1 游戏概述

狼人杀是一款**社交推理博弈**游戏。玩家分为两大阵营：
- **好人阵营 (Villager Faction)**：村民 + 神职，目标是找出并放逐所有狼人
- **狼人阵营 (Werewolf Faction)**：目标是存活至狼人数量 ≥ 好人数量（屠边局）

### 3.2 标准12人局·预女猎白 (经典板子)

| 阵营 | 角色 | 人数 | 技能 |
|------|------|------|------|
| 狼人 | 普通狼人 (Werewolf) | 4 | 每晚可刀杀一名玩家 |
| 神职 | 预言家 (Seer) | 1 | 每晚查验一名玩家的阵营（好人/狼人） |
| 神职 | 女巫 (Witch) | 1 | 拥有一瓶解药（救活夜间死者）和一瓶毒药（毒杀任意玩家），**不可自救**（视规则） |
| 神职 | 猎人 (Hunter) | 1 | 死亡时可开枪带走一名玩家（被毒杀则不能开枪） |
| 神职 | 白痴 (Idiot) | 1 | 被放逐投票出局时亮明身份，可继续发言但失去投票权 |
| 村民 | 普通村民 (Villager) | 4 | 无特殊技能，仅白天投票 |

**胜负条件（屠边局）**：
- 好人阵营：放逐所有狼人
- 狼人阵营：杀光所有神职 OR 杀光所有村民

### 3.3 游戏流程 (完整阶段机)

```
PRE_GAME (准备)
  ├─ 随机分配角色
  └─ 每个玩家获知自己的身份
       ↓
NIGHT 回合循环
  ├─ NIGHT_WEREWOLF  (狼人刀人)     —— 狼人互认，协商击杀目标
  ├─ NIGHT_SEER       (预言家查验)   —— 查验任意玩家的阵营
  ├─ NIGHT_WITCH      (女巫用药)     —— 得知夜间死者，决定救/毒/不用药
  ├─ NIGHT_HUNTER     (猎人确认)     —— 仅确认开枪状态（非主动阶段）
  ├─ NIGHT_GUARD      (守卫守护)  —— 守护一名玩家免于狼刀（如启用守卫板）
       ↓
DAY 回合循环
  ├─ DAY_ANNOUNCE     (天亮公布)     —— 公布夜间死亡信息
  ├─ DAY_DISCUSS      (白天讨论)     —— 按顺序发言/自由发言，含警长归票
  └─ DAY_VOTE         (放逐投票)     —— 投票放逐一名玩家，平票则平安日
       ↓
  GOTO NIGHT (若未达到胜利条件)
       ↓
GAME_OVER
  └─ 判定胜负，公布所有角色身份
```

**夜晚行动顺序**（法官唤醒顺序）：
1. 守卫（如启用）
2. 狼人 → 击杀目标
3. 女巫 → 得知死者，选择救/毒/不行动
4. 预言家 → 查验一名玩家身份
5. 猎人 → 确认开枪状态

### 3.4 狼人杀核心术语 (Glossary)

**身份相关**：
| 术语 | 含义 |
|------|------|
| 金水 | 预言家查验出的"好人"身份 |
| 查杀 | 预言家查验出的"狼人"身份 |
| 银水 | 女巫救活的人（被狼刀但被解药救起） |
| 铜水 | 被守卫守护而免于死亡的人 |
| 悍跳 | 狼人伪装成神职（通常指伪装预言家） |
| 对跳 | 两名玩家声称同一神职身份 |
| 退水 | 声明放弃之前声称的身份 |

**游戏流程相关**：
| 术语 | 含义 |
|------|------|
| 警长 (警徽) | 第一天由选举产生（可选规则），拥有1.5票归票权，死亡时可将警徽移交他人 |
| 警徽流 | 预言家在死前布置查验顺序，通过移交警徽传递查验结果（未查验者无信息） |
| 归票 | 警长/发言者在投票阶段号召统一投某人的行为 |
| 平安夜 | 无夜间死亡的夜晚（女巫救人/守卫守对人） |
| 屠边 | 杀光所有神职或所有村民的胜利方式 |
| 首刀 | 第一晚狼人选定的击杀目标 |
| 自刀 | 狼人自杀（通常为骗取女巫解药或做高身份） |
| 冲票 | 狼人集体投一个人 |
| 绑票 | 狼人票数足以左右投票结果 |
| 表水 | 被怀疑时解释自己的行为，表明好人身份 |
| 穿衣服 | 声称自己是某神职身份 |

**策略相关**：
| 术语 | 含义 |
|------|------|
| 倒钩狼 | 狼人伪装成好人对队友进行攻击来洗白自己 |
| 深水狼 | 全程低调不引人注目的狼人 |
| 煽动狼 | 在发言中煽动好人互打的狼人 |
| 金刚狼 | 永远不被怀疑的狼人（通常是被预言家发了金水的狼人） |
| 场外 | 与游戏逻辑无关的信息（本项目不涉及） |

### 3.5 扩展角色池 (可扩展板子)

| 扩展角色 | 阵营 | 技能描述 |
|----------|------|----------|
| 守卫 (Guard) | 神职 | 每晚选择一名玩家守护，被守护者免疫狼刀（不可连续守同一人） |
| 白狼王 (WhiteWolf) | 狼人 | 被放逐时可自爆带走一名玩家（带走的神职无法发动技能） |
| 狼美人 (WolfBeauty) | 狼人 | 每晚可魅惑一名玩家，若自己被放逐则魅惑对象一并死亡 |
| 狼巫 (AlphaWolf) | 狼人 | 可查验一名玩家的具体神职身份 |
| 恶灵骑士 (NightmareWolf) | 狼人 | 免疫女巫毒药，且女巫毒杀自身时反弹伤害 |
| 丘比特 (Cupid) | 第三方 | 首夜指定两名玩家为情侣（不为同阵营时组成第三方） |
| 盗贼 (Thief) | 中立 | 首夜从两张替补角色中选择一张，另一张作废 |
| 乌鸦 (Raven) | 神职 | 每晚可标记一名玩家，被标记者在投票中多计一票 |
| 骑士 (Knight) | 神职 | 白天可随时翻牌与一名玩家决斗，若对方是狼则狼死，否则自己死 |
| 守墓人 (GraveyardKeeper) | 神职 | 每晚可查验前一天被放逐者的阵营 |

---

## 4. 核心数据模型 (Schema)

*请要求 Coding 模型严格遵守以下字段定义：*

```python
# 角色枚举
from enum import Enum

class Faction(str, Enum):
    VILLAGER = "VILLAGER"   # 好人阵营
    WEREWOLF = "WEREWOLF"   # 狼人阵营
    THIRD_PARTY = "THIRD_PARTY"  # 第三方（情侣等）

class Role(str, Enum):
    WEREWOLF = "WEREWOLF"
    VILLAGER = "VILLAGER"
    SEER = "SEER"
    WITCH = "WITCH"
    HUNTER = "HUNTER"
    IDIOT = "IDIOT"
    GUARD = "GUARD"          # 守卫（扩展）
    WHITE_WOLF = "WHITE_WOLF"  # 白狼王（扩展）

class Phase(str, Enum):
    PRE_GAME = "PRE_GAME"
    NIGHT_WEREWOLF = "NIGHT_WEREWOLF"
    NIGHT_SEER = "NIGHT_SEER"
    NIGHT_WITCH = "NIGHT_WITCH"
    NIGHT_HUNTER = "NIGHT_HUNTER"
    DAY_ANNOUNCE = "DAY_ANNOUNCE"
    DAY_DISCUSS = "DAY_DISCUSS"
    DAY_VOTE = "DAY_VOTE"
    GAME_OVER = "GAME_OVER"

# 玩家状态
class Player(BaseModel):
    id: int
    name: str
    role: Role
    faction: Faction
    is_alive: bool = True
    can_vote: bool = True
    has_used_skill: bool = False      # 女巫是否已用药、守卫是否已守人等
    skill_available: Dict[str, bool]  # {"antidote": True, "poison": True}
    suspicion_score: Dict[int, float]  # 对其他人的可疑度建模
    revealed_role: Optional[Role] = None  # 出局后亮明的身份

# 游戏动作 (Agent -> GM)
class GameAction(BaseModel):
    player_id: int
    phase: Phase
    thinking: str          # CoT 思考内容（核心可视化）
    speech: str            # 公开对白
    vote_target: Optional[int]
    skill_target: Optional[int]
    skill_name: Optional[str]   # "antidote", "poison", "check", "guard", "shoot"
    lie_plan: Optional[Dict]    # 记录本轮是否撒谎及谎言类型
    belief_state: Optional[Dict[int, Dict[str, float]]]  # 对其他玩家的概率分布猜测

# 游戏历史记录
class GameEvent(BaseModel):
    round: int
    phase: Phase
    actor_id: int
    action: GameAction
    timestamp: datetime

class NightResult(BaseModel):
    killed_player: Optional[int]   # 狼刀目标
    saved_player: Optional[int]    # 女巫解救（可与kill相同 = 平安夜）
    poisoned_player: Optional[int]  # 女巫毒杀
    checked_player: Optional[int]   # 预言家查验目标
    check_result: Optional[Faction] # 查验结果

class GameState(BaseModel):
    phase: Phase
    round: int
    players: List[Player]
    alive_werewolves: int
    alive_villagers: int
    night_results: List[NightResult]
    sheriff_id: Optional[int]
    game_history: List[GameEvent]
```

---

## 5. 模块解构与指令 (Implementation Prompt)

### 第一阶段：异步 GM 状态机 (Core Engine)

**任务描述**：实现 `GameMaster` 类，使用异步状态机驱动游戏阶段轮转。

* **状态定义**：`PRE_GAME` -> `NIGHT_WEREWOLF` -> `NIGHT_SEER` -> `NIGHT_WITCH` -> `NIGHT_HUNTER` -> `DAY_ANNOUNCE` -> `DAY_DISCUSS` -> `DAY_VOTE` -> `GAME_OVER`。
* **核心逻辑**：
  1. 使用 `asyncio.Queue` 收集所有存活 Agent 的行动。
  2. 严格校验动作合法性（如：死人不能说话，平民不能在夜间行动）。
  3. 维护 `GameHistory` 全局单例，记录所有发言日志。
  4. 夜间严格按法官唤醒顺序执行：**守卫 → 狼人 → 女巫 → 预言家 → 猎人**。
  5. 女巫阶段：先告知夜间死者，再询问是否使用解药/毒药（解药与毒药不能同一晚使用，解药用后不再得知夜间死者详情）。
  6. 技能状态追踪：守卫不可连续守同一人；女巫解药/毒药各仅一次；猎人被毒杀不可开枪；白痴被投出不可投票。
  7. 警长机制（可选）：首日发言前选举警长 → 警长归票 → 警长死亡时移交警徽。

### 第二阶段：Agent 脑干（Prompt Engineering）

**System Prompt 结构定义**：

1. **Role Play**: `You are Player {id}, a {role} in the Werewolf game. Your faction is {faction}. Your goal is {goal}.`
2. **Context**: `Current Phase: {phase}. Round: {round}. Alive Players: {alive_list}. Last Night Result: {death_info}.`
3. **Memory**: `Summary of previous rounds: {summary}. Your previous claims: {lie_ledger}. Key events: {key_events}.`
4. **Belief State**: `Your current beliefs about other players: {belief_state}.`（Agent 应维护对每个玩家的内部概率估计）
5. **Strategy**: `Your lying strategy for this phase: {lying_strategy}.`
6. **Terminology Prompt**: 注入狼人杀术语知识，如 "金水 = SEER checked GOOD", "查杀 = SEER checked WOLF"

**Output Format**（强制 XML 格式）：

```xml
<thinking>
1. 局面分析：当前存活玩家{名单}，已知信息{...}
2. 他人动机推理：假设{玩家A}为狼，则{行为解释}
3. 策略选择：我本轮选择{策略}，因为{理由}
4. 概率估计：{1: "70% Wolf", 2: "80% Villager", ...}
</thinking>
<speak>
本轮公开发言内容（模拟真实玩家发言风格）
</speak>
<vote>ID 或 NONE</vote>
<action>SKILL_NAME:TARGET_ID 或 NONE</action>
```

### 第三阶段：Lying Skill 模块 (Deception Logic)

**逻辑实现**：

* **触发机制**：
  - 如果 `role in WEREWOLF_ROLES` → 强制触发谎言策略
  - 如果 `suspicion_score[self.id] > threshold` → 防御性谎言
  - 如果 `role == SEER` 且存活 → 必须诚实上报查验结果

* **策略池（基于狼人杀术语建模）**：
  | 策略 | 英文标识 | 描述 |
  |------|----------|------|
  | 悍跳预言家 | `SEER_CLAIM` | 狼人伪装预言家，发布虚假查验结果（给狼队友发金水/给好人发查杀） |
  | 编造信息 | `INFO_FABRICATION` | 编造虚假的夜间信息或对他人发言的扭曲引用 |
  | 倒钩 | `DEEP_COVER` | 狼人攻击自己的狼队友以洗白身份 |
  | 煽动 | `INSTIGATE` | 狼人煽动好人之间互相怀疑 |
  | 沉默深水 | `SILENT_DEEP` | 低调发言，避免成为焦点 |
  | 穿神衣服 | `ROLE_CLAIM` | 声称自己是某神职（女巫/猎人/守卫）来混淆好人视线 |
  | 选择性隐瞒 | `SILENT_OMISSION` | 刻意不提及某些对己方不利的关键事实 |
  | 自刀 | `SELF_KILL` | 狼人击杀自己人，骗取女巫解药或做高身份 |

* **矛盾检测**：
  - 谎言必须记录在 `lie_ledger` 中（格式：`{round: {claim: "I am SEER", actual_role: "WEREWOLF", target: 5, claimed_result: "GOOD"}}`）
  - 每轮生成前检查 `lie_ledger`，防止自相矛盾（如：曾声称查验5号金水，现又说5号是狼）
  - 若检测到矛盾，Agent 需生成"圆谎"策略（如：第一轮查验可能被干扰）

* **谎言一致性管理器**：
  ```python
  class LieLedgerManager:
      def add_claim(self, player_id: int, round: int, claim: Dict): ...
      def check_contradiction(self, player_id: int, new_claim: Dict) -> List[str]: ...
      def generate_reconciliation(self, contradictions: List[str]) -> str: ...
      def get_claimed_role(self, player_id: int) -> Optional[Role]: ...
  ```

---

## 6. 决策辅助模块 (Decision Skills)

> 该模块为可选但强烈建议实现。**规则不取代 LLM 决策**，而是提供合法性校验、fallback 及辅助信息注入。

### 6.1 设计目标

- **提高系统鲁棒性**：当 LLM 输出格式错误、超时或逻辑明显违规时，给出合法动作。
- **降低 LLM 认知负担**：将对跳判断、退水时机、技能使用规则等高频确定性逻辑剥离为纯函数。
- **保持博弈魅力**：所有规则决策均可被 LLM 最终覆盖，LLM 负责核心谎言与推理。

### 6.2 决策技能清单（按优先级）

| 技能 | 适用角色 | 功能 | 实现方式 |
|------|----------|------|----------|
| `vote_fallback` | 所有 | LLM 投票非法时，基于可疑度矩阵加权投票 | 规则 + `belief_state` |
| `should_retract_claim` | 狼人 | 悍跳后判断是否退水 | 规则：对跳人数≥2且自己怀疑度高 |
| `witch_antidote_suggestion` | 女巫 | 首夜必救，后期救明确金水 | 规则 |
| `witch_poison_suggestion` | 女巫 | 毒明确明狼，不毒预言家 | 规则 |
| `seer_check_suggestion` | 预言家 | 基于可疑度或警徽流推荐查验目标 | 规则 + 历史查验 |
| `judge_true_seer` | 所有 | 对跳时输出最可能真预言家的ID（供LLM参考） | 规则：查验一致性、警徽流、发言矛盾 |

### 6.3 集成方式

```python
class Agent:
    async def act(self, game_state, belief_state):
        llm_output = await self.call_llm(...)   # 包含 vote_target, skill_target 等
        
        # 第一层：合法性校验 + 修正
        llm_output.vote_target = VoteDecision.fallback_if_invalid(
            llm_output.vote_target, self.id, game_state, belief_state
        )
        
        # 第二层：注入辅助信息（可选，不覆盖LLM）
        hint = ""
        if game_state.phase == Phase.DAY_DISCUSS:
            true_seer_id = judge_true_seer(game_state, belief_state)
            hint += f"[系统提示] 规则模块推断真预言家可能是 {true_seer_id}。"
        
        # 将 hint 加入下一轮 prompt 的 Context 部分
        return llm_output
```

> **注意**：决策模块的输出**不应直接覆盖 LLM 的合法输出**，仅在 LLM 输出无效时作为 fallback，或作为额外提示注入。

---

## 7. 扩展模块：信念网络与ToM推理

### 6.1 信念建模 (Belief Modeling)

每个 Agent 维护对全局状态的**概率化信念**：

```python
class BeliefState(BaseModel):
    player_id: int
    round: int
    # 对每个玩家的阵营概率估计 {"1": {"WEREWOLF": 0.3, "VILLAGER": 0.1, "SEER": 0.6}}
    role_probabilities: Dict[int, Dict[str, float]]
    # 置信度 (对自身判断的确定程度)
    confidence: float
    # 信念更新来源
    update_reason: str
```

**信念更新规则**：
1. 预言家查验 → 对应玩家概率二值化
2. 玩家发言矛盾 → 提高该玩家为狼的概率
3. 狼队友死亡 → 降低对其他狼队友身份的怀疑
4. 投票模式分析 → 冲票/分票模式推断阵营

### 6.2 心智理论 (Theory of Mind)

Agent 模拟"其他人如何看我"：
```python
class TheoryOfMind(BaseModel):
    # 我认为玩家X认为我的身份是什么
    perceived_by_others: Dict[int, Dict[str, float]]
    # 我认为玩家X认为玩家Y的身份是什么
    second_order_beliefs: Dict[int, Dict[int, Dict[str, float]]]
```

---

## 8. 记忆与信念维护机制 (Memory & Belief)

### 8.1 设计目标

- **不存储原始发言全文**，而是提取关键"事件"（声明身份、查验结果、攻击/保护、退水等）。
- **模拟遗忘曲线**：事件权重随轮次指数衰减。
- **自动矛盾检测**：与 `lie_ledger` 联动，矛盾事件权重降低或标记无效。
- **直接更新 `belief_state.role_probabilities`**，为 LLM 提供结构化先验。

### 8.2 事件抽取 (轻量级，无需 LLM)

使用正则表达式匹配发言中的典型模式：

```python
STATEMENT_PATTERNS = {
    "claim_role": (r"(我是|我为)(预言家|女巫|猎人|守卫|村民|狼)", 1.0),
    "check_result": (r"(验|查)(\d+)(号|是)(好人|狼|金水|查杀)", 1.0),
    "accuse": (r"(我认为|觉得|怀疑)(\d+)(号|是)(狼|坏人)", 0.8),
    "defend": (r"(我觉得)(\d+)(号|是)(好人|金水|村民)", 0.6),
    "retract": (r"退水|我不是(预言家|神)", 0.9),
}
```

每轮所有发言经过抽取，生成 `MemoryUnit` 存入全局 `MemoryPool`。

### 8.3 数据结构

```python
class MemoryUnit(BaseModel):
    id: str
    round: int
    speaker_id: int
    target_id: Optional[int]   # 被攻击/查验/保护的对象
    event_type: str            # "claim_role", "check_result", ...
    content: str               # 摘要文本
    base_weight: float         # 预设权重
    current_weight: float      # 实时衰减后的权重
    is_contradicted: bool = False

class MemoryPool:
    units: List[MemoryUnit]
    
    def add_unit(self, unit: MemoryUnit): ...
    def decay_all(self, current_round: int, decay_factor: float = 0.85): ...
    def mark_contradiction(self, event_id: str): ...
    def get_active_memories(self, min_weight: float = 0.15) -> List[MemoryUnit]:
        return [u for u in self.units if u.current_weight >= min_weight and not u.is_contradicted]
```

### 8.4 权重计算公式

```
current_weight = base_weight × (decay_factor) ^ (current_round - event_round)
```

若事件被标记为矛盾，`current_weight` 强制设为 0（或乘以 0.1）。

### 8.5 更新 BeliefState 的流程

每轮结束后，`GameMaster` 调用 `BeliefUpdater`：

```python
class BeliefUpdater:
    @staticmethod
    def update(belief_state: BeliefState, memory_pool: MemoryPool):
        for unit in memory_pool.get_active_memories():
            target = unit.target_id
            if target is None:
                continue
            if unit.event_type == "accuse":
                # 攻击他人：提高目标为狼的概率
                belief_state.role_probabilities[target]["WEREWOLF"] += 0.05 * unit.current_weight
            elif unit.event_type == "check_result" and "狼" in unit.content:
                belief_state.role_probabilities[target]["WEREWOLF"] = 0.95
            elif unit.event_type == "defend":
                belief_state.role_probabilities[target]["VILLAGER"] += 0.1 * unit.current_weight
            # ... 其他类型
        belief_state.normalize()   # 确保概率和为1
```

### 8.6 在 Agent Prompt 中的使用

从 `MemoryPool` 中取出 `current_weight > 0.2` 的事件，按权重降序排列，格式化为自然语言：

```
[重要记忆]
- 第2轮，3号声称自己是预言家 (权重0.9)
- 第3轮，1号指责5号是狼人 (权重0.7)
- 第2轮，5号退水，说自己不是预言家 (权重0.6)
```

注入到 `System Prompt` 的 `Context` 部分，位于原始发言日志之后。

### 8.7 实现预估工作量

| 模块 | 时间 |
|------|------|
| 事件抽取正则 + 单元测试 | 4h |
| MemoryPool 及衰减/矛盾逻辑 | 4h |
| BeliefUpdater 集成 | 4h |
| Agent prompt 集成记忆 | 2h |
| 前端显示记忆事件（可选） | 4h |
| 调优权重参数 | 4h |
| **总计** | ≈ 22h（3个工作日）|

---

## 9. WebSocket 通信协议规范

### 9.1 下行消息 (GM → Agent)

GM 向各 Agent 推送阶段信息与行动请求：

```json
{
  "type": "ACTION_REQUIRED",
  "payload": {
    "phase": "DAY_DISCUSS",
    "round": 2,
    "alive_players": [1, 2, 4, 5],
    "night_result": {
      "deaths": [3],
      "death_info": "昨夜 3 号玩家死亡"
    },
    "history": "上一轮 3 号被放逐，5 号声称自己是预言家。",
    "belief_hint": {"3": "Confirmed Wolf"},
    "memory_snapshot": [
      {"round": 1, "event": "5 号声称自己是预言家", "weight": 0.85},
      {"round": 1, "event": "5 号查验 3 号为狼人", "weight": 0.85}
    ]
  }
}
```

### 9.2 上行消息 (Agent → GM)

Agent 返回思考过程与行动决策：

```json
{
  "type": "SUBMIT_ACTION",
  "payload": {
    "thinking": "<thinking>当前 5 号跳预言家，我作为狼人需要穿猎人衣服压制他...</thinking>",
    "speech": "我是猎人，5 号你在乱穿衣服，我看你才是狼。",
    "vote_target": 5,
    "skill_target": null,
    "skill_name": null,
    "lie_plan": {"type": "ROLE_CLAIM", "claimed_role": "HUNTER"}
  }
}
```

### 9.3 广播消息 (GM → 所有客户端)

| 消息类型 | 触发时机 | 内容 |
|----------|----------|------|
| `PHASE_CHANGE` | 阶段切换 | 新阶段名、轮次、存活玩家 |
| `NIGHT_RESULT` | 天亮公布 | 死者列表、死亡原因摘要 |
| `PLAYER_SPEECH` | 玩家发言 | 发言者 ID、发言内容（流式推送） |
| `PLAYER_VOTE` | 投票（可选匿名） | 投票者 ID、被投者 ID（可延迟公布） |
| `GAME_OVER` | 游戏结束 | 胜负结果、所有角色身份 |
| `THINKING_STREAM` | 观战模式专用 | 实时流式推送 Agent 的 `<thinking>` 内容 |

### 9.4 流式推送 (Streaming via WebSocket)

前端思维链面板通过 WebSocket 实时接收 Agent 思考过程：

```
Server → Client (streaming chunks):
  {"type": "THINKING_CHUNK", "player_id": 2, "chunk": "我认为 5 号的发言", "done": false}
  {"type": "THINKING_CHUNK", "player_id": 2, "chunk": "存在逻辑漏洞...", "done": false}
  {"type": "THINKING_CHUNK", "player_id": 2, "chunk": "", "done": true}
```

### 9.5 FastAPI WebSocket 端点

```python
@router.websocket("/ws/player/{player_id}")
async def player_websocket(websocket: WebSocket, player_id: int):
    await websocket.accept()
    agent = game_master.get_agent(player_id)
    while game_master.phase != Phase.GAME_OVER:
        action_req = await agent.wait_for_action_required()
        await websocket.send_json(action_req.dict())
        response = await websocket.receive_json()
        await agent.submit_action(GameAction(**response["payload"]))

@router.websocket("/ws/spectator")
async def spectator_websocket(websocket: WebSocket):
    await websocket.accept()
    async for event in game_master.event_stream():
        await websocket.send_json(event.dict())
```

---

## 10. 编码原则 (Coding Guidelines for AI)

1. **State Isolation**: 严禁在 `Agent` 类中直接修改 `GameMaster` 的状态，必须通过 `Action` 返回给 GM 统一处理。
2. **Concurrency**: 调用 LLM API 时必须使用 `asyncio.gather` 以支持多玩家并行思考，设置 `timeout=30s`。
3. **Error Handling**: 若 LLM 返回格式错误，需具备解析重试机制（Retry logic for XML parsing）。
4. **Logging**: 所有 `<thinking>` 标签内容必须后端存储并推送到前端，这是项目的核心功能。
5. **Role Validation**: 夜间阶段只唤醒对应角色（狼人阶段只唤醒狼人），不得向无关玩家泄露信息。
6. **Deterministic Resolution**: 投票平票/GM判定需有明确定义的规则，避免随机行为。
7. **Decision Fallback**: 所有 Agent 决策必须经过 `DecisionSkills` 合法性校验。若 LLM 输出无效，使用规则 fallback 保证游戏继续。

---

## 11. 前端可视化需求

* **棋盘视角**：圆桌布局显示12名玩家，实时标注存活/死亡状态
* **昼夜切换**：使用 `AnimatePresence` (React/Framer Motion) 处理昼夜切换的视觉反馈
* **思维链面板**：实时流式展示每个 Agent 的 `<thinking>` 内容（打字机效果）
* **发言流**：WebSocket 推送实时发言，按顺序高亮当前发言者
* **角色信息**：观战模式可查看所有角色；玩家模式仅显示已知信息
* **谎言追踪器**：观战模式下标注每个 Agent 的谎言记录
* **信念网络可视化**：可选展示 Agent 之间的概率估计矩阵（力导向图）
* **记忆事件面板**（观战模式）：按时间线展示每个 MemoryUnit 及其权重变化，便于调试和展示遗忘曲线

---

## 16. 模型配置与前后端协作 (Model Assignment)

> 前端提供每名玩家的模型选择面板，后端按玩家分配不同 LLM 驱动 Agent，支撑多模型同台竞技（Leaderboard 方向的数据基础）。

### 16.1 提供商与模型层级

前端选择流程：**提供商 → 模型 → 温度/自定义 Prompt**。每个提供商有独立 API Key 输入框。

| 提供商 | 可用模型 | API Base URL | 需填 API Key |
|--------|---------|-------------|-------------|
| DeepSeek | `deepseek-chat`, `deepseek-reasoner` | `https://api.deepseek.com/v1` | ✅ |
| OpenAI | `gpt-4o`, `gpt-4o-mini`, `o4-mini` | `https://api.openai.com/v1` | ✅ |
| 阿里 Qwen | `qwen-plus`, `qwen-max`, `qwen-turbo` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | ✅ |
| 豆包 Doubao | `doubao-lite-128k`, `doubao-pro-128k` | `https://ark.cn-beijing.volces.com/api/v3` | ✅ |
| Mock (本地) | `mock` | (无) | 不需要 |

### 16.2 前端 UI 设计（提供商→模型二级联动）

```
┌─ Game Setup ────────────────────────┐    ┌─ ⚙ API Keys ──────────────┐
│  P1 (狼人) [DeepSeek ▼] [deepseek-chat ▼] [0.8]  │  DeepSeek:  [sk-••••••] 👁  │
│  P2 (预言) [OpenAI   ▼] [gpt-4o ▼]       [0.7]  │  OpenAI:    [sk-••••••] 👁  │
│  P3 (女巫) [Qwen     ▼] [qwen-plus ▼]     [0.9]  │  Qwen:      [sk-••••••] 👁  │
│  ...                                            │  Doubao:    [sk-••••••] 👁  │
│  ─────────────────────────────────────          │  [保存到本地]              │
│  全部使用: [DeepSeek ▼] → [deepseek-chat ▼]    └──────────────────────────┘
│                                     │
│  [Start Game]                       │
└─────────────────────────────────────┘
```

- **左侧面板**：12 人逐行配置，第一列选提供商，第二列联动切换对应模型列表，第三列拖温度
- **右侧 API Keys 面板**：每个提供商一个密码输入框（带 👁 显/隐切换），`[保存到本地]` 写入 `localStorage`
- **"全部使用"快捷操作**：选提供商+模型一键应用到全部 12 人

### 16.3 后端 API

```python
# GET /providers — 返回提供商→模型映射（供前端渲染联动下拉框）
{
  "providers": {
    "deepseek": {
      "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
      "models": ["deepseek-chat", "deepseek-reasoner"]
    },
    "openai": {
      "name": "OpenAI", "base_url": "https://api.openai.com/v1",
      "models": ["gpt-4o", "gpt-4o-mini", "o4-mini"]
    },
    ...
  }
}

# POST /game/config — 含 api_key 字段，后端仅在内存保存，绝不落盘
{
  "providers": {
    "deepseek": {"api_key": "sk-xxx"},
    "openai":  {"api_key": "sk-yyy"}
  },
  "players": [
    {"player_id": 1, "provider": "deepseek", "model": "deepseek-chat", "temperature": 0.8},
    ...
  ]
}
```

### 16.4 前后端交互流程

```
前端                                 后端
 │  GET /providers                    │
 │ ─────────────────────────────────> │
 │  { providers: { deepseek: {...} }} │
 │ <───────────────────────────────── │
 │                                    │
 │  (用户在UI选提供商、填API Key、     │
 │   选模型、调温度)                   │
 │                                    │
 │  POST /game/config                 │
 │  { providers: {api_keys}, players } │
 │ ─────────────────────────────────> │
 │  { status: "ok" }                  │
 │ <───────────────────────────────── │
 │                                    │
 │  POST /game/start                  │
 │ ─────────────────────────────────> │
 │                                    │
 │  WS /ws/spectator                  │
 │ <═══════════════════════════════> │
```

### 16.5 数据模型扩展

```python
class PlayerModelConfig(BaseModel):
    player_id: int
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    temperature: float = 0.8
    system_prompt_extra: str = ""

class ProviderKey(BaseModel):
    api_key: str = ""

class GameModelConfig(BaseModel):
    default_provider: str = "deepseek"
    default_model: str = "deepseek-chat"
    default_temperature: float = 0.8
    providers: dict[str, ProviderKey] = {}
    players: list[PlayerModelConfig] = []
```

### 16.6 前后端配合要点

- **密钥安全**：API Key 通过 HTTPS body 传输，后端存入 `_provider_keys` 内存字典（`dict[str, str]`），**日志写入时强制脱敏为 `"sk-***"`**，对局结束后随进程销毁
- **localStorage 持久化**：前端可将 API Key 保存到浏览器 localStorage（带用户确认），下次打开自动填充，避免反复输入
- **默认值链**：玩家配置 > "全部使用"快捷设置 > 后端 `config.py` 默认值
- **提供商→base_url 映射**：后端 `/providers` 返回完整映射，前端不硬编码 URL，新增提供商只需改后端
- **日志记录**：每个 `GameEvent` 携带 `model` 字段标明发言由哪个模型生成；`llm_calls.jsonl` 中 `api_key` 字段强制脱敏

---

## 12. Vibe Coding 专用提示词 (One-Liner Start)

> "Act as a Senior Backend Engineer. Please initialize the project structure based on the provided Plan Doc. Start by implementing the `Phase` Enum, `Role` Enum, and the `GameMaster` class in `engine.py`. Ensure all state transitions are handled by an `async` loop. Support the standard 12-player Werewolf board (预女猎白) with proper night action ordering."

---

## 13. 可观测性与结构化日志 (Observability)

> 系统需产出结构化日志以实现**全程可观测**，这是评测、复盘与自进化的数据基础。

### 13.1 日志分层

| 层级 | 内容 | 存储格式 |
|------|------|----------|
| **对局元数据** | 角色分配、胜负结果、轮次、存活统计 | JSON |
| **回合事件流** | 每轮每阶段的 `GameEvent`（含 `<thinking>` 完整内容） | JSONL |
| **Agent 信念轨迹** | 每轮每 Agent 的 `BeliefState` 快照 | JSONL |
| **谎言账本** | 每局所有 Agent 的 `LieLedger` 完整记录 | JSON |
| **LLM 调用日志** | 每次 API 调用的 prompt、response、耗时、token 数 | JSONL |

### 13.2 日志文件规范

```
logs/
├── game_{timestamp}/
│   ├── meta.json              # 对局元数据
│   ├── events.jsonl           # 全量 GameEvent 流
│   ├── beliefs.jsonl          # 每轮信念快照
│   ├── lies.json              # 谎言账本
│   └── llm_calls.jsonl        # LLM 调用记录
```

### 13.3 实时观测端点

```python
@router.get("/game/{game_id}/events")       # 事件流 (支持 ?round=N 过滤)
@router.get("/game/{game_id}/beliefs")      # 信念轨迹
@router.get("/game/{game_id}/lies")         # 谎言账本
@router.get("/game/{game_id}/replay")       # 完整对局回放数据
```

---

## 14. 人机混战模式设计 (Human-in-the-Loop)

### 14.1 WebSocket 端点扩展

```python
@router.websocket("/ws/human")
async def human_player_ws(websocket: WebSocket):
    # 人类玩家加入队列，等待下一局开始
    # GM 在对应阶段向人类 WebSocket 发送 ACTION_REQUIRED
    # 人类通过 UI 提交发言 + 投票
```

### 14.2 人类玩家体验

| 阶段 | 人类可见信息 | 操作 |
|------|-------------|------|
| 身份确认 | 自己的角色与阵营 | 无 |
| 夜晚（狼人） | 狼队友 ID 列表 | 协商击杀目标 |
| 夜晚（预言家） | 查验结果 | 选择查验目标 |
| 夜晚（女巫） | 夜间死者 | 选择用药 |
| 白天讨论 | 所有公开发言 | 输入自己的发言 |
| 投票 | 存活玩家列表 | 选择投票目标 |

### 14.3 人机混战特殊规则

- 人类玩家的发言不经 LLM 生成，直接由输入框提交
- 人类发言后同样触发 `EventExtractor` 和 `MemoryPool` 更新
- 人类玩家的 `<thinking>` 区域显示 `[HUMAN]` 标记
- 支持 1~12 名人类玩家，其余由 AI 填充

---

## 15. 给你的工程建议 (SJTU Special)

既然你习惯于处理复杂的工程 derivation：

* **关于可疑度矩阵**：建议在 `thinking` 过程中让 Agent 输出对其他玩家的"概率分布猜测"，例如：`{1: "60% Wolf", 2: "90% Villager", 3: "SEER(金水)"}`。
* **关于前端**：建议在 React 中使用 `AnimatePresence` 处理昼夜切换的视觉反馈，增强"游戏感"。
* **关于LLM调用优化**：对同一夜晚阶段的独立角色（如守卫、狼人可并行），使用 `asyncio.gather` 并行调用；对相互依赖的角色（女巫需知死者后才能行动）串行执行。
* **关于提示词注入**：在 System Prompt 中注入狼人杀术语定义（金水/查杀/银水等），确保 Agent 能正确理解和使用游戏术语。
* **关于板子扩展**：采用注册机制 `RoleRegistry` 管理角色技能，方便后续添加守卫/白狼王/丘比特等角色。

需要我针对具体的 **FastAPI WebSocket 路由接口定义** 为你产出更详细的代码规范吗？

---

## 17. Self-Harness：狼人杀自进化引擎

> **理念来源**：Harness Engineering (*The Last Harness You'll Ever Build*, arXiv:2604.21003)、Gödel Agent (*Recursive Self-Improvement*, arXiv:2410.04444)、AutoHarness (*arXiv:2603.03329*)、*"Thin Harness, Fat Skills"* 准则、LangChain Better-Harness（评估驱动爬山）。

### 17.1 Harness 哲学

> *"不是让 Agent 更强，而是让 Agent 学会如何让自己更强。"*

传统 AI 工程：人写代码 → 人调 prompt → 人看结果 → 人改进。
**Self-Harness** 范式：Agent 读取自身代码/配置 → Agent 分析对局数据 → Agent 修改自身 → Agent 重跑验证 → 循环。

**Thin Harness, Fat Skills**：
- **Harness（缰绳）**：最小化的运行时期框架，只提供 ①日志读取 ②配置热重载 ③沙箱安全执行 ④评估打分 四个核心能力。Harness 本身不参与博弈逻辑。
- **Skills（技能）**：Agent 的 prompt、策略权重、谎言偏好、发言风格，这些是 Harness 优化的对象。

### 17.2 自进化循环 (The Loop)

```
                    ┌──────────────────┐
                    │   READ SELF      │
                    │ 读取自身配置/代码  │
                    └──────┬───────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │ 对局日志     │ │ 信念轨迹    │ │ LLM调用记录  │
    │ events.jsonl│ │beliefs.jsonl│ │llm_calls    │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                    ┌──────▼───────────┐
                    │   ANALYZE        │  ← LLM 驱动的复盘分析
                    │  失败归因 /       │
                    │  策略收益计算     │
                    └──────┬───────────┘
                           │
                    ┌──────▼───────────┐
                    │   MODIFY SELF    │  ← Agent 修改自身
                    │  更新 prompt     │     (代码生成 + 沙箱校验)
                    │  调整策略权重    │
                    │  优化发言模板    │
                    └──────┬───────────┘
                           │
                    ┌──────▼───────────┐
                    │   RUN SELF       │  ← N 局对抗赛
                    │  新配置 vs 旧配置 │
                    │  A/B 对照测试    │
                    └──────┬───────────┘
                           │
                    ┌──────▼───────────┐
                    │   EVALUATE       │  ← 多维评分
                    │  ELO / 胜率 /    │
                    │  谎言成功率      │
                    └──────┬───────────┘
                           │
                     是否显著提升？
                     ├─ YES → 提交为新基线
                     └─ NO  → 回滚，重新分析
```

### 17.3 架构分层

```
┌─────────────────────────────────────────────────┐
│              狼人杀 Self-Harness                   │
├─────────────────────────────────────────────────┤
│  Evaluator Layer (评估层)                         │
│  ├─ ResultEval: 胜率、存活轮次、屠边类型          │
│  ├─ ProcessEval: 逻辑一致性、谎言成功率、投票准确率│
│  └─ Leaderboard: ELO排名、模型对比矩阵             │
├─────────────────────────────────────────────────┤
│  Optimizer Layer (优化层)                          │
│  ├─ PromptOptimizer: 基于复盘调整 System Prompt   │
│  ├─ StrategyOptimizer: 调整谎言策略权重分配       │
│  ├─ TemplateOptimizer: 优化发言模板/风格          │
│  └─ HyperOptimizer: 调 temperature / top_p       │
├─────────────────────────────────────────────────┤
│  Sandbox Layer (沙箱层) — Thin Harness            │
│  ├─ ConfigReloader: 热重载 Agent 配置             │
│  ├─ CodeValidator: 生成代码的安全性校验           │
│  ├─ RollbackManager: 配置回滚与版本管理           │
│  └─ GameRunner: N 局并行调度                      │
├─────────────────────────────────────────────────┤
│  Analysis Layer (分析层)                           │
│  ├─ LogReader: 解析 events.jsonl + beliefs.jsonl │
│  ├─ RootCauseAnalyzer: LLM 驱动的失败归因        │
│  ├─ StrategyAuditor: 谎言收益/成本计算            │
│  └─ DiffEngine: 配置变更影响度量化                │
└─────────────────────────────────────────────────┘
```

### 17.4 核心数据模型

```python
class SelfHarnessConfig(BaseModel):
    games_per_iteration: int = 10      # 每次迭代跑N局
    min_win_rate_gain: float = 0.05   # 最小胜率提升阈值
    max_iterations: int = 100          # 最大迭代次数
    sandbox_enabled: bool = True       # 是否启用代码沙箱
    target_role: Optional[str] = None  # 只优化特定角色（None=全部）

class IterationResult(BaseModel):
    iteration: int
    baseline_win_rate: float
    new_win_rate: float
    changes: list[ConfigChange]        # 配置变更列表
    analysis: str                      # 复盘分析文本
    verdict: str                       # "promote" / "rollback"

class ConfigChange(BaseModel):
    target: str                        # "prompt" / "strategy_weight" / "temperature"
    player_role: str                   # 被修改的玩家角色
    before: str                        # 变更前值
    after: str                         # 变更后值
    rationale: str                     # 变更理由（LLM生成）
    diff_impact: float                 # 预测影响度 (0~1)

class LeaderboardEntry(BaseModel):
    model_name: str
    role: str
    games_played: int
    wins: int
    elo: float
    avg_rounds_survived: float
    lie_success_rate: float
    vote_accuracy: float
```

### 17.5 评估指标体系

| 维度 | 指标 | 计算方式 |
|------|------|----------|
| **结果评估** | 胜率 (Win Rate) | `wins / total_games` |
| | 平均存活轮次 | `sum(survived_rounds) / games` |
| | 屠边类型分布 | `gods_exhausted vs villagers_exhausted` |
| **过程评估** | 谎言成功率 | `(谎言被采信次数) / (谎言发布次数)` |
| | 投票准确率 | `(投中狼人次) / (总投票次)` |
| | 逻辑一致性 | `(无矛盾发言轮次) / (总轮次)` |
| | 查验有效率 | `(查验到狼人次) / (总查验次)`（预言家专属） |
| **效率评估** | 平均发言长度 | tokens per speech |
| | LLM 调用耗时 | avg latency per action |
| | 总 Token 消耗 | total tokens per game |

### 17.6 Prompt 自优化策略

```
[Agent 原始 System Prompt]
         │
         ▼
[复盘分析 Agent 读取对局日志]
   "玩家3在第2轮悍跳预言家时，发言逻辑出现矛盾：
    先声称查验5号金水，后又说5号发言像狼..."
         │
         ▼
[Optimizer 生成 Prompt 追加指令]
   system_prompt_extra += """
   ⚠️ 历史教训 (第N次迭代):
   - 悍跳预言家时，查验结果一旦发布就不可更改，除非你有合理的"修正"理由
   - 如果被质疑查验结果矛盾，使用以下话术模板: "第X轮我的判断基于有限信息..."
   """
         │
         ▼
[下一局使用新 Prompt]
```

### 17.7 谎言策略权重自进化

每轮迭代后，根据各策略的收益/成本比自动调整权重：

```python
class StrategyWeightUpdater:
    def update(self, strategy_stats: dict, current_weights: dict) -> dict:
        """
        strategy_stats = {
            "SEER_CLAIM": {"uses": 12, "successes": 8, "detections": 4},
            "DEEP_COVER": {"uses": 6, "successes": 4, "detections": 2},
            ...
        }
        """
        new_weights = {}
        for strategy, stats in strategy_stats.items():
            if stats["uses"] > 0:
                success_rate = stats["successes"] / stats["uses"]
                detection_rate = stats["detections"] / stats["uses"]
                # 收益因子: 成功+1, 被识破-2
                utility = success_rate * 1.0 - detection_rate * 2.0
                # 新权重: 原权重 + 学习率 × 效用
                new_weights[strategy] = max(
                    0.01, current_weights.get(strategy, 0.1) + 0.05 * utility
                )
        # 归一化
        total = sum(new_weights.values())
        return {k: v/total for k, v in new_weights.items()}
```

### 17.8 安全沙箱 (Sandbox)

Agent 只能修改三类内容，**严禁修改 Harness 自身**：

| 允许修改 | 禁止修改 |
|----------|----------|
| `system_prompt` / `system_prompt_extra` | Harness 引擎代码 |
| `lying_strategy_weights` | 游戏规则 / 胜负判定 |
| `temperature` / `top_p` | 数据模型 / API 接口 |
| `speech_templates`（发言模板库） | 日志写入逻辑 |
| `vote_fallback` 策略参数 | 沙箱规则自身 |

```python
class SandboxValidator:
    ALLOWED_TARGETS = {
        "prompt", "strategy_weight", "temperature",
        "template", "vote_fallback_param",
    }

    def validate(self, change: ConfigChange) -> tuple[bool, str]:
        if change.target not in self.ALLOWED_TARGETS:
            return False, f"Denied: cannot modify {change.target}"
        if change.target == "temperature":
            t = float(change.after)
            if not (0.0 <= t <= 2.0):
                return False, f"Temperature out of range: {t}"
        return True, "OK"
```

### 17.9 CLI 驱动

```bash
# 启动自进化循环：狼人阵营 100 次迭代
python -m backend.harness.run \
  --target-faction WEREWOLF \
  --games-per-iteration 20 \
  --max-iterations 100 \
  --min-gain 0.03

# 输出：
# Iter 1: baseline=42.5% → new=45.0% (+2.5%) [PROMOTE]
# Iter 2: baseline=45.0% → new=48.2% (+3.2%) [PROMOTE]
# Iter 3: baseline=48.2% → new=47.0% (-1.2%) [ROLLBACK]
# ...

# 仅分析不复盘（单次归因）
python -m backend.harness.analyze --game-id game_20260511_131536
```

### 17.10 与现有模块的关系

```
Harness (Thin)          Skills (Fat) — 被 Harness 优化的对象
─────────────────────   ─────────────────────────────────────
Sandbox (17.8)          → Agent Prompt (§5 第二阶段)
GameRunner              → GameMaster (§5 第一阶段)
Evaluator (17.5)        → 可观测性日志 (§13)
ConfigReloader          → 模型配置 (§16)
Optimizer (17.6/17.7)   → Lying Skill (§5 第三阶段)
Leaderboard (17.4)      → 评测+复盘 (进阶方向②)
```

### 17.11 实现预估工作量

| 模块 | 时间 | 依赖 |
|------|------|------|
| LogReader + Analysis Layer | 4h | §13 日志已就绪 |
| Evaluator (多维指标) | 3h | LogReader |
| StrategyWeightUpdater | 2h | LyingEngine |
| PromptOptimizer (LLM 复盘) | 4h | 分析层 |
| Sandbox + RollbackManager | 3h | — |
| HarnessRunner CLI | 3h | 全部上述 |
| Leaderboard UI | 4h | Evaluator |
| **总计** | ≈ 23h（3~4 个工作日） | |
