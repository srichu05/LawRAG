import React from 'react';

const STATS = [
  {
    title: 'Indexed Judgments',
    value: '24,500',
    suffix: '+'
  },
  {
    title: 'Searchable Chunks',
    value: '185',
    suffix: 'K+'
  },
  {
    title: 'Autonomous Agents',
    value: '4',
    suffix: ''
  },
  {
    title: 'Legal Disciplines',
    value: '6',
    suffix: ''
  },
  {
    title: 'Source Traceability',
    value: '100',
    suffix: '%'
  }
];

export default function StatsStrip() {
  return (
    <div className="stats-wrapper">
      <div className="ast-container">
        <div className="stats-card">
          {STATS.map((stat, idx) => (
            <div key={idx} className="stat-item">
              <div className="stat-title">{stat.title}</div>
              <div className="stat-number">
                {stat.value}
                {stat.suffix && <span className="stat-suffix">{stat.suffix}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
