import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import About from './components/About';
import Categories from './components/Categories';
import HowItWorks from './components/HowItWorks';
import StatsStrip from './components/StatsStrip';
import TrustSection from './components/TrustSection';
import AgentsGrid from './components/AgentsGrid';
import CallToAction from './components/CallToAction';
import Footer from './components/Footer';
import LegalResearchModal from './components/LegalResearchModal';
import DisclaimerModal from './components/DisclaimerModal';

export default function App() {
  const [researchModalOpen, setResearchModalOpen] = useState(false);
  const [disclaimerModalOpen, setDisclaimerModalOpen] = useState(false);
  const [activeQuery, setActiveQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');

  const handleOpenResearch = (query = '', category = 'All') => {
    setActiveQuery(query);
    setActiveCategory(category);
    setResearchModalOpen(true);
  };

  const handleSelectCategoryQuery = (query, category) => {
    handleOpenResearch(query, category);
  };

  const handleScrollToHowItWorks = () => {
    const el = document.getElementById('how-it-works');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="hfeed site" id="page">
      {/* 1. Header & Navigation */}
      <Navbar onOpenResearch={() => handleOpenResearch()} />

      {/* Main Content Area */}
      <main id="main" className="site-main">
        {/* 2. Hero Section */}
        <Hero
          onOpenResearch={() => handleOpenResearch()}
          onExploreHowItWorks={handleScrollToHowItWorks}
        />

        {/* 3. About Section */}
        <About onOpenResearch={() => handleOpenResearch()} />

        {/* 4. Legal Research Categories (Practice Areas) */}
        <Categories
          onSelectCategoryQuery={handleSelectCategoryQuery}
          onOpenResearch={() => handleOpenResearch()}
        />

        {/* 5. How It Works / FAQ Accordion (Why Choose Us) */}
        <HowItWorks />

        {/* 6. Statistics Strip (Floating 5-column counter card) */}
        <StatsStrip />

        {/* 7. Trust & Evidentiary Standards (Testimonials) */}
        <TrustSection onOpenResearch={() => handleOpenResearch()} />

        {/* 8. AI Agents (Attorneys Grid) */}
        <AgentsGrid />

        {/* 9. Final Call to Action */}
        <CallToAction onOpenResearch={() => handleOpenResearch()} />
      </main>

      {/* 10. Footer */}
      <Footer
        onOpenResearch={() => handleOpenResearch()}
        onOpenDisclaimer={() => setDisclaimerModalOpen(true)}
      />

      {/* 11. Working Interactive Legal Research Application Modal */}
      <LegalResearchModal
        isOpen={researchModalOpen}
        onClose={() => setResearchModalOpen(false)}
        initialQuery={activeQuery}
        initialCategory={activeCategory}
      />

      {/* 12. Responsible AI Disclaimer Modal */}
      <DisclaimerModal
        isOpen={disclaimerModalOpen}
        onClose={() => setDisclaimerModalOpen(false)}
      />
    </div>
  );
}
