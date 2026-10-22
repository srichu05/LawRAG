import React from 'react';

export default function Hero({ onOpenResearch, onExploreHowItWorks }) {
  return (
    <section id="home" className="hero-section">
      <div className="hero-overlay"></div>
      <div className="ast-container">
        <div className="hero-content">
          <div className="hero-text">
            <h5 className="hero-subtitle">Welcome to LawPilot AI</h5>
            <h1 className="hero-title">Legal Research. Backed by Evidence.</h1>
            <div className="gold-divider"></div>
            <p className="hero-description">
              Explore Indian court judgments and legal documents with an AI research assistant that retrieves relevant evidence, verifies supporting passages, and presents source-backed answers.
            </p>
            <div className="hero-button-group">
              <button
                type="button"
                className="ast-button-outlined hero-btn-primary"
                onClick={onOpenResearch}
              >
                Start Legal Research
              </button>
              <button
                type="button"
                className="ast-button-outlined hero-btn-secondary"
                onClick={onExploreHowItWorks}
              >
                Explore How It Works
              </button>
            </div>
          </div>

          <div className="hero-badge-panel">
            <div className="hero-glass-card">
              <div className="hero-glass-title">Agentic RAG Engine</div>
              <p className="hero-glass-text">
                Autonomous legal intelligence ground-truthed against Supreme Court of India precedents and Central Acts.
              </p>
              <div className="hero-glass-specs">
                <div className="spec-item">
                  <span className="num">24.5K+</span>
                  <span className="label">Indexed Judgments</span>
                </div>
                <div className="spec-item">
                  <span className="num">100%</span>
                  <span className="label">Source Verified</span>
                </div>
                <div className="spec-item">
                  <span className="num">4-Stage</span>
                  <span className="label">Agent Pipeline</span>
                </div>
                <div className="spec-item">
                  <span className="num">0.0%</span>
                  <span className="label">Speculative Claims</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
