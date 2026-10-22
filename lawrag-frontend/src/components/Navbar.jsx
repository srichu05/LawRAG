import React, { useState, useEffect } from 'react';

export default function Navbar({ onOpenResearch }) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('home');

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 40) {
        setScrolled(true);
      } else {
        setScrolled(false);
      }

      // Track active section
      const sections = ['home', 'about', 'categories', 'how-it-works', 'trust', 'agents', 'contact'];
      for (const sectionId of sections) {
        const el = document.getElementById(sectionId);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= 120 && rect.bottom >= 120) {
            setActiveSection(sectionId);
            break;
          }
        }
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollTo = (id) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header className={`site-header ${scrolled ? 'scrolled' : ''}`}>
      <div className="ast-container">
        <div className="header-inner">
          {/* Brand Logo */}
          <a href="#home" className="site-logo" onClick={(e) => { e.preventDefault(); scrollTo('home'); }}>
            <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="64" height="64" rx="4" fill="#00123a" />
              <path d="M32 12 L32 50" stroke="#e3b969" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M18 20 L46 20" stroke="#e3b969" strokeWidth="2.5" strokeLinecap="round" />
              <circle cx="32" cy="14" r="3" fill="#e3b969" />
              <path d="M18 20 L13 32 M18 20 L23 32" stroke="#e3b969" strokeWidth="1.5" />
              <path d="M11 32 C11 37, 25 37, 25 32 Z" fill="#e3b969" />
              <path d="M46 20 L41 32 M46 20 L51 32" stroke="#e3b969" strokeWidth="1.5" />
              <path d="M39 32 C39 37, 53 37, 53 32 Z" fill="#e3b969" />
              <path d="M22 50 L42 50" stroke="#e3b969" strokeWidth="3" strokeLinecap="round" />
            </svg>
            <div className="site-logo-text">
              LAWPILOT<span>AI</span>
            </div>
          </a>

          {/* Desktop Navigation */}
          <nav className="site-nav">
            <a
              href="#home"
              className={`nav-link ${activeSection === 'home' ? 'active' : ''}`}
              onClick={(e) => { e.preventDefault(); scrollTo('home'); }}
            >
              Home
            </a>
            <a
              href="#about"
              className={`nav-link ${activeSection === 'about' ? 'active' : ''}`}
              onClick={(e) => { e.preventDefault(); scrollTo('about'); }}
            >
              About
            </a>
            <a
              href="#categories"
              className={`nav-link ${activeSection === 'categories' ? 'active' : ''}`}
              onClick={(e) => { e.preventDefault(); scrollTo('categories'); }}
            >
              Legal Research
            </a>
            <a
              href="#how-it-works"
              className={`nav-link ${activeSection === 'how-it-works' ? 'active' : ''}`}
              onClick={(e) => { e.preventDefault(); scrollTo('how-it-works'); }}
            >
              How It Works
            </a>
            <a
              href="#agents"
              className={`nav-link ${activeSection === 'agents' ? 'active' : ''}`}
              onClick={(e) => { e.preventDefault(); scrollTo('agents'); }}
            >
              AI Agents
            </a>
            <a
              href="#contact"
              className={`nav-link ${activeSection === 'contact' ? 'active' : ''}`}
              onClick={(e) => { e.preventDefault(); scrollTo('contact'); }}
            >
              Contact
            </a>
          </nav>

          {/* Primary CTA (Astra Header Button) */}
          <button
            type="button"
            className="ast-header-btn"
            onClick={onOpenResearch}
          >
            Start Legal Research
          </button>

          {/* Mobile Menu Hamburger */}
          <button
            type="button"
            className="mobile-nav-toggle"
            aria-label="Toggle Navigation Menu"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {mobileMenuOpen ? (
                <path d="M6 18L18 6M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
              ) : (
                <path d="M3 12h18M3 6h18M3 18h18" strokeLinecap="round" strokeLinejoin="round" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      <div className={`mobile-nav-drawer ${mobileMenuOpen ? 'open' : ''}`}>
        <a href="#home" className="nav-link" onClick={(e) => { e.preventDefault(); scrollTo('home'); }}>Home</a>
        <a href="#about" className="nav-link" onClick={(e) => { e.preventDefault(); scrollTo('about'); }}>About</a>
        <a href="#categories" className="nav-link" onClick={(e) => { e.preventDefault(); scrollTo('categories'); }}>Legal Research</a>
        <a href="#how-it-works" className="nav-link" onClick={(e) => { e.preventDefault(); scrollTo('how-it-works'); }}>How It Works</a>
        <a href="#agents" className="nav-link" onClick={(e) => { e.preventDefault(); scrollTo('agents'); }}>AI Agents</a>
        <a href="#contact" className="nav-link" onClick={(e) => { e.preventDefault(); scrollTo('contact'); }}>Contact</a>
        <button
          type="button"
          className="ast-button-outlined"
          style={{ width: '100%', marginTop: '10px' }}
          onClick={() => { setMobileMenuOpen(false); onOpenResearch(); }}
        >
          Start Legal Research
        </button>
      </div>
    </header>
  );
}
