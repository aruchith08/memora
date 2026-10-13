import Nav from '../components/layout/Nav';
import Footer from '../components/layout/Footer';
import Hero from '../components/sections/Hero';
import HowItWorks from '../components/sections/HowItWorks';
import MultiAgentSection from '../components/sections/MultiAgentSection';
import PrivacyTrust from '../components/sections/PrivacyTrust';
import FinalCTA from '../components/sections/FinalCTA';

export default function HomePage() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <HowItWorks />
        <MultiAgentSection />
        <PrivacyTrust />
        <FinalCTA />
      </main>
      <Footer />
    </>
  );
}
