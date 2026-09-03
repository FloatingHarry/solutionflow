# Enterprise Solution Copilot — Development Plan

## 1. 项目定位

项目名称暂定：

**Enterprise Solution Copilot**  
**企业级 AI 客户洞察与解决方案工作台**

这是一个面向 **B2B Solution Consultant / GTM / Enterprise Sales / AI Product** 的 AI 工作流系统。

核心目标不是做一个通用聊天机器人，而是把企业客户从：

**Account Research → Opportunity Discovery → Customer Discovery → Solution Design → POC → Evaluation → Deployment / Business Case**

整个流程结构化，并保证每一个结论都可以向前追踪到：

**Source / Evidence → Hypothesis → Confirmed Need → Solution → POC → Result → Decision**

AI 负责辅助研究、分析和方案生成，人负责关键确认和决策。

---

## 2. 产品核心价值

普通 ChatGPT/Claude 可以回答：

> “分析一下 Company X。”

本产品需要解决的是一个完整的企业售前工作流：

1. 搜集企业公开资料；
2. 建立 Account Profile；
3. 提出潜在业务机会 Hypothesis；
4. 为用户生成 Discovery Questions；
5. 记录用户与客户沟通后得到的真实需求；
6. 将需求匹配到内部 AI Solution；
7. 生成 Solution Architecture；
8. 生成 POC Plan；
9. 记录 POC Evaluation；
10. 形成部署建议、成本及 ROI；
11. 保留完整 Traceability。

最终产品应该更像一个：

**AI-native Enterprise Solution Workspace**

而不是聊天框。

---

## 3. MVP 用户场景

第一版只服务一个核心用户：

### AI Solution Consultant / Enterprise GTM

场景：

> 用户明天需要拜访 Company X，希望快速研究客户、找到潜在 AI 场景，并形成初步 Solution / POC Proposal。

用户进入系统：

**Create Account → 输入公司名称 → Research → Review → Discovery → Solution → POC**

最终得到完整的 Account Workspace。

---

## 4. 核心 Workflow

整个系统围绕以下状态流转：

```text
Account Created
↓
Research
↓
Opportunity Hypothesis
↓
Discovery
↓
Confirmed Need
↓
Solution Design
↓
POC
↓
Evaluation
↓
Deployment / Business Case
```

每个 Account 都必须能够显示当前阶段。

例如：

```text
Research ✅
Discovery ✅
Solution ✅
POC 🟡
Deployment ⚪
```

---

## 5. Phase 1 — Account Research

用户创建一个 Account：

```text
Company Name
Website
Industry
Region
Optional Notes
```

例如：

```text
Company: Example Retail UK
Industry: Retail
Region: UK
```

系统调用 Research Agent。

Research Agent 使用：

- Web Search
- Company Website
- Annual Report / PDF
- News
- Other public sources

生成结构化：

### Company Profile

```text
Company Overview
Products / Services
Market / Geography
Customers
Recent Developments
Financial / Operating Signals
AI / Digital Initiatives
Potential Strategic Priorities
```

### 关键要求

任何事实性信息尽量带：

```text
Source
URL
Retrieved Date
Supporting Text
```

UI 中重要结论显示 Citation。

不要让 LLM 无依据生成企业事实。

---

## 6. Phase 2 — Opportunity Discovery

根据 Research 结果生成：

### Opportunity Hypothesis

每个 Hypothesis 必须是结构化对象：

```text
title
description
evidence[]
confidence
business_area
potential_impact
status
```

例如：

```text
Hypothesis:
Internal knowledge retrieval may be inefficient.

Evidence:
- Rapid expansion across multiple European markets
- Increasing number of support / operations roles

Confidence:
Medium

Status:
AI Suggested
```

注意：

**Hypothesis ≠ Confirmed Need**

必须明确区分。

状态包括：

```text
AI Suggested
User Accepted
User Rejected
Need Validation
Confirmed
```

---

## 7. Phase 3 — Customer Discovery

针对 Hypothesis 自动生成 Discovery Questions。

例如：

```text
How do employees currently find internal policy information?
How long does it usually take?
Which information sources are involved?
What data cannot leave the EU?
How many employees perform this task?
What is the current cost?
```

用户可以：

- 编辑问题；
- 添加问题；
- 删除问题；
- 记录 Customer Answer；
- 将 Hypothesis 标记为 Confirmed / Rejected。

形成：

```text
Hypothesis
↓
Discovery Question
↓
Customer Answer
↓
Confirmed Need
```

这是整个 Traceability 的关键节点。

---

## 8. Phase 4 — Solution Knowledge Base

系统内部建立一个**模拟企业 AI Solution Catalog**。

明确标注这是：

**Demo / Simulated Solution Catalog**

第一版只需要 4 个 Solution：

### Enterprise Knowledge Assistant

RAG 企业知识库。

### Customer Service Copilot

客服辅助。

### Sales / Account Copilot

销售及客户研究辅助。

### Document Intelligence

文档解析、信息提取及工作流自动化。

每个 Solution 包含：

```text
solution_name
description
target_pain_points
target_industries
required_data
architecture
deployment_options
success_metrics
known_limitations
estimated_cost_model
example_use_cases
```

未来支持用户上传：

- Product Documentation
- Solution Deck
- Pricing
- Customer Cases
- Technical Documents

形成真正的 Internal Knowledge Base。

---

## 9. Phase 5 — Solution Design Agent

只有在存在 Confirmed Need 后，才能生成正式 Solution。

输入：

```text
Account Profile
Evidence
Confirmed Needs
Internal Solution Knowledge Base
Constraints
```

输出：

```text
Recommended Solution
Why This Solution
Mapped Customer Need
Architecture
Required Data
Model / Tool Requirements
Deployment Option
Security / Compliance Considerations
Risks
Expected Business Impact
```

每个 Solution 必须保存：

```text
derived_from_need_ids[]
```

从 Solution 可以反向点击到：

**Confirmed Need → Discovery Answer → Hypothesis → Evidence → Original Source**

这是项目最重要的能力之一。

---

## 10. Deployment Options

Solution Agent 第一版需要支持三种方案比较：

```text
SaaS / API
EU Cloud Deployment
Private / On-premise Deployment
```

从以下维度比较：

```text
Cost
Implementation Difficulty
Data Privacy
Scalability
Maintenance
Latency
Compliance
```

不要求做真正复杂的云基础设施。

MVP 重点是：

**Solution Design + Trade-off Analysis**

---

## 11. Phase 6 — POC Generator

系统根据 Solution 自动生成 POC Plan。

结构：

```text
POC Objective
Business Problem
Scope
Required Data
Architecture
Timeline
Evaluation Dataset
Success Metrics
Risk
Expected Output
```

例如：

```text
Goal:
Reduce internal knowledge retrieval time.

Dataset:
100 internal documents.

Evaluation:
100 representative questions.

Metrics:
Answer Accuracy
Citation Accuracy
Task Success Rate
Latency
Cost per Query
```

POC 默认时间：

```text
2 weeks
```

但允许编辑。

---

## 12. Phase 7 — Evaluation

用户可以录入 POC 实际结果。

第一版支持：

```text
Task Success Rate
Answer Accuracy
Citation Accuracy
Hallucination Rate
Latency
Cost per Task
Human Rating
```

系统显示：

```text
Target
Actual
Pass / Fail
```

例如：

```text
Citation Accuracy

Target: > 90%
Actual: 93%

PASS
```

最终生成：

```text
Proceed
Iterate
Reject
```

Decision。

Decision 必须保留原因。

---

## 13. Phase 8 — Business Case / ROI

加入一个 Scenario-based ROI Calculator。

注意：

这是估算工具，不是真实业务结果。

输入：

```text
Number of Employees
Average Hourly Cost
Current Time per Task
Tasks per Month
Expected Time Reduction
LLM / Infrastructure Cost
```

计算：

```text
Current Monthly Cost
Estimated New Cost
Monthly Savings
Annual Savings
AI Operating Cost
Estimated ROI
Payback Period
```

页面明确显示：

**Scenario Estimate**

避免把模拟结果呈现成真实客户收益。

---

## 14. 最终 Account Workspace

Account 详情页是产品最核心页面。

建议结构：

```text
Company X

Overview
Research
Discovery
Solutions
POC
Evaluation
Business Case
Activity
```

顶部：

```text
Research ✅
Discovery ✅
Solution ✅
POC 🟡
Deployment ⚪
```

Overview 页面展示：

```text
Company Summary
Top Opportunities
Confirmed Needs
Recommended Solutions
Current POC
Latest Decision
```

---

## 15. Traceability

这是项目的核心产品能力。

必须建立：

```text
Source
↓
Evidence
↓
Hypothesis
↓
Discovery Question
↓
Customer Answer
↓
Confirmed Need
↓
Solution
↓
POC
↓
Evaluation
↓
Decision
```

任何 Solution 都应该能够回答：

> Why did we recommend this?

任何 Need 都能回答：

> Where did this need come from?

任何 AI Generated Claim 都应该尽量回答：

> What evidence supports this?

不要只保存最终生成文本。

---

## 16. Human-in-the-loop

关键节点必须要求用户确认。

推荐状态：

```text
AI Generated
Human Reviewed
Human Confirmed
Human Rejected
```

特别是：

- Opportunity Hypothesis
- Confirmed Need
- Solution Recommendation
- POC Decision

不能由 Agent 自动完成整个销售决策。

---

## 17. Agent Architecture

MVP 不需要大量 Agent。

只实现三个：

### Research Agent

负责：

```text
Search
Web/PDF Retrieval
Information Extraction
Evidence Collection
Company Profile
```

### Business Diagnosis Agent

负责：

```text
Analyze Evidence
Generate Opportunity Hypotheses
Generate Discovery Questions
```

### Solution Agent

负责：

```text
Match Confirmed Needs
Retrieve Internal Solution Knowledge
Generate Architecture
Generate POC
Generate Business Case
```

通过 LangGraph Workflow 编排。

不要为了 Multi-Agent 而增加 Agent 数量。

---

## 18. 技术栈

优先使用熟悉的技术：

### Frontend

```text
Next.js
React
TypeScript
```

### Backend

```text
Python
FastAPI
```

### Agent

```text
LangGraph
```

### Database

优先：

```text
PostgreSQL
```

如果开发效率更高，可使用：

```text
Supabase
```

### AI

抽象 Model Provider Layer。

至少能够支持未来切换：

```text
OpenAI
Anthropic
Chinese LLM Provider
```

不要把业务逻辑直接写死在单一模型 API 中。

---

## 19. RAG / Search

需要两种 Knowledge：

### External Knowledge

真实企业公开资料。

### Internal Knowledge

模拟 AI Solution Catalog / 上传资料。

两者严格区分。

Solution Agent 主要依据：

```text
External Customer Evidence
+
Internal Solution Knowledge
```

完成匹配。

---

## 20. 数据模型

至少设计以下实体：

```text
Account
Source
Evidence
Hypothesis
DiscoveryQuestion
DiscoveryAnswer
Need
SolutionTemplate
SolutionProposal
POC
Evaluation
Decision
Activity
```

实体之间建立明确 foreign key / relation。

不要把整个 Account 保存成一个巨大 JSON。

结构化数据库本身也是该项目的重要部分。

---

## 21. Activity / Audit Trail

任何关键动作写入 Activity Log：

```text
Research Generated
Hypothesis Accepted
Hypothesis Rejected
Discovery Answer Added
Need Confirmed
Solution Generated
Solution Modified
POC Started
Evaluation Updated
Decision Made
```

形成 Timeline。

例如：

```text
Sep 03
Account created

Sep 03
Research completed

Sep 04
Hypothesis #2 confirmed

Sep 05
Solution #1 generated

Sep 10
POC evaluation updated
```

体现整个 Workflow 的可追踪性。

---

## 22. Evaluation System

项目本身还需要一个系统级 Evaluation。

选择约 5–10 家真实企业作为 Demo Account。

构造 30–50 个 evaluation tasks。

评估：

```text
Research factual accuracy
Citation correctness
Evidence completeness
Hypothesis relevance
Solution relevance
Hallucination rate
Task completion rate
Latency
Cost
```

后期可以比较：

```text
Model A
vs
Model B
```

或者：

```text
Simple Prompt
vs
Workflow Agent
```

这是该项目区别于普通 Demo 的重要部分。

---

## 23. 第一版不要做的功能

MVP 暂时不要做：

```text
CRM Integration
Salesforce Integration
Complex RBAC
Real billing
Automatic customer outreach
Automatic loan decisions
Investment recommendations
Full enterprise SSO
Complex multi-tenant architecture
Real production compliance certification
```

先保证核心 Workflow 完整。

---

## 24. UI 原则

不要把整个产品设计成 ChatGPT clone。

主要 UI 应该是：

**Workspace + Cards + Workflow + Timeline**

聊天可以作为辅助功能。

视觉上偏：

```text
Linear
Notion
HubSpot
Enterprise SaaS Dashboard
```

强调：

- 信息结构；
- 状态；
- Evidence；
- Traceability；
- Workflow。

---

## 25. 建议开发顺序

### Phase 1

先完成：

```text
Database schema
Account CRUD
Account Workspace
Workflow status
Activity log
```

暂时不接 LLM。

确保业务模型成立。

### Phase 2

完成：

```text
Research Agent
Web Search
Source
Evidence
Citation
Company Profile
```

### Phase 3

完成：

```text
Hypothesis
Discovery Question
Human Review
Customer Answer
Confirmed Need
```

### Phase 4

完成：

```text
Solution Knowledge Base
Solution Matching
Solution Proposal
Traceability
```

### Phase 5

完成：

```text
POC
Evaluation
Decision
```

### Phase 6

完成：

```text
ROI Calculator
Deployment Recommendation
Final Account Brief
```

### Phase 7

完成：

```text
Deployment
System Evaluation
Demo Accounts
UI polish
README
Architecture Diagram
```

---

## 26. MVP 完成标准

当满足以下条件时，可以认为项目已经达到简历展示标准：

- 有真实可访问 Web App；
- 可以创建 Account；
- 可以研究真实公司；
- 重要企业信息带 Citation；
- 可以生成 Hypothesis；
- 用户可以 Confirm / Reject；
- 可以记录 Discovery Answers；
- 可以生成 Confirmed Need；
- Need 可以映射到 Solution；
- 可以自动生成 POC；
- 可以录入 Evaluation；
- 有 ROI Scenario；
- 有完整 Timeline；
- Solution 可以反向追踪到 Evidence；
- 至少存在 5 个完整 Demo Accounts；
- 有基础系统 Evaluation；
- 有 README + Architecture Diagram。

---

## 27. 开发原则

1. **Workflow first, Agent second.**  
   先做完整业务流程，再嵌入 AI。

2. **Structured data over long text.**  
   尽量使用 schema / structured output，不要让 Agent 返回无法管理的大段文本。

3. **Evidence first.**  
   AI 生成企业事实时必须尽可能有 Source。

4. **Human confirmation for important decisions.**  
   AI 提建议，人做决策。

5. **Traceability by design.**  
   所有实体之间保留来源关系。

6. **Build MVP before optimization.**  
   第一目标是完整跑通：

```text
Company
→
Research
→
Need
→
Solution
→
POC
→
Evaluation
```

不要一开始过度工程化。

---

## 28. Codex 当前任务

请先不要直接开始大量写代码。

第一步：

**检查当前 repository。**

然后输出：

```text
1. Existing repository structure
2. Existing reusable components
3. Proposed architecture
4. Proposed database schema
5. Proposed route/page structure
6. Proposed API structure
7. Phase 1 implementation plan
8. Potential technical risks
```

确认整体架构合理后，再实施 Phase 1。

开发过程中，每完成一个 Phase：

- 确保可以运行；
- 检查 TypeScript / Python errors；
- 增加必要测试；
- 更新 README；
- 不破坏已经完成的 Workflow；
- 再进入下一阶段。
