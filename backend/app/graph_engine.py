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

    def add_document_node(self, doc_id: str, metadata: dict):
        """
        Adds a document node and links it to its extracted skills, 
        creating dynamic relationships across user data.
        """
        title = metadata.get("title", doc_id)
        category = metadata.get("category", "Document")
        date = metadata.get("date", "Unknown")

        # 1. Add primary document node
        self.graph.add_node(
            doc_id, 
            label=title, 
            type=category, 
            date=date, 
            summary=metadata.get("summary", "")
        )

        # 2. Add skill nodes & create relationship edges
        extracted_skills = metadata.get("extracted_skills", [])
        for skill in extracted_skills:
            skill_id = f"skill:{skill.lower().strip()}"
            
            # Ensure skill node exists
            if not self.graph.has_node(skill_id):
                self.graph.add_node(skill_id, label=skill, type="Skill")

            # Create directed edge from Document -> Skill
            self.graph.add_edge(doc_id, skill_id, relationship="USES_SKILL")

        self.save_graph()

    def get_skill_connections(self, skill_name: str) -> dict:
        """
        Retrieves all documents (Certs, Projects, Internships) linked to a specific skill.
        """
        skill_id = f"skill:{skill_name.lower().strip()}"
        if not self.graph.has_node(skill_id):
            return {"skill": skill_name, "connected_documents": []}

        # Find all documents connected to this skill
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

        return {
            "skill": skill_name,
            "connected_documents": docs
        }

    def get_all_graph_data(self) -> dict:
        """
        Exports full graph structure (nodes + links) for frontend visualization.
        """
        nodes = []
        for node, attrs in self.graph.nodes(data=True):
            nodes.append({"id": node, **attrs})

        links = []
        for source, target, attrs in self.graph.edges(data=True):
            links.append({"source": source, "target": target, **attrs})

        return {"nodes": nodes, "links": links}

    def save_graph(self):
        """Persists graph structure to data/memory_graph.json"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        data = nx.node_link_data(self.graph)
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_graph(self):
        """Loads graph structure from data/memory_graph.json if available"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data)
            except Exception as e:
                print(f"Graph loading warning: {e}")
                self.graph = nx.DiGraph()