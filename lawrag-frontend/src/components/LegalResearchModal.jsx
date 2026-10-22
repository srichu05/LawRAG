import React, { useState, useEffect } from 'react';
import { executeLegalResearch, checkBackendHealth } from '../services/api';

const SAMPLE_QUERIES = [
  {
    label: 'Industrial Tribunal Duties (Supreme Court)',
    query: 'What are the functions and duties of the Industrial Tribunal under the Industrial Disputes Act, 1947?',
    category: 'Employment and Labour Law'
  },
  {
    label: 'Termination & Retrenchment (Labour Law)',
    query: 'What constitutes valid grounds for termination and retrenchment under the Industrial Disputes Act, 1947?',
    category: 'Employment and Labour Law'
  },
  {
    label: 'Patent Illegality (Arbitration §34)',
    query: 'Can an arbitral award be set aside on the ground of patent illegality under Section 34 of the Arbitration Act?',
    category: 'Contract and Commercial Law'
  },
  {
    label: 'Homebuyer Delayed Possession (Consumer)',
    query: 'What legal remedies and interest rates are available to flat buyers for delayed possession under the Consumer Protection Act?',
    category: 'Consumer Protection'
  },
  {
    label: 'Quashing FIR in Civil Disputes (§482)',
    query: 'Under what principles can the High Court quash an FIR under Section 482 CrPC when the dispute is predominantly of a civil nature?',
    category: 'Criminal Law & Procedure'
  },
  {
    label: 'Continuous Readiness & Willingness (§16c)',
    query: 'Is continuous readiness and willingness under Section 16(c) of Specific Relief Act mandatory throughout the trial?',
    category: 'Property Law'
  },
  {
    label: '⚠️ Test Insufficient Evidence Guard',
    query: 'What are the statutory liability penalties under Martian Maritime Space Code §999 for cryptocurrency contracts?',
    category: 'Corpus Boundary Limitation',
    isInsufficient: true
  }
];

export default function LegalResearchModal({ isOpen, onClose, initialQuery = '', initialCategory = 'All' }) {
  const [query, setQuery] = useState(initialQuery);
  const [category, setCategory] = useState(initialCategory);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0); // 1: Planner, 2: Retriever, 3: Verifier, 4: Synthesizer
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [expandedCitationId, setExpandedCitationId] = useState(null);
  const [backendHealth, setBackendHealth] = useState({ online: false, source: 'Checking...' });
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      if (initialCategory) {
        setCategory(initialCategory);
      }
      if (initialQuery) {
        setQuery(initialQuery);
        handleRunResearch(initialQuery, initialCategory || 'All');
      }
      checkBackendHealth().then(status => setBackendHealth(status));
    } else {
      setCopied(false);
    }
  }, [isOpen, initialQuery, initialCategory]);

  if (!isOpen) return null;

  const handleRunResearch = async (searchQuery = query, searchCategory = category) => {
    if (!searchQuery.trim()) {
      setError('Please provide a legal research question.');
      return;
    }

    setError(null);
    setLoading(true);
    setResult(null);
    setCurrentStep(1);

    // Simulate realistic agentic pipeline phases with animated feedback
    try {
      const stepTimer1 = setTimeout(() => setCurrentStep(2), 500);
      const stepTimer2 = setTimeout(() => setCurrentStep(3), 1100);
      const stepTimer3 = setTimeout(() => setCurrentStep(4), 1700);

      const researchResult = await executeLegalResearch(searchQuery, searchCategory);

      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);

      setCurrentStep(4);
      setTimeout(() => {
        setResult(researchResult);
        setLoading(false);
      }, 400);
    } catch (err) {
      setError(err.message || 'An error occurred during legal research retrieval.');
      setLoading(false);
    }
  };

  const handleSelectSample = (sample) => {
    setQuery(sample.query);
    setCategory(sample.category);
    handleRunResearch(sample.query, sample.category);
  };

  const handleReset = () => {
    setResult(null);
    setQuery('');
    setError(null);
    setCurrentStep(0);
  };

  const handleCopySummary = () => {
    if (!result) return;
    const textToCopy = `LAWPILOT AI — LEGAL RESEARCH MEMORANDUM\n\nQuery: ${result.query}\nCategory: ${result.category}\n\nSUMMARY & RATIO DECIDENDI:\n${result.summary}\n\nGROUNDING CITATIONS:\n${(result.citations || []).map(c => `- ${c.caseName} [${c.citation}], ${c.court} (${c.paragraph})`).join('\n')}`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="research-modal-backdrop" onClick={onClose}>
      <div className="research-modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Backend Indicator Bar */}
        <div className="backend-indicator-bar">
          <div>
            <span className={`backend-indicator-dot ${backendHealth.online ? '' : 'offline'}`}></span>
            Backend: <strong>{backendHealth.source}</strong> ({backendHealth.apiUrl || 'Local ChromaDB Engine'})
          </div>
          <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: '11px' }}>
            Agentic RAG v2.4 · 185K+ Chunks Grounded
          </div>
        </div>

        {/* Modal Header */}
        <div className="research-modal-header">
          <div className="modal-header-info">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#e3b969" strokeWidth="2">
              <path d="M12 2v20M2 12h20M12 2l8 10-8 10-8-10z"></path>
            </svg>
            <h3 className="modal-header-title">LawPilot AI Legal Research Console</h3>
            <span className="modal-header-badge">Evidence-Grounded RAG</span>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close research console"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        {/* Modal Body */}
        <div className="research-modal-body">
          {/* Query Input Section */}
          <div className="research-input-group">
            <label className="research-label" htmlFor="legal-query-input">
              Enter Indian Legal Question or Judicial Subject:
            </label>
            <textarea
              id="legal-query-input"
              className="research-textarea"
              placeholder="e.g., What are the essential requirements for retrenchment compensation under Section 25F of the Industrial Disputes Act?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
              rows={3}
            />

            {/* Suggested Sample Queries */}
            <div className="sample-queries-wrapper">
              <div className="sample-queries-label">Sample Grounded Queries (Click to Test):</div>
              <div className="sample-queries-pills">
                {SAMPLE_QUERIES.map((sample, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className={`query-pill ${sample.isInsufficient ? 'pill-insufficient' : ''}`}
                    onClick={() => handleSelectSample(sample)}
                    disabled={loading}
                  >
                    {sample.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Actions: Category Selector + Submit Button */}
            <div className="research-actions">
              <div className="category-select-wrap">
                <label htmlFor="category-select">Domain Filter:</label>
                <select
                  id="category-select"
                  className="category-select"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  disabled={loading}
                >
                  <option value="All">All Indexed Domains</option>
                  <option value="Employment and Labour Law">Employment & Labour Law</option>
                  <option value="Contract and Commercial Law">Contract & Commercial Law</option>
                  <option value="Consumer Protection">Consumer Protection</option>
                  <option value="Property Law">Property Law</option>
                  <option value="Constitutional Law">Constitutional Law</option>
                  <option value="Criminal Law & Procedure">Criminal Law & Procedure</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                {result && (
                  <button
                    type="button"
                    className="ast-button-outlined"
                    style={{ padding: '10px 18px', fontSize: '12px' }}
                    onClick={handleReset}
                  >
                    Ask Another Question
                  </button>
                )}
                <button
                  type="button"
                  className="research-submit-btn"
                  onClick={() => handleRunResearch()}
                  disabled={loading || !query.trim()}
                >
                  {loading ? 'Synthesizing Answers...' : 'Execute Legal Research'}
                </button>
              </div>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div style={{ padding: '14px', background: '#fee2e2', color: '#b91c1c', marginBottom: '20px', borderLeft: '4px solid #ef4444' }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {/* Active Agent Pipeline Progress Stepper */}
          {loading && (
            <div className="agent-progress-stepper">
              <div className="stepper-header">
                <span>Autonomous Agentic RAG Coordination</span>
                <span style={{ color: 'var(--ast-global-color-0)' }}>Analyzing Corpus...</span>
              </div>
              <div className="stepper-grid">
                <div className={`step-card ${currentStep >= 1 ? (currentStep > 1 ? 'done' : 'active') : ''}`}>
                  <div className="step-title">1. Query Planner</div>
                  <div className="step-status">
                    {currentStep > 1 ? '✓ Issue Parsed' : (currentStep === 1 ? 'Decomposing legal issue...' : 'Queued')}
                  </div>
                </div>
                <div className={`step-card ${currentStep >= 2 ? (currentStep > 2 ? 'done' : 'active') : ''}`}>
                  <div className="step-title">2. Retrieval Agent</div>
                  <div className="step-status">
                    {currentStep > 2 ? '✓ Passages Retrieved' : (currentStep === 2 ? 'Scanning 185K+ chunks...' : 'Queued')}
                  </div>
                </div>
                <div className={`step-card ${currentStep >= 3 ? (currentStep > 3 ? 'done' : 'active') : ''}`}>
                  <div className="step-title">3. Verifier Agent</div>
                  <div className="step-status">
                    {currentStep > 3 ? '✓ Citations Verified' : (currentStep === 3 ? 'Checking authenticity...' : 'Queued')}
                  </div>
                </div>
                <div className={`step-card ${currentStep >= 4 ? 'active' : ''}`}>
                  <div className="step-title">4. Synthesis Agent</div>
                  <div className="step-status">
                    {currentStep >= 4 ? 'Formulating memorandum...' : 'Queued'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Research Results Output */}
          {result && !loading && (
            <div className="research-output-area">
              <div className="output-header-bar">
                <h4 className="output-title">Evidence-Backed Research Summary</h4>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span className="output-source-tag">Source: {result.backendSource}</span>
                  <button
                    type="button"
                    onClick={handleCopySummary}
                    style={{
                      background: 'none',
                      border: '1px solid #ccc',
                      padding: '4px 10px',
                      fontSize: '12px',
                      cursor: 'pointer'
                    }}
                  >
                    {copied ? '✓ Copied' : 'Copy Memorandum'}
                  </button>
                </div>
              </div>

              {/* Explicit Insufficient Evidence Response Handling */}
              {result.isInsufficientEvidence ? (
                <div className="insufficient-evidence-alert">
                  <div className="alert-title">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
                      <line x1="12" y1="9" x2="12" y2="13"></line>
                      <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                    Insufficient Corroborating Evidence Detected
                  </div>
                  <p className="alert-text">{result.summary}</p>
                  <div style={{ fontWeight: 600, fontSize: '13.5px', marginBottom: '6px', color: '#78350f' }}>
                    Agentic Verification Findings:
                  </div>
                  <ul className="alert-list">
                    {result.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                  <div style={{ fontWeight: 600, fontSize: '13.5px', marginTop: '14px', marginBottom: '6px', color: '#78350f' }}>
                    Recommended Refinements:
                  </div>
                  <ul className="alert-list">
                    {result.recommendations.map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                /* Valid Evidence Response */
                <>
                  {/* Synthesis Summary */}
                  <div className="summary-callout">
                    <p>{result.summary}</p>
                  </div>

                  {/* Applicable Statutes */}
                  {result.statutes && result.statutes.length > 0 && (
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.8px', color: '#555', marginBottom: '8px' }}>
                        Applicable Indian Statutory Provisions:
                      </div>
                      <div className="statute-chips">
                        {result.statutes.map((st, i) => (
                          <div key={i} className="statute-chip">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                              <polyline points="14 2 14 8 20 8"></polyline>
                            </svg>
                            <span>{st.act} — <strong>{st.section}</strong></span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Citations & Evidence Passages */}
                  {result.citations && result.citations.length > 0 && (
                    <div className="citations-wrapper">
                      <h5 className="citations-heading">
                        Retrieved Precedent Passages ({result.citations.length} Grounded Sources)
                      </h5>
                      {result.citations.map((cite) => {
                        const isExpanded = expandedCitationId === cite.id;
                        return (
                          <div key={cite.id} className="citation-card">
                            <div
                              className="citation-top"
                              onClick={() => setExpandedCitationId(isExpanded ? null : cite.id)}
                              style={{ cursor: 'pointer' }}
                            >
                              <span className="citation-case-name">{cite.caseName}</span>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <span className="citation-ref-pill">{cite.citation}</span>
                                <span style={{ fontSize: '12px', color: '#666' }}>
                                  {isExpanded ? '▲ Hide Passage' : '▼ Expand Passage'}
                                </span>
                              </div>
                            </div>

                            <div className="citation-meta">
                              <span><strong>Court:</strong> {cite.court}</span>
                              <span><strong>Bench:</strong> {cite.bench}</span>
                              <span><strong>Location:</strong> {cite.paragraph}</span>
                              <span><strong>Relevance:</strong> {cite.relevanceScore}%</span>
                            </div>

                            {/* Expandable Evidence Quote */}
                            {isExpanded && (
                              <div className="citation-body">
                                &ldquo;{cite.snippet}&rdquo;
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Agent Trace Logs */}
                  {result.agentTraces && (
                    <div style={{ marginTop: '25px', padding: '16px', background: '#f8fafc', border: '1px solid #e2e8f0', fontSize: '12.5px' }}>
                      <div style={{ fontWeight: 700, color: '#334155', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        Agent Trace Audit Trail:
                      </div>
                      <div style={{ display: 'grid', gap: '6px', color: '#475569', fontFamily: 'var(--font-mono)' }}>
                        <div><strong>Planner:</strong> {result.agentTraces.planner}</div>
                        <div><strong>Retriever:</strong> {result.agentTraces.retriever}</div>
                        <div><strong>Verifier:</strong> {result.agentTraces.verifier}</div>
                        <div><strong>Synthesizer:</strong> {result.agentTraces.synthesizer}</div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
