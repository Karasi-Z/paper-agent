from pathlib import Path

import pytest

from paper_agent.agents.qa_agent import QAAgent
from paper_agent.config import AppConfig
from paper_agent.models.entities import Evidence
from paper_agent.rag.evidence_pack import EvidencePackBuilder
from paper_agent.workflow.service import PaperAgentService


SAMPLE_PDF = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "pdfs"
    / "interactive_bilevel_method_sample.pdf"
)


def test_evidence_pack_handles_fts_only_items() -> None:
    builder = EvidencePackBuilder()
    evidence_list = builder.build(
        query="精确求解框架",
        ranked_item_list=[
            {
                "chunk_id": "chunk_1",
                "document": "An exact bilevel solution framework is developed and verified to achieve convergence.",
                "metadata": {
                    "paper_id": "paper_1",
                    "paper_title": "Sample Paper",
                    "section_title": "solution framework",
                },
                "distance": None,
                "score": 0.82,
            }
        ],
    )

    assert len(evidence_list) == 1
    assert evidence_list[0].final_score > 0


def test_qa_agent_follows_query_language() -> None:
    agent = QAAgent(llm_provider="none", llm_model="unused", ollama_base_url="http://127.0.0.1:11434")
    result = agent.answer(
        project_id="proj_1",
        query="这篇论文提出了什么精确求解框架？",
        evidence_list=[
            Evidence(
                paper_id="paper_1",
                chunk_id="chunk_1",
                paper_title="Sample Paper",
                section_title="solution framework",
                quote="An exact bilevel solution framework is developed which is verified to achieve convergence and obtain the bilevel optimality.",
                final_score=0.91,
            )
        ],
        paper_list=[],
    )

    assert result.content_md.startswith("# 回答")
    assert "论文提出了一个用于双层模型的精确求解框架" in result.content_md


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="Sample PDF is not available on this machine.")
def test_end_to_end_pdf_qa_on_sample_pdf(tmp_path: Path) -> None:
    config = AppConfig(
        data_dir=tmp_path / "paper_agent_data",
        llm_provider="none",
        embedding_provider="hash",
        parser_backend="auto",
    )
    service = PaperAgentService(config)
    project = service.create_project(name="sample-eval", question="验证 PDF 解析和问答质量")
    paper = service.import_file_paper(project.project_id, str(SAMPLE_PDF))

    assert "interactive decision making framework" in paper.title.lower()
    assert "more and more airlines outsource maintenance tasks" in paper.abstract.lower()
    assert "exact bilevel solution framework" in paper.content_text.lower()

    service.build_index(project.project_id)
    answer = service.ask(project.project_id, "这篇论文提出了什么精确求解框架？请用中文回答。", top_k=5)
    analysis = answer.payload

    assert analysis is not None
    assert analysis.content_md.startswith("# 回答")
    assert "双层模型的精确求解框架" in analysis.content_md
    assert "GSNCG" in analysis.content_md or "exact algorithm framework" in analysis.content_md.lower()
