# Paper Agent

## 关于 Paper Agent

Paper Agent 是一款面向科研文献场景的本地优先研究代理系统，覆盖的核心场景包括论文检索、论文解析、分块索引、检索增强问答、研究流程编排、聚类分析、综述生成与 Markdown 导出。  
`02delivery` 对应第二周交付版本，重点完成完整框架落地、测试与 CI 补齐、GitHub 可发布化整理。

## 文档

设计文档请见项目设计稿：

+ [Paper_Agent_设计文档_20260310_ZXY_V02](../Paper_Agent_设计文档_20260310_ZXY_V02.md)

部署演示说明路径如下：

+ [Deploy/server_demo.md](./Deploy/server_demo.md)

演示脚本路径如下：

+ [Example/demo_cli.sh](./Example/demo_cli.sh)

版本发布说明：

+ [RELEASE_NOTES_v0.2.0.md](./RELEASE_NOTES_v0.2.0.md)

## 主要概念

+ Project（研究项目）：Project 是文献研究任务的顶层对象，用于组织研究问题、候选论文、索引结果、问答结果、聚类结果、综述结果和导出产物。

+ Agent（功能代理）：Agent 是各个功能模块的具体实现，当前 `02delivery` 已实现 `SearchAgent`、`ParseAgent`、`IndexAgent`、`QAAgent`、`ClusterAgent`、`ReportAgent`、`LibrarySyncAgent`。

+ Workflow（研究工作流）：Workflow 是基于 LangGraph 编排的执行流，当前版本已支持 `检索 -> 解析 -> 索引 -> 问答 / 聚类 / 综述 / 导出` 的完整工程骨架。

+ Store / DAO（存储与访问层）：Store 负责底层存储适配，DAO 负责业务数据读写，当前已接入 `SQLite + ChromaDB`，并对 `run / cluster / analysis` 等对象做了独立持久化。

+ Evidence Pack（证据包）：Evidence Pack 是从混合检索结果中构建出的问答证据集合，用于生成带引用的回答内容。

## 使用了哪些技术

+ FastAPI

+ LangGraph

+ AutoGen

+ Ollama

+ ChromaDB

+ SQLite / SQLite FTS5

+ Gradio

+ Pydantic

+ CLI 工具链

+ GitHub Actions CI

## 支持的核心模块及实现

|模块|功能|实现|是否已支持|
|:---:|:---:|:---:|:---:|
|接口层|HTTP API 服务|FastAPI|是<input type="checkbox" checked>|
|工作流层|研究流程编排|LangGraph|是<input type="checkbox" checked>|
|检索层|论文检索|ArXiv Client|是<input type="checkbox" checked>|
|解析层|文本/文件解析|本地解析服务|是<input type="checkbox" checked>|
|索引层|文档分块|Chunking Service|是<input type="checkbox" checked>|
|索引层|向量索引|ChromaDB|是<input type="checkbox" checked>|
|索引层|词法检索|SQLite FTS5|是<input type="checkbox" checked>|
|问答层|证据构建|Evidence Pack|是<input type="checkbox" checked>|
|问答层|问答生成|AutoGen + Ollama / Heuristic Fallback|是<input type="checkbox" checked>|
|分析层|主题聚类|Cluster Agent|是<input type="checkbox" checked>|
|分析层|综述生成|Report Agent|是<input type="checkbox" checked>|
|文献管理层|文献库同步/回写|Literature Manager + Zotero API|是<input type="checkbox" checked>|
|存储层|业务元数据存储|SQLite|是<input type="checkbox" checked>|
|导出层|研究结果导出|Markdown / JSON / CSV / BibTeX|是<input type="checkbox" checked>|
|界面层|本地工作台|Gradio|是<input type="checkbox" checked>|
|运行态|状态记录、checkpoint、artifacts|Workspace Store + Scheduler|是<input type="checkbox" checked>|
|工程化|自动化测试与 CI|Pytest + GitHub Actions|是<input type="checkbox" checked>|

## 支持的算法应用与功能场景

|应用场景|开放方式|功能|是否已支持|
|:---:|:---:|:---:|:---:|
|项目管理|CLI / API|创建研究项目、查看项目快照|是<input type="checkbox" checked>|
|论文检索|CLI / API|按关键词、作者、分类、年份检索论文|是<input type="checkbox" checked>|
|论文导入|CLI / API|导入文本论文、本地文件论文|是<input type="checkbox" checked>|
|文档解析|Workflow|解析文本、文件、PDF 类内容|是<input type="checkbox" checked>|
|索引构建|CLI / API / Workflow|执行 chunk 切分、向量入库、FTS 建库|是<input type="checkbox" checked>|
|项目问答|CLI / API / Workflow|执行项目内检索增强问答|是<input type="checkbox" checked>|
|主题聚类|CLI / API / Workflow|对项目论文进行主题聚类|是<input type="checkbox" checked>|
|综述生成|CLI / API / Workflow|生成聚类/项目级综述草稿|是<input type="checkbox" checked>|
|文献库同步|CLI / API / Workflow|同步 Zotero/Mendeley/EndNote 风格导出|是<input type="checkbox" checked>|
|文献 note 回写|CLI / API|将分析结果回写到文献库|是<input type="checkbox" checked>|
|自动路由|CLI / API|根据查询自动选择问答或工作流|是<input type="checkbox" checked>|
|运行管理|CLI / API|查询 run 状态、日志、恢复、取消|是<input type="checkbox" checked>|
|导出结果|CLI / API|导出 Markdown / JSON / CSV / BibTeX|是<input type="checkbox" checked>|
|端到端流程|CLI / API|执行 research workflow|是<input type="checkbox" checked>|

## 02delivery 版本实现内容

### 1. 完整工程骨架

+ 已完整落地 `api / workflow / agents / dao / store / ui` 分层
+ 已补齐统一配置管理、CLI 入口、服务入口、运行目录管理
+ 已补齐 `WorkflowScheduler`，支持异步执行与 worker 模式

### 2. 存储与模型接入

+ 已接入 `Ollama`
+ 已接入 `ChromaDB`
+ 已接入 `SQLite`
+ 已实现 SQLite FTS5 词法检索
+ 已实现 Ollama 不可用时的启发式降级
+ 已新增 cluster 持久化与文献管理对象接入

### 3. 完整闭环与新增能力

+ 已打通 `检索 -> 解析 -> 索引 -> 问答 -> Markdown 导出`
+ 已扩展到 `聚类 -> 综述 -> 多格式导出`
+ 已支持 ArXiv 检索与离线 fallback
+ 已支持本地文本导入和文件导入
+ 已支持 Literature Manager 同步与 Zotero note 回写
+ 已支持 auto route、resume、cancel、run logs
+ 已支持项目级 Markdown / JSON / CSV / BibTeX 导出

### 4. 测试与工程化

+ 已新增 `tests/` 测试目录
+ 已覆盖 API、导出、异步 run、PDF QA 回归
+ 已新增 GitHub Actions CI
+ 已新增发布材料、版本说明和推送说明

### 5. 当前交付目录结构

```text
02delivery/
├── README.md
├── pyproject.toml
├── requirements.txt
├── .github/
│   └── workflows/
│       └── ci.yml
├── Deploy/
│   └── server_demo.md
├── Example/
│   └── demo_cli.sh
├── tests/
│   ├── test_api_run_cancel.py
│   ├── test_exports_and_auto.py
│   ├── test_pdf_qa_quality.py
│   ├── test_run_async.py
│   └── fixtures/
│       └── pdfs/
├── paper_agent/
│   ├── __init__.py
│   └── __main__.py
└── Package/
    └── paper_agent/
        ├── api/
        ├── workflow/
        ├── agents/
        ├── dao/
        ├── literature/
        ├── models/
        ├── parsing/
        ├── rag/
        ├── retrieval/
        ├── store/
        ├── ui/
        └── utils/
```

## 如何获得 Paper Agent

建议在已有的 `conda` 环境 `paper-agent` 中运行：

```bash
conda activate paper-agent
cd /Users/3199489460qq.com/Desktop/Code_project/Paper-Agent/02delivery
```

当前版本采用 `pyproject.toml` 打包，可通过以下方式安装：

```bash
pip install -r requirements.txt
pip install -e .
```

说明：

- 当前环境若无法联网，`pip install` 可能因依赖下载受限失败
- 在这种情况下，可以直接使用源码方式运行 `python -m paper_agent ...`

## 启动方式

启动 API 服务：

```bash
python -m paper_agent serve --host 0.0.0.0 --port 8000
```

访问文档：

```text
http://127.0.0.1:8000/docs
```

启动本地 UI：

```bash
python -m paper_agent ui --host 0.0.0.0 --port 7860
```

运行 CLI 演示脚本：

```bash
conda run -n paper-agent bash Example/demo_cli.sh
```

运行测试：

```bash
pytest
```

## License

Paper Agent License

## ChangeLog

<details>
<summary>点击查看 ChangeLog</summary>

### Version-0.2.0
  - 完成完整分层工程结构：`api / workflow / agents / dao / store / ui`
  - 新增 `ClusterAgent`、`ReportAgent`、`LibrarySyncAgent`
  - 新增文献库同步、note 回写、auto route、cluster、review 能力
  - 新增 `WorkflowScheduler`，补齐异步 run、worker、resume、cancel、logs
  - 新增 Gradio UI 工作台
  - 新增 JSON / CSV / BibTeX 多格式导出
  - 新增测试目录、PDF fixture、GitHub Actions CI
  - 新增 GitHub 发布材料：`RELEASE_NOTES_v0.2.0.md`
  - 强化 PDF 解析，在低质量 PDF 上增加兜底恢复逻辑

### Version-0.1.0
  - 完成 Paper Agent V1 工程骨架
  - 完成 `FastAPI + LangGraph + AutoGen(可关闭)` 基础框架集成
  - 完成 `Ollama + ChromaDB + SQLite` 接入
  - 完成 ArXiv 检索与离线 fallback
  - 完成本地文本导入和文件导入
  - 完成解析、分块、向量索引、SQLite FTS5 混合检索
  - 完成项目内检索增强问答
  - 完成 Evidence Pack 构建与运行态产物落盘
  - 完成 Markdown 导出
  - 完成 CLI 演示脚本与服务器演示说明

</details>
