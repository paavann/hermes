import type { MetaFunction } from 'react-router';

import {
  Nav,
  Footer,
  HeroSection,
  ProblemSection,
  CapabilitiesSection,
  ContactSection,
} from '../components/landing';

export { LaunchMapBtn } from '../components/landing';

export const meta: MetaFunction = () => [
  { title: 'Hermes — Geospatial Intelligence Platform' },
  {
    name: 'description',
    content:
      "Provably grounded real-time geospatial intelligence. Observe the world's critical events unfold across space and causal time.",
  },
  { property: 'og:title', content: 'Hermes — Geospatial Intelligence Platform' },
  {
    property: 'og:description',
    content:
      'Autonomous geospatial news intelligence with vector consensus and causal lineage.',
  },
];

export default function LandingRoute(): React.JSX.Element {
  return (
    <div className="relative min-h-screen overflow-x-clip bg-obsidian font-mono text-ivory antialiased selection:bg-neon-blue selection:text-black">
      <div
        className="pointer-events-none fixed inset-0 z-0 bg-grid-hud opacity-[0.55]"
        aria-hidden="true"
      />

      <div
        className="pointer-events-none fixed inset-0 z-20 mx-auto flex max-w-[1600px] justify-center"
        aria-hidden="true"
      >
        <div className="relative h-full w-full">
          <div className="absolute bottom-0 left-0 top-0 w-px bg-border-subtle/40" />
          <div className="absolute bottom-0 left-[180px] top-0 w-px bg-border-subtle/50 md:left-[220px]" />
          <div className="absolute bottom-0 right-0 top-0 w-px bg-border-subtle/40" />
        </div>
      </div>

      <Nav />

      <main id="main-content" className="relative z-10 pt-[62px]">
        <HeroSection />
        <ProblemSection />
        <CapabilitiesSection />
        <ContactSection />
      </main>

      <Footer />
    </div>
  );
}
