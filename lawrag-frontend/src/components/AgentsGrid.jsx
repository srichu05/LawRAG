import React from 'react';

const AGENTS = [
  {
    name: 'Legal Query Planner',
    role: 'Stage 1 · Query Decomposition',
    image: '/assets/agent-planner.jpg',
    description: 'Identifies the user\'s research question, statutory context, and core legal issues. Decomposes multi-faceted questions into targeted retrieval sub-queries.'
  },
  {
    name: 'Legal Retrieval Agent',
    role: 'Stage 2 · Dense-Sparse Search',
    image: '/assets/agent-retriever.jpg',
    description: 'Executes hybrid keyword and neural semantic search across indexed Supreme Court of India precedents, High Court cases, and Central Statutory provisions.'
  },
  {
    name: 'Evidence Verification Agent',
    role: 'Stage 3 · Hallucination Guard',
    image: '/assets/agent-verifier.jpg',
    description: 'Verifies whether retrieved passages factually support proposed legal conclusions. Identifies insufficient evidence and halts unsupported propositions.'
  },
  {
    name: 'Answer Synthesis Agent',
    role: 'Stage 4 · Citation Presentation',
    image: '/assets/agent-synthesizer.jpg',
    description: 'Drafts a structured legal research summary grounded strictly in verified passages, embedding direct court citations (AIR/SCC) and paragraph numbers.'
  }
];

export default function AgentsGrid() {
  return (
    <section id="agents" className="agents-section">
      <div className="ast-container">
        <div className="agents-header">
          <h2 className="agents-title">Autonomous Research Agents</h2>
          <div className="gold-divider"></div>
          <p style={{ color: '#666', fontSize: '15.5px', maxWidth: '650px', lineHeight: '1.8' }}>
            LawPilot AI coordinates four specialized AI agents to ensure thorough research, evidentiary fidelity, and source traceability.
          </p>
        </div>

        <div className="agents-grid">
          {AGENTS.map((agent, index) => (
            <div key={index} className="agent-card">
              <h5 className="agent-name">{agent.name}</h5>
              <div className="agent-role">{agent.role}</div>
              <div className="agent-img-wrapper">
                <img
                  src={agent.image}
                  alt={agent.name}
                  className="agent-img"
                />
              </div>
              <p className="agent-desc">{agent.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
