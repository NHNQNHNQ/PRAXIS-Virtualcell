# 03 · 论文定稿方案 —— 引用核验(联网搜索为核心)+ 收尾

> 接 `02_review_and_revision.md`。manuscript v0.1 草稿(577 行)已写完并过 5 审稿人对抗审查 + revision,
> 5 张 Nature 风格图(Fig1–5,4 格式)已出齐。本方案聚焦把论文推到**可投稿**状态,核心是把
> 13 个 `[CIT:key]` 占位解析成真实可核验文献,并完成参考文献组装 / 内容补强 / 质量门 / 输出。

## 0. 技术路线前置(已确认)

- **文献 MCP 全部未连接**:PubMed / CrossRef / arXiv / Semantic Scholar MCP 不可用(ToolSearch 已验)。
- **可用通道**:`WebSearch`(发现)+ `WebFetch`(取 CrossRef REST API JSON / 出版商页)。
- **核验引擎 = CrossRef REST API**:
  `https://api.crossref.org/works?query.bibliographic=<标题词+>&rows=3&select=DOI,title,author,container-title,issued,volume,issue,page,article-number,type`
  → WebFetch 用 prompt 让小模型从 JSON 抽最佳匹配的完整元数据 + DOI。
- **限流对策**:public pool 易 429(本会话 6 并发即触发)。规则:**并发 ≤3**;给 URL 加
  `&mailto=<可公开邮箱>` 进 CrossRef polite pool 提速;429 则退避重试。
- **防幻觉铁律**:DOI 只采信 CrossRef / 出版商真实返回;查不到就标 `UNVERIFIED` 留给人工,**绝不臆造 DOI/卷期页**。

## 1. 引用核验与发现(联网搜索核心阶段)

13 个 key 分三类处理。**确定型**直接 CrossRef 核验;**发现型**先 WebSearch 定位确切论文再 CrossRef/出版商核验;
全程双源(CrossRef DOI + 出版商落地页)交叉确认存疑项。

### 1A 确定型 —— 直接 CrossRef 核验(本会话已完成 6/7)

| key | 文献 | 状态 | DOI |
|---|---|---|---|
| virtual-cell | Bunne et al., How to build the virtual cell with AI, *Cell* 2024;187(25):7045–7063 | ✅ | 10.1016/j.cell.2024.11.015 |
| Norman2019 | Norman et al., genetic interaction manifolds, *Science* 2019;365(6455):786–793 | ✅ | 10.1126/science.aax4438 |
| scGPT | Cui et al., scGPT, *Nat Methods* 2024;21(8):1470–1480 | ✅ | 10.1038/s41592-024-02201-0 |
| GEARS | Roohani et al., GEARS, *Nat Biotechnol* 2024;42(6):927–935 | ✅ | 10.1038/s41587-023-01905-6 |
| CPA | Lotfollahi et al., CPA, *Mol Syst Biol* 2023;19(6):e11517 | ✅ | 10.15252/msb.202211517 |
| Geneformer | Theodoris et al., Geneformer, *Nature* 2023;618(7965):616–624 | ✅ | 10.1038/s41586-023-06139-9 |

> GEARS 在线 2023、卷 42 对应 2024;参考表按卷年记 2024,正文不受影响。

### 1B 确定型待确认 —— CrossRef 二次核验(3 条)

| key | 候选文献 | 待确认点 |
|---|---|---|
| selective-prediction | Geifman & El-Yaniv, *Selective classification for DNN*, NeurIPS 2017;或 El-Yaniv & Wiener, *JMLR* 2010 | NeurIPS 老论文 CrossRef 常无 DOI;本会话查到 SelectiveNet(ICML 2019)。需定哪篇为代表作并取到 DOI(JMLR 2010 有 DOI 更稳)。 |
| applicability-domain | Sahigara et al., *Comparison of approaches to define AD of QSAR models*, *Molecules* 2012 | CrossRef 核 DOI/卷期。 |
| AI-trust | Wang et al., *Scientific discovery in the age of AI*, *Nature* 2023 | CrossRef 核 DOI;确认与正文"科学 ML 可信"语境贴合。 |

### 1C 发现型 —— WebSearch 定位 → 核验(4 条)

这些 key 指向"一类工作",需先用 WebSearch 选定**确切那一篇**(看 manuscript 语境),再核验:

| key | 正文语境(manuscript 行) | WebSearch 检索方向 |
|---|---|---|
| STATE | L115 "and STATE predict expression change" | Arc Institute "State" perturbation/virtual-cell 模型(2025,bioRxiv/正刊);确认是否已正式发表,preprint 则标 preprint+DOI。 |
| foundation-models | L83 "Foundation models are useful…" 讲单细胞 FM 局限 | 单细胞基础模型**评测/批评**论文(如 zero-shot 局限类);选与"非银弹"论点一致的一篇。 |
| abstention | L76 "an explicit 'I cannot answer'" | reject option / abstention 经典或综述(Chow 1970;或 Hendrickx et al. *Machine learning with a reject option: a survey* 2024)。 |
| multi-agent-llm | L124 "multi-agent and tool-using LLM systems" | 代表作或综述(AutoGen;Generative Agents;或 LLM multi-agent survey)——选与"可选 LLM agent"定位呼应的。 |

**1C 操作规范**:每条 ① WebSearch 得候选标题+出处 → ② CrossRef API 按标题核 DOI/元数据 → ③ 存疑则 WebFetch 出版商落地页二次确认 → ④ 仍无 DOI(纯 preprint/会议)则记 arXiv/会议号并标注类型,不伪造。

### 1D 时效性扫描(降 desk-reject 风险,可选但推荐)

现在是 2026-06,虚拟细胞/扰动预测领域更新极快。用 WebSearch 扫一遍 2025–2026 的**强相关竞品/新基准**
(virtual cell、perturbation prediction、multi-agent for science),确认:① Related Work 没漏掉关键新工作(R3 devil's advocate 关注点);② 没有更该对标的外部 baseline。命中则补 1–2 条进 Related Work / Limitations,**不强行塞**。

## 2. 参考文献组装 + 正文编号

- 目标格式:**Nature Methods 数字引用**(按正文首次出现顺序编号)。
- 步骤:① 13 条核验结果按首现顺序排号 → ② 正文 `[CIT:key]` 批量替换为 `[n]`(同一 key 复用同号)→
  ③ manuscript 末尾 519–535 行的占位清单替换为正式 **References** 列表 → ④ 清掉 2 处 `[CIT:key]` 模板残留(L519、L8 示例)。
- 校验:每个正文编号在 References 有对应;每条 Reference 至少被引一次;无残留 `[CIT:`。

## 3. Related Work / 内容补强(基于已核验文献)

- 用真实引用把 Related Work 三条线坐实:selective prediction / reject option(1B)、applicability domain(1B)、
  multi-agent LLM(1C);foundation-model 局限(1C)接 Discussion"非银弹"论点。
- 若 1D 命中新竞品,补一句定位 + 引用。
- 维持 02 review 的诚实边界,**不因补引用而 over-claim**。

## 4. 质量门(投稿前)

- **引用一致性**:`ars-citation-check`(ARS)或 `nature-citation` 复核 —— 孤儿引用 / 漏引 / key-编号错配 / DOI 格式。
- **数字保真**:抽查每个定量 claim 仍可溯源到 `docs/findings/`(沿用 02 的 number-fidelity 标准,防回归)。
- **诚实边界**:Limitations 逐条仍在(manifest 缺失 / abstain_gain 未做 / mock 不激活 / scGPT frozen / 无外部 baseline)。

## 5. 输出与收尾

- **格式转换**:`ars-format-convert` → LaTeX + DOCX(via pandoc),投稿备用;图引用对齐 Fig1–5。
- **顺手修**:`docs/RELEASE-v0.1.0.md` 测试数 71 → 75(R12 已 flag);RELEASE/manuscript 口径统一。
- **入库**:`find docs -name '._*' -delete` 后,`git add docs/paper/ && commit`(整目录尚未跟踪),
  commit message 末尾带 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。

## 6. 工具与 skill

- 检索/核验:`nature-academic-search`(本方案所在 skill;CrossRef API + WebSearch 路线)。
- 引用 QA:`academic-research-skills:ars-citation-check`。
- 补引(如需给新段落找支撑):`nature-citation`。
- 格式:`ars-format-convert`。**不**调用未连接的 PubMed/CrossRef MCP。

## 7. 风险与对策

| 风险 | 对策 |
|---|---|
| CrossRef 429 限流 | 并发 ≤3 + mailto polite pool + 退避重试(本会话已踩) |
| 幻觉 DOI/卷期 | 双源核验;查不到标 UNVERIFIED 交人工;绝不臆造 |
| 概念性引用多候选(abstention/multi-agent) | 由 manuscript 语境选定;仍歧义则问用户 |
| 新领域时效(STATE 2025 / 2026 新竞品) | 1D WebSearch 时效扫描 |
| preprint 无正式 DOI | 记 arXiv/bioRxiv DOI + 标 preprint,不冒充正刊 |

## 8. 执行顺序与预估

1. **Phase 1**(联网搜索核心):1B 3 条 + 1C 4 条核验 + 1D 扫描 → 13 条全部 verified/标注。**本阶段最重**。
2. **Phase 2**:组装 References + 正文编号 + 清残留。
3. **Phase 3**:Related Work 补强。
4. **Phase 4**:citation-check + number-fidelity 质量门。
5. **Phase 5**:format-convert + RELEASE 修数 + commit。

> 工作量集中在 Phase 1 的 7 条剩余核验(约一半需 WebSearch 发现)。Phase 2–5 为机械整合 + QA。
> 全程联网仅用于**文献核验/发现**,不向外发布任何内容。
