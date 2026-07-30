import os
import json
import networkx as nx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GRAPH_DIR = os.path.join(BASE_DIR, "data", "graphs")


class MemoryGraph:
    def __init__(self, user_id: str):
        self.user_id = user_id
        os.makedirs(GRAPH_DIR, exist_ok=True)
        self.storage_path = os.path.join(GRAPH_DIR, f"{user_id}.json")
        self.graph = nx.DiGraph()
        self.load_graph()

    def add_document_node(self, doc_id: str, metadata: dict) -> list:
        """
        Adds a document node, links it to skills, and auto-links it to other
        documents that share skills (RELATES_TO). Returns related doc_ids
        so the caller can run causal LLM inference on them.
        """
        title = metadata.get("title", doc_id)
        category = metadata.get("category", "Document")
        date = metadata.get("date", "Unknown")

        self.graph.add_node(
            doc_id, label=title, type=category, date=date,
            summary=metadata.get("summary", "")
        )

        extracted_skills = metadata.get("extracted_skills", [])
        connected_docs_count = {}
        for skill in extracted_skills:
            skill_id = f"skill:{skill.lower().strip()}"
            if not self.graph.has_node(skill_id):
                self.graph.add_node(skill_id, label=skill, type="Skill")
            else:
                for other_doc in self.graph.predecessors(skill_id):
                    if other_doc != doc_id:
                        connected_docs_count[other_doc] = connected_docs_count.get(other_doc, 0) + 1
            self.graph.add_edge(doc_id, skill_id, relationship="USES_SKILL")

        for other_doc_id, shared_count in connected_docs_count.items():
            self.graph.add_edge(doc_id, other_doc_id, relationship="RELATES_TO", weight=shared_count)
            self.graph.add_edge(other_doc_id, doc_id, relationship="RELATES_TO", weight=shared_count)

        self.save_graph()
        return sorted(connected_docs_count, key=connected_docs_count.get, reverse=True)

    def get_document(self, doc_id: str):
        if not self.graph.has_node(doc_id):
            return None
        return {"id": doc_id, **self.graph.nodes[doc_id]}

    def add_causal_edge(self, source_id: str, target_id: str, relation: str):
        self.graph.add_edge(source_id, target_id, relationship=relation)
        self.save_graph()

    def get_skill_connections(self, skill_name: str) -> dict:
        """
        Retrieves all documents (Certs, Projects, Internships) linked to a specific skill.
        """
        skill_id = f"skill:{skill_name.lower().strip()}"
        if not self.graph.has_node(skill_id):
            return {"skill": skill_name, "connected_documents": []}

        connected_doc_ids = list(self.graph.predecessors(skill_id))
        docs = []
        for d_id in connected_doc_ids:
            node_data = self.graph.nodes[d_id]
            docs.append({
                "id": d_id,
                "title": node_data.get("label"),
                "type": node_data.get("type"),
                "date": node_data.get("date")
            })

        return {"skill": skill_name, "connected_documents": docs}

    def get_documents_summary(self) -> list:
        docs = [
            {"id": n, "title": a.get("label"), "type": a.get("type"),
             "date": a.get("date"), "summary": a.get("summary", "")}
            for n, a in self.graph.nodes(data=True) if not n.startswith("skill:")
        ]
        docs.sort(key=lambda d: d["date"] if d["date"] and d["date"] != "Unknown" else "9999")
        return docs

    def get_all_graph_data(self) -> dict:
        """
        Exports full graph structure (nodes + links) for frontend visualization.
        """
        nodes = [{"id": node, **attrs} for node, attrs in self.graph.nodes(data=True)]
        links = [{"source": s, "target": t, **attrs} for s, t, attrs in self.graph.edges(data=True)]
        return {"nodes": nodes, "links": links}

    def save_graph(self):
        """Persists graph structure to this user's graph JSON file."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        data = nx.node_link_data(self.graph)
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_graph(self):
        """Loads graph structure from this user's graph JSON file if available."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data)
            except Exception as e:
                print(f"Graph loading warning: {e}")
                self.graph = nx.DiGraph()