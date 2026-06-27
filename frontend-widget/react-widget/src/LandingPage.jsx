import React from 'react';
import './LandingPage.css';

function LandingPage() {
  return (
    <div className="landing-page">
      <header className="landing-header">
        <div className="logo">Portfolio Builders</div>
        <nav className="landing-nav">
          <a href="#courses">Courses</a>
          <a href="#internships">Internships</a>
          <a href="#about">About</a>
        </nav>
      </header>

      <main className="landing-main">
        <section className="hero-section">
          <h1>Build a World-Class Portfolio</h1>
          <p>Accelerate your career with industry-led UI/UX, Full Stack, and AICTE Internships.</p>
          <button className="hero-cta">Explore Programs</button>
        </section>

        <section className="features-section" id="courses">
          <div className="feature-card">
            <h3>UI/UX Portfolio Program</h3>
            <p>Master Figma and product design with real-world SaaS projects. Reviewed by top recruiters.</p>
          </div>
          <div className="feature-card">
            <h3>Full Stack Development</h3>
            <p>React, Node, Python. Build end-to-end applications from scratch and host them live.</p>
          </div>
          <div className="feature-card">
            <h3>AICTE Internships</h3>
            <p>Official corporate internships verified by AICTE & FYUGP with dedicated mentorship.</p>
          </div>
        </section>
      </main>
    </div>
  );
}

export default LandingPage;
