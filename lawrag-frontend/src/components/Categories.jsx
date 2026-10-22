import React from 'react';

const CATEGORIES = [
  {
    num: '.01',
    name: 'Employment & Labour Law',
    desc: 'Industrial disputes, retrenchment compliance under Section 25F, wage codes, continuous service doctrines, and unfair labour practice precedents.',
    sampleQuery: 'What constitutes valid grounds for termination and retrenchment under the Industrial Disputes Act, 1947?',
    categoryTag: 'Employment and Labour Law'
  },
  {
    num: '.02',
    name: 'Contract & Commercial Law',
    desc: 'Breach of contract, specific performance under Specific Relief Act, commercial arbitration challenges under Section 34, and damages estimation.',
    sampleQuery: 'Can an arbitral award be set aside on the ground of patent illegality under Section 34 of the Arbitration Act?',
    categoryTag: 'Contract and Commercial Law'
  },
  {
    num: '.03',
    name: 'Consumer Protection',
    desc: 'Deficiency of service, unfair trade practices, product liability under Consumer Protection Act 2019, and home buyer delayed possession remedies.',
    sampleQuery: 'What legal remedies and interest rates are available to flat buyers for delayed possession under the Consumer Protection Act?',
    categoryTag: 'Consumer Protection'
  },
  {
    num: '.04',
    name: 'Property & Real Estate Law',
    desc: 'Title verification, Transfer of Property Act doctrines, part performance under Section 53A, continuous readiness & willingness, and easement rights.',
    sampleQuery: 'Is continuous readiness and willingness under Section 16(c) of Specific Relief Act mandatory throughout the trial?',
    categoryTag: 'Property Law'
  },
  {
    num: '.05',
    name: 'Constitutional Law',
    desc: 'Fundamental rights writ petitions under Articles 32 and 226, administrative overreach, equality before law (Art. 14), and judicial review standards.',
    sampleQuery: 'What are the established guidelines for the exercise of writ jurisdiction under Article 226 when alternative statutory remedies exist?',
    categoryTag: 'Constitutional Law'
  },
  {
    num: '.06',
    name: 'Criminal Law & Procedure',
    desc: 'Inherent powers of High Court under Section 482 CrPC / Section 528 BNSS, quashing of FIRs in commercial controversies, and bail jurisprudence.',
    sampleQuery: 'Under what principles can the High Court quash an FIR under Section 482 CrPC when the dispute is predominantly of a civil nature?',
    categoryTag: 'Criminal Law & Procedure'
  }
];

export default function Categories({ onSelectCategoryQuery, onOpenResearch }) {
  return (
    <section id="categories" className="categories-section">
      <div className="ast-container">
        <div className="categories-header">
          <h2 className="categories-title">Practice Areas</h2>
          <div className="gold-divider"></div>
          <p className="categories-intro">
            Specialized retrieval pipelines indexed across key Indian legal disciplines. Query authentic precedents, extract relevant statutory sections, and review source-backed answers.
          </p>
        </div>

        {/* Row 1: 4 Cards (.01 to .04) */}
        <div className="categories-grid-top">
          {CATEGORIES.slice(0, 4).map((cat) => (
            <div key={cat.num} className="category-card">
              <div className="category-num">{cat.num}</div>
              <h5 className="category-name">{cat.name}</h5>
              <div className="gold-divider" style={{ width: '35px', margin: '6px 0 12px 0' }}></div>
              <p className="category-desc">{cat.desc}</p>
              <button
                type="button"
                className="category-query-chip"
                onClick={() => onSelectCategoryQuery(cat.sampleQuery, cat.categoryTag)}
                title="Run research query for this category"
              >
                Research {cat.name.split('&')[0]} &rarr;
              </button>
            </div>
          ))}
        </div>

        {/* Row 2: 3 Columns (.05, .06, and Highlighted Card 7) */}
        <div className="categories-grid-bottom">
          {CATEGORIES.slice(4, 6).map((cat) => (
            <div key={cat.num} className="category-card">
              <div className="category-num">{cat.num}</div>
              <h5 className="category-name">{cat.name}</h5>
              <div className="gold-divider" style={{ width: '35px', margin: '6px 0 12px 0' }}></div>
              <p className="category-desc">{cat.desc}</p>
              <button
                type="button"
                className="category-query-chip"
                onClick={() => onSelectCategoryQuery(cat.sampleQuery, cat.categoryTag)}
                title="Run research query for this category"
              >
                Research {cat.name.split('&')[0]} &rarr;
              </button>
            </div>
          ))}

          {/* Special Card 7 (Astra Warm Gold Card) */}
          <div className="category-card category-card-highlight">
            <div>
              <h4 className="highlight-title">Corpus Coverage</h4>
              <ul className="highlight-list">
                <li>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="9 18 15 12 9 6"></polyline>
                  </svg>
                  Supreme Court of India Precedents
                </li>
                <li>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="9 18 15 12 9 6"></polyline>
                  </svg>
                  High Courts of Delhi, Bombay & Karnataka
                </li>
                <li>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="9 18 15 12 9 6"></polyline>
                  </svg>
                  Central Acts & Statutory Amendments
                </li>
              </ul>
            </div>
            <a
              href="#research"
              className="highlight-link"
              onClick={(e) => { e.preventDefault(); onOpenResearch(); }}
            >
              Start Legal Research &rarr;
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
