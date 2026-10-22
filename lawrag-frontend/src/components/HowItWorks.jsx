import React, { useState } from 'react';

const FAQ_ITEMS = [
  {
    id: 1,
    question: 'How does LawPilot AI retrieve legal information?',
    answer: 'LawPilot AI utilizes a dual-stage retrieval engine optimized for Indian legal literature. When a question is submitted, the Legal Query Planner deconstructs the legal issues and statutory hooks. Next, the Retrieval Agent performs hybrid dense-sparse vector search across indexed judgments from the Supreme Court of India, High Courts, and Central Acts. This ensures that both exact statutory phrases (e.g., "Section 25F", "patent illegality") and semantic legal concepts are retrieved with high precision.'
  },
  {
    id: 2,
    question: 'How are sources and citations displayed?',
    answer: 'Every factual assertion and synthesized legal summary includes direct, verifiable citations. Citations detail the full case name (e.g., State Bank of India v. N. Sundara Money), the court and bench composition, the official legal reporter citation (AIR or SCC), the decision year, and the exact paragraph number. Users can expand citations to review the authentic excerpt directly.'
  },
  {
    id: 3,
    question: 'What happens when the retrieved evidence is insufficient?',
    answer: 'LawPilot AI is engineered with an active Evidence Verification Agent. If the retrieved document chunks do not contain verified legal authorities that substantiate the query, or if the question pertains to an unindexed statute or fabricated premise, the system explicitly returns an Insufficient Evidence response rather than hallucinating or guessing. This maintains absolute evidentiary integrity.'
  },
  {
    id: 4,
    question: 'Can the system compare relevant court judgments?',
    answer: 'Yes. The Answer Synthesis Agent compares ratio decidendi across landmark precedents, distinguishing earlier Constitution Bench rulings from subsequent divisional bench decisions. It highlights when a statutory amendment (such as the 2015 amendments to Section 34 of the Arbitration Act or the Consumer Protection Act 2019) has superseded or refined earlier judicial interpretations.'
  },
  {
    id: 5,
    question: 'Does the system provide definitive legal advice?',
    answer: 'No. LawPilot AI is an advanced research assistant designed to assist legal practitioners, researchers, students, and citizens in discovering and understanding Indian legal documents. It provides evidence-backed research summaries and document retrieval, not a definitive legal opinion or substitute for a licensed advocate or qualified lawyer.'
  }
];

export default function HowItWorks() {
  const [openId, setOpenId] = useState(1);

  const toggleAccordion = (id) => {
    setOpenId(openId === id ? null : id);
  };

  return (
    <section id="how-it-works" className="faq-section">
      <div className="faq-overlay"></div>
      <div className="ast-container">
        <div className="faq-grid">
          {/* Left Column */}
          <div className="faq-left">
            <div className="gold-divider"></div>
            <h2 className="faq-title">Why Choose Us</h2>
            <p className="faq-subtitle">
              How LawPilot AI ensures rigor, source traceability, and zero-hallucination legal research through specialized agentic coordination.
            </p>
            <div style={{ marginTop: '25px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--ast-global-color-0)', fontSize: '14px', fontWeight: 600 }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                </svg>
                Hallucination Guardrail Active
              </div>
              <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', marginTop: '6px' }}>
                Every paragraph is cross-checked against ChromaDB indexed collections.
              </p>
            </div>
          </div>

          {/* Right Column: Accordion */}
          <div className="faq-right">
            <div className="accordion-list">
              {FAQ_ITEMS.map((item) => {
                const isOpen = openId === item.id;
                return (
                  <div key={item.id} className={`accordion-item ${isOpen ? 'active' : ''}`}>
                    <div
                      className="accordion-header"
                      onClick={() => toggleAccordion(item.id)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleAccordion(item.id); }}
                    >
                      <span className="accordion-title">{item.question}</span>
                      <svg
                        className="accordion-icon"
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                      >
                        <polyline points="9 18 15 12 9 6"></polyline>
                      </svg>
                    </div>
                    {isOpen && (
                      <div className="accordion-body">
                        {item.answer}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
