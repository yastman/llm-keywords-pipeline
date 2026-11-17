"""Cluster slugs in generate/checklists are prefixed with their L3 slug (audit B20)."""

from __future__ import annotations

import sys

from llm_keywords_pipeline.generate import checklists

STRUCTURE = """\
##### 🏷️ L3: Shampoo (Vol: 100)
###### 📦 Cluster: Red (Vol: 10)
| red shampoo | 10 |
##### 🏷️ L3: Wax (Vol: 50)
###### 📦 Cluster: Red (Vol: 5)
| red wax | 5 |
"""

STRUCTURE_NO_L3 = """\
#### 📁 L2: Care (Vol: 200)
###### 📦 Cluster: Red (Vol: 10)
"""


def _setup(tmp_path, monkeypatch, structure: str):
    structure_file = tmp_path / "STRUCTURE.md"
    structure_file.write_text(structure, encoding="utf-8")
    tasks = tmp_path / "tasks"
    monkeypatch.setattr(checklists, "BASE_DIR", tmp_path)
    monkeypatch.setattr(checklists, "STRUCTURE_FILE", structure_file)
    monkeypatch.setattr(checklists, "TASKS_DIR", tasks)
    monkeypatch.setattr(checklists, "MASTER_CHECKLIST_FILE", tmp_path / "MASTER.md")
    monkeypatch.setattr(checklists, "PIPELINE_STATUS_FILE", tmp_path / "PIPELINE.md")
    return structure_file, tasks


def test_same_name_clusters_under_different_l3_get_distinct_slugs(tmp_path, monkeypatch):
    structure_file, _ = _setup(tmp_path, monkeypatch, STRUCTURE)

    nodes = checklists.parse_structure(structure_file)

    clusters = [n["slug"] for n in nodes if n["type"] == "Cluster"]
    assert clusters == ["shampoo-red", "wax-red"]


def test_cluster_without_l3_keeps_plain_slug(tmp_path, monkeypatch):
    structure_file, _ = _setup(tmp_path, monkeypatch, STRUCTURE_NO_L3)

    nodes = checklists.parse_structure(structure_file)

    assert [n["slug"] for n in nodes if n["type"] == "Cluster"] == ["red"]


def test_reset_writes_task_per_cluster_and_reads_prefixed_category_dir(tmp_path, monkeypatch):
    _, tasks = _setup(tmp_path, monkeypatch, STRUCTURE)
    tasks.mkdir()
    (tasks / "red.md").write_text("old", encoding="utf-8")
    cat = tmp_path / "categories/shampoo-red"
    (cat / "data").mkdir(parents=True)
    (cat / "data/shampoo-red_clean.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["checklists", "--reset"])

    checklists.main()

    assert sorted(p.name for p in tasks.glob("*.md")) == [
        "shampoo-red.md",
        "shampoo.md",
        "wax-red.md",
        "wax.md",
    ]
    master = (tmp_path / "MASTER.md").read_text(encoding="utf-8")
    shampoo_red = next(line for line in master.splitlines() if "`shampoo-red`" in line)
    wax_red = next(line for line in master.splitlines() if "`wax-red`" in line)
    # Init column: the cluster's category dir is categories/{l3}-{cluster}.
    assert shampoo_red.split("|")[8].strip() == "✅"
    assert wax_red.split("|")[8].strip() == "⬜"
    pipeline = (tmp_path / "PIPELINE.md").read_text(encoding="utf-8")
    assert "- shampoo-red (Meta)" in pipeline
    assert "- wax-red (Meta)" in pipeline
