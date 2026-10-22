import React from 'react';

export default function Footer({ onOpenResearch, onOpenDisclaimer }) {
  const scrollTo = (id) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <footer id="contact" className="site-footer">
      <div className="ast-container">
        {/* Above Footer */}
        <div className="footer-top">
          <h2 className="footer-top-title">Do You Need Legal Research Assistance?</h2>
          <div className="gold-divider center"></div>
          <p className="footer-top-text">
            LawPilot AI assists legal professionals, researchers, and citizens in investigating Indian judicial precedents, statutory provisions, and ratio decidendi with verifiable citation grounding.
          </p>
        </div>

        {/* Primary Footer (3 Columns) */}
        <div className="footer-middle">
          <div className="footer-col">
            <h4 className="footer-col-title">Corpus Registry</h4>
            <p>
              Indexed across 24,500+ landmark judgments from the Supreme Court of India, Delhi High Court, Bombay High Court, and Central Acts.
            </p>
            <p style={{ marginTop: '12px' }}>
              <a href="#categories" onClick={(e) => { e.preventDefault(); scrollTo('categories'); }}>
                Explore Practice Categories &rarr;
              </a>
            </p>
          </div>

          <div className="footer-col">
            <h4 className="footer-col-title">System Status & API</h4>
            <p>
              Autonomous Multi-Agent Orchestrator: <span style={{ color: '#10b981', fontWeight: 600 }}>Active</span>
            </p>
            <p>
              Vector Index Store: <span style={{ color: '#e3b969' }}>ChromaDB Precedent Store</span>
            </p>
            <p style={{ marginTop: '12px' }}>
              <button
                type="button"
                onClick={onOpenResearch}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--ast-global-color-0)',
                  cursor: 'pointer',
                  padding: 0,
                  fontFamily: 'inherit',
                  fontSize: 'inherit',
                  textDecoration: 'underline'
                }}
              >
                Launch Research Console &rarr;
              </button>
            </p>
          </div>

          <div className="footer-col">
            <h4 className="footer-col-title">Legal Operations</h4>
            <p>
              Supreme Court & High Court Judgments Hub<br />
              Tilak Marg, New Delhi 110001, India
            </p>
            <p style={{ marginTop: '10px' }}>
              Contact: <a href="mailto:research@lawpilot.ai">research@lawpilot.ai</a>
            </p>
            <p style={{ marginTop: '4px' }}>
              Phone: +91 11 2338 8942
            </p>
          </div>
        </div>

        {/* Below Footer */}
        <div className="footer-bottom">
          <div>
            Copyright &copy; 2026 LawPilot AI. All rights reserved.
          </div>
          <div className="footer-links">
            <a href="#home" onClick={(e) => { e.preventDefault(); scrollTo('home'); }}>Home</a>
            <a href="#about" onClick={(e) => { e.preventDefault(); scrollTo('about'); }}>About</a>
            <a href="#categories" onClick={(e) => { e.preventDefault(); scrollTo('categories'); }}>Legal Research</a>
            <a href="#how-it-works" onClick={(e) => { e.preventDefault(); scrollTo('how-it-works'); }}>How It Works</a>
            <a href="#disclaimer" onClick={(e) => { e.preventDefault(); onOpenDisclaimer(); }}>Legal Disclaimer</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
