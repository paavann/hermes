import type React from 'react';
import type { MetaFunction } from 'react-router';
import { Footer } from '../components/landing';
import { PrivacyNav, PrivacyPolicyContent } from '../components/privacy';

export const meta: MetaFunction = () => [
  { title: 'Privacy Policy — Hermes Geospatial Intelligence' },
  {
    name: 'description',
    content:
      'Privacy Policy, data collection practices, and privacy commitments for the Hermes open-source geospatial intelligence project.',
  },
  {
    property: 'og:title',
    content: 'Privacy Policy — Hermes Geospatial Intelligence',
  },
  {
    property: 'og:description',
    content:
      'Open-source geospatial intelligence privacy commitments and data practices.',
  },
];

export default function PrivacyRoute(): React.JSX.Element {
  return (
    <div className="relative min-h-screen bg-obsidian text-ivory font-mono selection:bg-neon-blue selection:text-black antialiased overflow-x-clip">
      {/* Background Architectural Grid Lines */}
      <div
        className="fixed inset-0 pointer-events-none z-20 flex justify-center max-w-360 mx-auto"
        aria-hidden="true"
      >
        <div className="w-full h-full relative">
          <div className="absolute top-0 bottom-0 left-0 w-px bg-border-subtle/40" />
          <div className="hidden md:block absolute top-0 bottom-0 left-55 w-px bg-border-subtle/50" />
          <div className="absolute top-0 bottom-0 right-0 w-px bg-border-subtle/40" />
        </div>
      </div>

      <PrivacyNav />

      <main id="main-content" className="pt-15.5 relative z-10">
        <PrivacyPolicyContent />
      </main>

      <Footer />
    </div>
  );
}
