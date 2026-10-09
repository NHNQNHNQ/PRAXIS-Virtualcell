# GAP-AH-1 + GAP-AH-2:反幻觉武器接入生产 — 设计

- 日期:2026-06-06
- 状态:设计已批准(待 writing-plans)
- 关联:`TEST-AGENT-FRAMEWORK.md` §1 / §5.3 GAP-AH-1/AH-2;承接 GAP-E2E(skill 真执行验证,已完成 DONE_real 12→20)
- 范围:GAP-AH-1(相位门接入)+ GAP-AH-2(stop_hook 接入)+ AgentTool 描述强化。**不含 GAP-AH-3(KPI 纳 CI)**。

## 1. 背景与问题

GAP-E2E 证明了 skill **真能跑**;GAP-AH 确保 agent **不能假称跑过/分析过**——闭合"端到端真分析不幻觉"主线。审计(`TEST-AGENT-FRAMEWORK.md` §1)定位:两件反幻觉武器实现完整但**未接入 chat 生产路径**,且代码里有 3 个幻觉风险点。

本设计阶段的代码核查(关键发现,改变了 GAP-AH-1 的范围):

1. **chat 路径根本不驱动相位机**。能推进相位的 `brains/retrieve_first.py`(检索命中→`advance_phase(RETRIEVE)`)**没接进 chat**——`server/app.py` 用 `build_chat_system_prompt` 旁路了它。`get_phase` 默认 `INIT`,且 `app.py`/`query.py`/`tools/` 全路径无任何 `advance_phase`/`set_phase` 调用。→ 相位永远卡 `INIT`(`ALLOWED_OPS[INIT]` 为空集)。**天真地把 `PhaseAwarePermission` 加进权限链,会 DENY 掉所有 `rmcp_op != None` 的工具(SkillExec/RMCPWriteCase)→ 黄金链路立刻断,"全量零回归"必挂。**
2. **latent op 名不匹配**:`SkillExec.rmcp_op = "execute"`,但 `ALLOWED_OPS[Phase.EXECUTE] = {"call_skill"}`(`core/rmcp.py:42`);测试 `tests/test_brains_retrieve_first.py` 里的执行工具用的是 `rmcp_op="call_skill"`。→ 即使相位到了 EXECUTE,生产 SkillExec 也对不上,会被拒。
3. **现有 v1-移植件与真工具错位**:`hooks/builtin.advance_phase_on_retrieve` 按 `rmcp_op ∈ ALLOWED_OPS[RETRIEVE]` 判定检索工具,但真 `BrainQuery.rmcp_op = None`(`tools/brain_query.py:47`,"检索类不受相位门否则 INIT 死锁")→ 该钩子对真 BrainQuery 不触发;且 hooks 在 chat 未接线。
4. **`server/app.py:707-719`** 权限链实际只注入 `BashCommandPolicy` → `BridgePermissionAdapter` → `SerialToolRunner`,无相位门;`query()`(`core/query.py:35`)虽有 `stop_hook` 形参,`app.py` 调用时**没传**。

3 个幻觉风险点(代码仍存在):

| 风险点 | 证据 | 风险 |
|---|---|---|
| AgentTool 不真 fork | `agents/agent_tool.py` run() 只构 spawn 描述符,恒 ok=True | 把"构了描述符"当"子 agent 已完成分析" |
| SkillExec 降级 ok=True | `tools/skill_exec.py`,SSH 缺/无 run.py → SOP 模板 + ok=True | 把降级当"已执行"转述 |
| BrainQuery fixture | `tools/brain_query.py`,真盘空 → fixture 占位带 score | 把 fixture score 当真实命中 |

## 2. 目标 / 非目标

**目标**
- 在 chat 生产路径堵住"未检索就执行/写入"(检索先行证据门)和"声称执行但零工具证据"(终答 veto)两条幻觉根因路径。
- 不破坏黄金链路(检索后正常执行)、全量回归零失败。

**非目标**
- 不在 chat 跑完整 7 相位线性机(INIT→…→SEAL);采用轻量"检索先行证据门"。
- 不做 GAP-AH-3(把反幻觉 KPI 脚本化纳 ship 前 CI)——单独立项。
- 不改 BrainQuery fixture 行为本身(风险点③的透明标记已存在;本设计只确保 fixture/空命中**不解锁**执行,不把 fixture 当真检索)。

## 3. 关键设计决策(brainstorm 结论)

- **相位门强制模型 = 证据门:检索先行**。门的不变量:`rmcp_op != None` 的执行/写入类工具,仅当本会话已发生**成功的真实 BrainQuery 检索**才放行。用相位是否 `!= INIT` 作"已检索"信号。
- **落地方案 = 新建轻量 `RetrieveFirstPermission`**(而非把相位驱到 EXECUTE/SEAL 伪造中间相位)。统一管 call_skill + write_case,改动集中,不伪造 anti_filter/plan。
- **stop_hook veto 触发 = 声称执行 + 零工具证据**(保守):仅当终答声称做过执行/分析、且本会话历史零成功 tool_use 时 veto。几乎不误杀纯概念问答。

## 4. 组件设计

### 4.1 `RetrieveFirstPermission`(新,`praxis2/tools/permission.py`)
包一个 base `PermissionPolicy`(生产用 `BashCommandPolicy`)。`check(tool, payload, state)`:
1. `base_result = base.check(...)`;若非 `ALLOW`(DENY/ASK)→ 直接返回(base 优先,体例同 `PhaseAwarePermission` 对规则层)。
2. `op = getattr(tool, "rmcp_op", None)`;`op is None` → `ALLOW`(BrainQuery/FileRead/WebFetch/Bash/AgentTool 等检索/读/编排类透传)。
3. `op is not None` 且 `get_phase(state) is Phase.INIT` → `DENY`,reason:
   > "检索先行:本会话尚无成功的大脑检索(BrainQuery 命中),不能执行/写入。请先用 BrainQuery 检索相关 cases/rules,命中后再调用(自行补检索,勿停下问人)。"
4. 否则(`phase != INIT`,检索已发生)→ `ALLOW`。

与 `PhaseAwarePermission` 并存(后者保留给可能的严格相位场景);chat 生产用 `RetrieveFirstPermission`。

### 4.2 检索推进信号(`core/query.py` + 注入回调)
- `query()` 新增可选形参 `on_tool_results: Callable[[State, list[dict]], None] | None = None`,在 `run_turn` 拿到 `results` 后调用(`core/query.py:161` 之后)。query.py 不耦合 BrainQuery 具体语义。
- `app.py` 注入一个 `advance_phase_on_real_retrieval(state, results)`:扫 `results`,若存在某结果来自 BrainQuery 且为**真命中**(`value.degraded_to_bare == False` 且 `value.source == "filesystem"`,非 fixture/空)→ `advance_phase(state, Phase.RETRIEVE)`(幂等;已在 RETRIEVE 则跳过,守 S7 无 RETRIEVE→RETRIEVE 边)。
- degraded/fixture/空命中**不推进** → execute 仍被 `RetrieveFirstPermission` 拒(反幻觉不失守)。

### 4.3 `tool_use_presence` stop_hook(新,建议 `hooks/` 下)
- 签名 `(state) -> StopDecision`,`StopDecision.veto: bool` + `.message: str`(对齐 `core/query.py:194-200` 已有机制)。
- veto 条件:**(a)** 终答文本声称做过执行/分析 **且 (b)** 本会话历史(`state.messages`)零成功 tool_use。
  - (a) claims 检测:curated 中英短语/正则集 v1(中:已运行/已执行/已对接/已折叠/已计算/结果显示/结果为/得分/亲和力/打分;英:ran/executed/docked/folded/computed/results show/score is/affinity)。先小而精,后续可扩。
  - (b) 证据检测:扫历史 tool_result,有无 `ok=True`(非 is_error)的工具调用。零 → 无证据。
- 命中 → `veto=True`,message 注入纠正:"你声称已执行/分析,但本轮及历史未真正调用任何工具拿到结果。请先调用 BrainQuery/SkillExec 等工具取得真实数据后再作答。" → query.py `continue` 重走一轮。
- **防循环**:`State` 加计数(如 `stop_hook_veto_count`),**最多 veto 1 次**;之后即便仍命中也放行(maxTurns/recovery_budget 兜底,体例同 query.py:190 "宁松勿死循环")。

### 4.4 `SkillExec.rmcp_op` 修正
`"execute"` → `"call_skill"`,对齐 `ALLOWED_OPS[Phase.EXECUTE]` 与 `test_brains_retrieve_first.py` 约定。消除 latent bug(`RetrieveFirstPermission` 按 `!=None` 判,本身鲁棒,但对齐为正确)。

### 4.5 `AgentTool` 描述强化
工具描述(模型可见)补充:"本工具只返回 spawn 描述符、不自动 fork 子 agent;返回成功不代表子 agent 已完成分析。" 堵风险点①措辞误导。仅改描述文案,不改 run() 行为。

## 5. 数据流

```
用户问
  → 模型(未检索就想 call_skill)
      → RetrieveFirstPermission: phase==INIT → DENY + "检索先行"诊断
  → 模型自补 BrainQuery
      → 真命中(degraded_to_bare=False, source=filesystem)
      → on_tool_results 回调 → advance_phase(INIT→RETRIEVE)
  → 模型再 call_skill
      → RetrieveFirstPermission: phase!=INIT → ALLOW → 真执行
  → 终答前 stop_hook:
      声称执行 + 零成功 tool_use? → veto(≤1 次)+ 注入纠正 → 重走一轮
      否则 → STOP 放行
```

## 6. 边界 / 错误处理

- 空/fixture/降级检索 → 不推进相位 → execute 仍被拒(科学严谨不失守)。
- 纯概念问答(不声称执行)→ stop_hook 不 veto(保守,低误杀)。
- veto 至多 1 次,防死循环;maxTurns/recovery_budget 兜底。
- `rmcp_op == None` 的工具(BrainQuery/FileRead/WebFetch/Bash/AgentTool)全程透传 ALLOW → 不影响既有行为(全量零回归基础)。
- claims 短语集 v1 召回有限是可接受取舍(漏网的"可以用 X 方法"不算声称);精度优先,避免误杀。

## 7. 测试策略

**单测**
- `RetrieveFirstPermission` DENY/ALLOW 矩阵:INIT+rmcp_op→DENY;RETRIEVE+rmcp_op→ALLOW;rmcp_op=None→ALLOW;base DENY/ASK 优先返回。
- 推进信号:BrainQuery 真命中 results → 推进 RETRIEVE;fixture/空命中 → 不推进(execute 仍 DENY);幂等(二次命中不 double-advance / 不 PhaseError)。
- stop_hook:声称执行+零工具→veto;声称执行+有成功工具→放行;纯概念无声称→放行;veto 计数≤1。
- `SkillExec.rmcp_op == "call_skill"`;AgentTool 描述含"不自动 fork"。

**回归**:全量 `pytest`(`--ignore=tests/integration`)零失败。

**staging e2e**(controller 亲做):
- 黄金链路:对话先检索后对接 → call_skill 放行 → 真 JSON(不回归 GAP-E2E)。
- 裸执行:诱导未检索直接要求对接 → 被门 DENY,模型自补检索后成功。
- "只说不做":诱导模型不调工具直接声称已对接出分 → stop_hook veto → 补调工具。
- 反幻觉 KPI(`eval_v0160.py`)复跑:A+B≥80% / C≤10% / D=0 / S-FAIL=0(确认接线不引入回归;基线本会话已测 91%/9%/0%/0)。

## 8. 验收标准

- GAP-AH-1:① chat 权限链串入 `RetrieveFirstPermission`(与 BashCommandPolicy/BridgePermissionAdapter 组合);② 未检索调 `rmcp_op != None` 工具 → DENY + 诊断;③ 单测覆盖 DENY/ALLOW 矩阵;④ 全量零回归;⑤ SkillExec.rmcp_op 对齐;⑥ AgentTool 描述强化。
- GAP-AH-2:① `app.py` 调 `query()` 传 stop_hook;② 声称执行+零证据终答被 veto 并强制再走一轮;③ 单测覆盖 veto/放行各案 + 防循环;④ staging 真实对话验证 veto 后补调工具。

## 9. 预计触及文件

- `praxis2/tools/permission.py`(新增 `RetrieveFirstPermission`)
- `praxis2/core/query.py`(新增 `on_tool_results` 回调点)
- `praxis2/server/app.py`(权限链串 `RetrieveFirstPermission`、注入推进回调、传 stop_hook)
- `praxis2/hooks/`(新 `tool_use_presence` stop_hook + claims 检测助手)
- `praxis2/core/state.py`(`stop_hook_veto_count` 计数字段)
- `praxis2/tools/skill_exec.py`(`rmcp_op` 修正)
- `praxis2/agents/agent_tool.py`(工具描述)
- 对应 `tests/`

## 10. 风险 / 待定

- claims 短语集精度:v1 小而精,可能漏部分声称;通过 staging KPI + 人工复核 C/D 样本迭代。
- 推进信号识别 BrainQuery 的方式(按工具名 vs 结果 shape):倾向按结果 shape(`degraded_to_bare`/`source`)+ 工具名双重确认,plan 阶段定细节。
- `on_tool_results` 回调注入是否改动 `query()` 既有 SSE 行为:回调只读 state + results、不产事件,零行为变更;单测断言。
