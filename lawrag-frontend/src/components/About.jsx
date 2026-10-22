import React from 'react';

export default function About({ onOpenResearch }) {
  return (
    <section id="about" className="about-section">
      <div className="ast-container">
        <div className="about-grid">
          <div className="about-text-col">
            <h2 className="about-title">Legal Research, Made Clearer.</h2>
            <div className="gold-divider"></div>
            <p className="about-description">
              LawPilot AI helps users navigate complex legal information by combining document retrieval, specialized AI agents, and evidence-based answer generation. Its goal is to make legal research easier to explore while keeping supporting sources visible.
            </p>
            <p className="about-description" style={{ color: '#666', fontSize: '14.5px' }}>
              Unlike generic generative models prone to inventing case citations or misinterpreting statutory sections, LawPilot AI treats legal authenticity as non-negotiable. Every legal claim is synthesized strictly from retrieved paragraphs, complete with court bench details, law report citations (AIR/SCC), and paragraph references.
            </p>

            <div className="about-author-block">
              <h6 className="about-author-name">Agentic RAG Engine</h6>
              <span className="about-author-role">Supreme Court & High Courts of India</span>
              <img
                src="/assets/legal-seal.png"
                alt="LawPilot Authentic Legal Seal"
                className="about-seal-img"
              />
            </div>

            <div style={{ marginTop: '35px' }}>
              <button
                type="button"
                className="ast-button-outlined"
                style={{ color: '#111', borderColor: 'var(--ast-global-color-0)' }}
                onClick={onOpenResearch}
              >
                Start Legal Research
              </button>
            </div>
          </div>

          <div className="about-img-col">
            <img
              src="/assets/about-img.jpg"
              alt="Legal Research Consultation in Law Firm"
              className="about-main-image"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
