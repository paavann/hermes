import type { MetaFunction } from 'react-router'
import {
  Nav, Footer,
  HeroSection, ProblemSection, CapabilitiesSection, ContactSection,
} from '../components/landing'
export { LaunchMapBtn } from '../components/landing'


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
    content: 'Autonomous geospatial news intelligence with vector consensus and causal lineage.',
  },
];





export default function LandingRoute(): React.JSX.Element {
  return (
    <div className="relative min-h-screen bg-obsidian text-ivory font-mono selection:bg-neon-blue selection:text-black antialiased overflow-x-clip">
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.035] z-0"
        aria-hidden="true"
      />

      <div
        className="fixed inset-0 pointer-events-none z-20 flex justify-center max-w-360 mx-auto"
        aria-hidden="true"
      >
        <div className="w-full h-full relative">
          <div className="absolute top-0 bottom-0 left-0 w-px bg-border-subtle/40" />
          <div className="absolute top-0 bottom-0 left-45 md:left-55 w-px bg-border-subtle/50" />
          <div className="absolute top-0 bottom-0 right-0 w-px bg-border-subtle/40" />
        </div>
      </div>

      <Nav />


      <main id="main-content" className="pt-15.5">
        <HeroSection />
        <ProblemSection />
        <CapabilitiesSection />
        <ContactSection />
      </main>

      <Footer />
    </div>
  );
}