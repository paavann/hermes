import type React from 'react';
import { Link } from 'react-router';
import type { PrivacySection } from './types';

export const PRIVACY_SECTIONS: readonly PrivacySection[] = [
  {
    id: 'overview',
    number: '1',
    title: 'Overview',
    summary: 'What Hermes is and why this privacy policy exists.',
  },
  {
    id: 'information-collected',
    number: '2',
    title: 'Information We Collect',
    summary: 'The minimal data needed to create accounts and run the map.',
  },
  {
    id: 'authentication',
    number: '3',
    title: 'User Accounts & Authentication',
    summary: 'How login credentials and sessions are handled securely by Clerk.',
  },
  {
    id: 'map-data',
    number: '4',
    title: 'Map Data & Location Information',
    summary: 'How map coordinate queries work without tracking your location history.',
  },
  {
    id: 'third-parties',
    number: '5',
    title: 'Third-Party Services',
    summary: 'External providers used for hosting, maps, and geocoding.',
  },
  {
    id: 'commitments',
    number: '6',
    title: 'Privacy Commitments',
    summary: 'No advertising, no data sales, and no AI model training on user data.',
  },
  {
    id: 'cookies',
    number: '7',
    title: 'Cookies & Storage',
    summary: 'Strictly necessary session cookies and saved UI preferences.',
  },
  {
    id: 'user-rights',
    number: '8',
    title: 'Your Rights & Account Deletion',
    summary: 'How to request your data or permanently delete your account.',
  },
  {
    id: 'contact',
    number: '9',
    title: 'Contact & Open Source Code',
    summary: 'How to reach the maintainer and view the source code on GitHub.',
  },
] as const;

export function PrivacyPolicyContent(): React.JSX.Element {
  return (
    <div className="w-full max-w-360 mx-auto flex flex-col md:flex-row font-mono text-slate-muted selection:bg-neon-blue selection:text-black">
      {/* Left Sidebar (Desktop Only) - Aligned to the 220px vertical grid line */}
      <aside
        aria-label="Privacy policy table of contents"
        className="hidden md:block w-45 md:w-55 shrink-0 p-5 md:p-8"
      >
        <div className="sticky top-24 space-y-6">
          <div>
            <div className="text-xs uppercase tracking-widest text-ivory flex items-center gap-2 font-semibold">
              <span className="text-neon-blue">■</span>
              <span>Privacy</span>
            </div>
            <p className="mt-2 text-[11px] text-slate-muted/70 leading-relaxed">
              Open source project created by Pavan.
            </p>
          </div>

          <nav aria-label="Table of contents" className="space-y-1.5 pt-2 border-t border-white/10">
            <div className="text-[10px] uppercase tracking-widest text-slate-muted/50 mb-3">
              Sections
            </div>
            {PRIVACY_SECTIONS.map((sec) => (
              <a
                key={sec.id}
                href={`#${sec.id}`}
                className="block text-xs text-slate-muted hover:text-ivory transition-colors py-1 truncate"
                title={`${sec.number}. ${sec.title}`}
              >
                <span className="text-neon-blue mr-1.5">{sec.number}.</span>
                <span>{sec.title}</span>
              </a>
            ))}
          </nav>

          <div className="pt-4 border-t border-white/10 text-[11px] space-y-2">
            <a
              href="https://github.com/paavann/hermes"
              target="_blank"
              rel="noopener noreferrer"
              className="text-neon-blue hover:underline flex items-center gap-1"
            >
              <span>GitHub Repository</span>
              <span>↗</span>
            </a>
            <Link to="/#contact" className="text-slate-muted hover:text-ivory transition-colors block">
              Contact Form →
            </Link>
          </div>
        </div>
      </aside>

      {/* Main Content Area - Strictly to the right of the 220px vertical grid line */}
      <div className="flex-1 min-w-0 px-5 sm:px-8 md:pl-12 lg:pl-16 md:pr-10 lg:pr-14 py-8 md:py-12 space-y-14">
        {/* Page Header */}
        <header className="border-b border-border-subtle pb-8 space-y-4">
          <div className="text-xs uppercase tracking-widest text-neon-blue flex items-center gap-2">
            <span className="w-2 h-2 bg-neon-blue inline-block animate-pulse" />
            <span>Open Source Project</span>
          </div>

          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight text-ivory">
            Privacy Policy
          </h1>

          <p className="text-base sm:text-lg text-slate-muted leading-relaxed max-w-3xl">
            Hermes is an open-source real-time geospatial intelligence project created and maintained by{' '}
            <strong className="text-ivory">Pavan</strong>. This privacy policy clearly explains what
            data is collected, how it is used, and how your privacy is protected when using the platform.
          </p>

          {/* Key Facts Summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs border border-white/10 bg-white/[0.02] p-4 pt-3 mt-4">
            <div>
              <div className="text-[10px] text-slate-muted/60 uppercase tracking-wider mb-1">
                Last Updated
              </div>
              <div className="text-ivory font-medium">October 26, 2026</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-muted/60 uppercase tracking-wider mb-1">
                Project Stage
              </div>
              <div className="text-ivory font-medium">Alpha Prototype</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-muted/60 uppercase tracking-wider mb-1">
                Maintainer
              </div>
              <div className="text-ivory font-medium">Pavan</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-muted/60 uppercase tracking-wider mb-1">
                License & Source
              </div>
              <a
                href="https://github.com/paavann/hermes"
                target="_blank"
                rel="noopener noreferrer"
                className="text-neon-blue hover:underline"
              >
                Open Source (MIT) ↗
              </a>
            </div>
          </div>
        </header>

        {/* 1. Overview */}
        <section id="overview" className="scroll-mt-24 space-y-3">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-ivory flex items-center gap-2">
            <span className="text-neon-blue font-mono">1. </span>
            <span>Overview</span>
          </h2>
          <div className="text-sm leading-relaxed space-y-3">
            <p>
              Hermes is an independent open-source project designed to explore real-time news and global
              events through geographic maps. The system reads publicly available syndicated news feeds,
              geolocates event places, and displays them on a live map interface.
            </p>
            <p>
              Because Hermes is currently an early alpha prototype, it is provided for demonstration,
              educational, and research purposes. We believe in total transparency: we collect only what is
              strictly necessary to let you log in and view the map, and we never sell or monetize your
              information.
            </p>
          </div>
        </section>

        {/* 2. Information We Collect */}
        <section id="information-collected" className="scroll-mt-24 space-y-3">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-ivory flex items-center gap-2">
            <span className="text-neon-blue font-mono">2. </span>
            <span>Information We Collect</span>
          </h2>
          <div className="text-sm leading-relaxed space-y-3">
            <p>
              We practice data minimization and only collect the minimal information needed to operate:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div className="border border-white/10 bg-white/[0.02] p-4 space-y-1.5">
                <div className="text-xs font-semibold text-ivory uppercase tracking-wider">
                  Account Details
                </div>
                <p className="text-xs text-slate-muted leading-relaxed">
                  When you sign up or log in, we collect your email address and basic profile information.
                  Authentication is managed through Clerk. We do not store or see your raw passwords.
                </p>
              </div>

              <div className="border border-white/10 bg-white/[0.02] p-4 space-y-1.5">
                <div className="text-xs font-semibold text-ivory uppercase tracking-wider">
                  Contact Form Messages
                </div>
                <p className="text-xs text-slate-muted leading-relaxed">
                  If you send a message through the contact form, we collect your name, email address,
                  subject, and message text to respond to your inquiry.
                </p>
              </div>

              <div className="border border-white/10 bg-white/[0.02] p-4 space-y-1.5">
                <div className="text-xs font-semibold text-ivory uppercase tracking-wider">
                  Map Viewport Area
                </div>
                <p className="text-xs text-slate-muted leading-relaxed">
                  When you move or zoom the map, your browser sends the coordinates of the visible box to
                  the API to fetch events in that area. We do not save your browsing history or track your
                  personal movements.
                </p>
              </div>

              <div className="border border-white/10 bg-white/[0.02] p-4 space-y-1.5">
                <div className="text-xs font-semibold text-ivory uppercase tracking-wider">
                  Standard Server Logs
                </div>
                <p className="text-xs text-slate-muted leading-relaxed">
                  Like almost all web servers, standard temporary logs (IP address, browser type, request time)
                  are kept briefly by our hosting services to prevent spam and diagnose errors.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* 3. User Accounts & Authentication */}
        <section id="authentication" className="scroll-mt-24 space-y-3">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-ivory flex items-center gap-2">
            <span className="text-neon-blue font-mono">3. </span>
            <span>User Accounts & Authentication</span>
          </h2>
          <div className="text-sm leading-relaxed space-y-3">
            <p>
              We use <strong className="text-ivory">Clerk</strong> to handle all user sign-ups, logins,
              one-time passwords, and session tokens. Clerk is an industry-standard identity provider with
              SOC 2 Type II certification.
            </p>
            <p>
              If you log in with Google or GitHub, Clerk securely verifies your identity and shares your
              verified email address and display name with Hermes. You can read more about how Clerk protects
              data in the{' '}
              <a
                href="https://clerk.com/privacy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-neon-blue hover:underline"
              >
                Clerk Privacy Policy
              </a>
              .
            </p>
          </div>
        </section>

        {/* 4. Map Data & Location Information */}
        <section id="map-data" className="scroll-mt-24 space-y-3">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-ivory flex items-center gap-2">
            <span className="text-neon-blue font-mono">4. </span>
            <span>Map Data & Location Information</span>
          </h2>
          <div className="text-sm leading-relaxed space-y-3">
            <p>
              Hermes uses <strong className="text-ivory">Mapbox GL</strong> to render vector map tiles.
              Map tiles and geographic visuals are downloaded directly from Mapbox servers to your browser.
            </p>
            <p>
              We do not track your real-time physical GPS location, and we never create personal movement
              profiles. Any search queries or map pans remain strictly in your browser session memory.
            </p>
          </div>
        </section>

        {/* 5. Third-Party Services */}
        <section id="third-parties" className="scroll-mt-24 space-y-3">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-ivory flex items-center gap-2">
            <span className="text-neon-blue font-mono">5. </span>
            <span>Third-Party Services</span>
          </h2>
          <div className="text-sm leading-relaxed space-y-3">
            <p>
              We rely on a few trusted third-party providers to keep Hermes running:
            </p>

            <div className="overflow-x-auto border border-white/10 pt-1">
              <table className="w-full text-left text-xs">
                <thead className="bg-white/[0.03] text-ivory uppercase tracking-wider border-b border-white/10">
                  <tr>
                    <th className="py-2.5 px-3">Service</th>
                    <th className="py-2.5 px-3">Purpose</th>
                    <th className="py-2.5 px-3">Data Processed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-muted">
                  <tr>
                    <td className="py-2.5 px-3 font-semibold text-ivory">Clerk</td>
                    <td className="py-2.5 px-3">User login & accounts</td>
                    <td className="py-2.5 px-3">Email, user ID, session token</td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold text-ivory">Mapbox</td>
                    <td className="py-2.5 px-3">Map tiles and visuals</td>
                    <td className="py-2.5 px-3">Standard HTTP requests for map tiles</td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold text-ivory">OpenStreetMap / Nominatim</td>
                    <td className="py-2.5 px-3">Server-side geocoding</td>
                    <td className="py-2.5 px-3">
                      Public city/country names from news articles (client IPs are never shared)
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold text-ivory">Vercel & Render</td>
                    <td className="py-2.5 px-3">Frontend and backend hosting</td>
                    <td className="py-2.5 px-3">HTTP requests and encrypted database storage</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* 6. Privacy Commitments */}
        <section id="commitments" className="scroll-mt-24 space-y-3">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-ivory flex items-center gap-2">
            <span className="text-neon-blue font-mono">6. </span>
            <span>Privacy Commitments</span>
          </h2>
          <div className="border border-neon-blue/30 bg-neon-blue/[0.02] p-5 space-y-3 text-sm">
            <div className="text-xs uppercase tracking-wider text-neon-blue font-semibold">
              Our Plain-Language Promises
            </div>
            <ul className="space-y-2.5 text-xs sm:text-sm text-slate-muted leading-relaxed">
              <li className="flex items-start gap-2">
                <span className="text-neon-blue font-bold">✓</span>
                <div>
                  <strong className="text-ivory">No Ads or Trackers:</strong> We do not use Google
                  Analytics, Meta Pixels, ad retargeting tags, or cross-site tracking scripts.
                </div>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-neon-blue font-bold">✓</span>
                <div>
                  <strong className="text-ivory">No Data Selling:</strong> We do not sell, rent, or trade
                  your personal information or email address to advertisers or data brokers.
                </div>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-neon-blue font-bold">✓</span>
                <div>
                  <strong className="text-ivory">No AI Model Training on Your Data:</strong> While Hermes
                  analyzes public news feeds with language models, your account information and private
                  interactions are never used to train AI models.
                </div>
              </li>
            </ul>
          </div>
        </section>

        {/* 7. Cookies & Local Storage */}
        <section id="cookies" className="scroll-mt-24 space-y-3">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-ivory flex items-center gap-2">
            <span className="text-neon-blue font-mono">7. </span>
            <span>Cookies & Local Storage</span>
          </h2>
          <div className="text-sm leading-relaxed space-y-3">
            <p>
              Hermes only uses strictly necessary cookies and local browser storage:
            </p>
            <ul className="list-disc list-inside space-y-1.5 text-xs sm:text-sm pl-2">
              <li>
                <strong className="text-ivory">Clerk Session Cookies:</strong> Required so you stay logged
                in as you navigate between pages.
              </li>
              <li>
                <strong className="text-ivory">Local Storage:</strong> Remembers your local UI preferences
                (like map filter selections) on your own device.
              </li>
            </ul>
            <p className="text-xs text-slate-muted">
              Because we do not use advertising or third-party tracking cookies, no annoying cookie consent
              banner is required.
            </p>
          </div>
        </section>

        {/* 8. Your Rights & Account Deletion */}
        <section id="user-rights" className="scroll-mt-24 space-y-3">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-ivory flex items-center gap-2">
            <span className="text-neon-blue font-mono">8. </span>
            <span>Your Rights & Account Deletion</span>
          </h2>
          <div className="text-sm leading-relaxed space-y-3">
            <p>
              You are always in control of your data:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
              <div className="border border-white/10 p-3.5 space-y-1">
                <div className="text-xs font-semibold text-ivory">Access Data</div>
                <p className="text-xs text-slate-muted">
                  Ask what personal details (like your email) are linked to your account.
                </p>
              </div>
              <div className="border border-white/10 p-3.5 space-y-1">
                <div className="text-xs font-semibold text-ivory">Delete Account</div>
                <p className="text-xs text-slate-muted">
                  Request complete removal of your account and credentials from Clerk.
                </p>
              </div>
              <div className="border border-white/10 p-3.5 space-y-1">
                <div className="text-xs font-semibold text-ivory">Disconnect Social Logins</div>
                <p className="text-xs text-slate-muted">
                  Revoke Hermes access from your Google or GitHub account at any time.
                </p>
              </div>
            </div>
            <p className="text-xs pt-1">
              To request account deletion or ask any questions, send a message through the{' '}
              <Link to="/#contact" className="text-neon-blue hover:underline">
                Contact Form
              </Link>{' '}
              or open an issue on GitHub. Requests are processed promptly.
            </p>
          </div>
        </section>

        {/* 9. Contact & Open Source Code */}
        <section id="contact" className="scroll-mt-24 space-y-3">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-ivory flex items-center gap-2">
            <span className="text-neon-blue font-mono">9. </span>
            <span>Contact & Open Source Code</span>
          </h2>
          <div className="text-sm leading-relaxed space-y-3">
            <p>
              Hermes is completely open source. You can inspect the entire codebase, including database
              models and background workers, on GitHub:
            </p>
            <div className="border border-white/10 bg-white/[0.015] p-4 text-xs space-y-2">
              <div>
                <span className="text-ivory font-semibold">GitHub Repository:</span>{' '}
                <a
                  href="https://github.com/paavann/hermes"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-neon-blue hover:underline"
                >
                  https://github.com/paavann/hermes
                </a>
              </div>
              <div>
                <span className="text-ivory font-semibold">GitHub Issues:</span>{' '}
                <a
                  href="https://github.com/paavann/hermes/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-neon-blue hover:underline"
                >
                  https://github.com/paavann/hermes/issues
                </a>
              </div>
              <div>
                <span className="text-ivory font-semibold">Direct Message:</span>{' '}
                <Link to="/#contact" className="text-neon-blue hover:underline">
                  Hermes Contact Form (/#contact)
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Footer Navigation */}
        <div className="pt-8 border-t border-white/10 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-muted">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-neon-blue hover:underline flex items-center gap-1">
              <span>←</span>
              <span>Back to Home</span>
            </Link>
            <span className="text-white/20">/</span>
            <Link to="/map" className="hover:text-ivory transition-colors">
              Live Map
            </Link>
          </div>
          <a href="#privacy-header" className="hover:text-ivory transition-colors">
            Back to Top ↑
          </a>
        </div>
      </div>
    </div>
  );
}
