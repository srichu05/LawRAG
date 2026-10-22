import React from 'react';

export default function TrustSection({ onOpenResearch }) {
  return (
    <section id="trust" className="trust-section">
      <div className="ast-container">
        <div className="trust-grid">
          {/* Left Column: Testimonial & Evidence Standard */}
          <div className="trust-left">
            <h2 className="trust-title">Built on Research Integrity & Verifiable Truth</h2>
            <div className="gold-divider"></div>

            <div className="trust-quote-wrapper">
              <span className="trust-quote-icon">&ldquo;</span>
              <p className="trust-quote-text">
                In legal practice, hallucination is unacceptable. LawPilot AI enforces strict source grounding: every synthesized proposition maps directly to verifiable paragraphs in authentic Indian court judgments, complete with court bench records and citation metadata.
              </p>

              <div className="trust-author-row">
                <img
                  src="/assets/testimonial-avatar.jpg"
                  alt="Evidence Verification Architecture"
                  className="trust-author-img"
                />
                <div>
                  <div className="trust-author-name">Evidence Verification Protocol</div>
                  <div className="trust-author-sub">Grounded against Indian Judgments & Central Acts</div>
                </div>
              </div>

              <div className="trust-stars">
                {[...Array(5)].map((_, i) => (
                  <svg key={i} width="18" height="18" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" />
                  </svg>
                ))}
              </div>

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

          {/* Right Column: Institutional Data Sources Grid */}
          <div className="trust-right">
            <div className="trust-badges-grid">
              <div className="badge-card">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 3v18M3 9l9-6 9 6M3 9h18M5 9v9M19 9v9M2 21h20"></path>
                </svg>
                <div className="badge-label">Supreme Court of India</div>
                <div className="badge-sub">Full Text Precedents & Rulings</div>
              </div>

              <div className="badge-card">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                </svg>
                <div className="badge-label">Central Acts Registry</div>
                <div className="badge-sub">Amended Statutes & Codes</div>
              </div>

              <div className="badge-card">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="10"></circle>
                  <path d="m4.93 4.93 4.24 4.24M14.83 14.83l4.24 4.24M14.83 9.17l4.24-4.24M4.93 19.07l4.24-4.24"></path>
                </svg>
                <div className="badge-label">High Court Precedents</div>
                <div className="badge-sub">Delhi, Bombay, Karnataka & Madras</div>
              </div>

              <div className="badge-card">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                  <path d="m9 12 2 2 4-4"></path>
                </svg>
                <div className="badge-label">Zero-Hallucination Guard</div>
                <div className="badge-sub">Strict Cross-Corroboration</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
