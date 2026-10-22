import React from 'react';

export default function DisclaimerModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="research-modal-backdrop" onClick={onClose}>
      <div className="research-modal-container" style={{ maxWidth: '650px' }} onClick={(e) => e.stopPropagation()}>
        <div className="research-modal-header">
          <div className="modal-header-info">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#e3b969" strokeWidth="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <h3 className="modal-header-title">Responsible AI & Legal Disclaimer</h3>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div className="research-modal-body" style={{ fontSize: '14.5px', lineHeight: '1.8', color: '#333' }}>
          <h4 style={{ fontFamily: 'var(--font-serif)', fontSize: '18px', color: '#111', marginBottom: '10px' }}>
            Informational and Research Assistance Only
          </h4>
          <p>
            LawPilot AI is an Agentic Retrieval-Augmented Generation (RAG) system built to help legal researchers, practitioners, and citizens discover, explore, and comprehend authentic Indian legal documents, judicial decisions, and statutory enactments.
          </p>
          <p style={{ marginTop: '12px' }}>
            <strong>No Attorney-Client Relationship:</strong> Use of this software does not constitute legal advice, a formal legal opinion, or the formation of an advocate-client relationship. The law is dynamic, subject to amendment and judicial review.
          </p>
          <p style={{ marginTop: '12px' }}>
            <strong>Zero-Hallucination Guardrail:</strong> LawPilot AI uses multi-agent verification to ground statements in real court paragraphs. However, users must always cross-reference retrieved passages with official court registries or an authorized legal counsel prior to filing or advising.
          </p>
          <div style={{ marginTop: '25px', textAlign: 'right' }}>
            <button
              type="button"
              className="ast-button-outlined"
              style={{ color: '#111', borderColor: 'var(--ast-global-color-0)' }}
              onClick={onClose}
            >
              Understood
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
