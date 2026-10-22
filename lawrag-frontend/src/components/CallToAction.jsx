import React from 'react';

export default function CallToAction({ onOpenResearch }) {
  return (
    <section id="cta" className="cta-section">
      <div className="ast-container">
        <h2 className="cta-title">Research the Law with Greater Clarity.</h2>
        <div className="gold-divider center"></div>
        <p className="cta-desc">
          Explore legal documents, investigate relevant judgments, and review evidence-backed research summaries.
        </p>
        <button
          type="button"
          className="ast-button-outlined"
          style={{ borderColor: 'var(--ast-global-color-0)', color: 'var(--ast-global-color-0)' }}
          onClick={onOpenResearch}
        >
          Start Legal Research
        </button>
      </div>
    </section>
  );
}
