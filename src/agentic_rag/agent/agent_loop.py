"""Bounded agent loop around an injectable RAG pipeline."""
class AgentLoop:
    def __init__(self, pipeline, max_steps: int = 3): self.pipeline, self.max_steps = pipeline, max_steps
    def run(self, question: str, **kwargs): return self.pipeline.answer(question, **kwargs)

def run_agent(pipeline, question: str, **kwargs): return AgentLoop(pipeline).run(question, **kwargs)

