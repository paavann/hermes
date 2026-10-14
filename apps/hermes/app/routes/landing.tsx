import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import type { MetaFunction } from 'react-router'
import './landing.css'
import satelliteImg from '../assets/satellite.jpg'
import mapChartImg from '../assets/map-chart.jpg'
import darkTextureImg from '../assets/dark-texture.jpg'


export const meta: MetaFunction = () => [
  { title: 'Hermes — Geospatial Intelligence' },
  { name: 'description', content: 'Real-time geospatial news aggregation. Watch the world\'s events unfold on an interactive intelligence map.' },
  { property: 'og:title', content: 'Hermes — Geospatial Intelligence' },
  { property: 'og:description', content: 'Real-time geospatial news intelligence. Monitor global events as they unfold.' },
]


// ─── Scramble Text Hook ──────────────────────────────────────────────────────

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*<>/\\|[]{}~'

function useScramble(finalText: string, delay = 0) {
  const [display, setDisplay] = useState('')
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>
    let iteration = 0
    const len = finalText.length

    function animate() {
      setDisplay(
        finalText
          .split('')
          .map((char, idx) => {
            if (char === ' ') return ' '
            if (idx < iteration) return finalText[idx]
            return CHARS[Math.floor(Math.random() * CHARS.length)]
          })
          .join(''),
      )
      iteration += 0.5
      if (iteration < len) {
        rafRef.current = requestAnimationFrame(animate)
      } else {
        setDisplay(finalText)
      }
    }

    timeoutId = setTimeout(() => {
      rafRef.current = requestAnimationFrame(animate)
    }, delay)

    return () => {
      clearTimeout(timeoutId)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [finalText, delay])

  return display
}


// ─── Animated Counter Hook ────────────────────────────────────────────────────

function useCounter(target: number, duration = 2000, delay = 0) {
  const [count, setCount] = useState(0)
  const [started, setStarted] = useState(false)

  useEffect(() => {
    const timeout = setTimeout(() => setStarted(true), delay)
    return () => clearTimeout(timeout)
  }, [delay])

  useEffect(() => {
    if (!started) return
    let startTime: number | null = null

    function step(timestamp: number) {
      if (!startTime) startTime = timestamp
      const progress = Math.min((timestamp - startTime) / duration, 1)
      setCount(Math.floor(progress * target))
      if (progress < 1) requestAnimationFrame(step)
    }

    requestAnimationFrame(step)
  }, [started, target, duration])

  return count
}


// ─── Intersection Observer Hook ───────────────────────────────────────────────

function useInView(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setInView(true)
      },
      { threshold },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [threshold])

  return { ref, inView }
}


// ─── Nav ──────────────────────────────────────────────────────────────────────

function Nav() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav
      id="nav"
      role="navigation"
      aria-label="Primary navigation"
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? 'nav-scrolled' : ''
      }`}
      style={{
        borderBottom: scrolled ? '1px solid rgba(0, 255, 200, 0.12)' : '1px solid transparent',
        background: scrolled ? 'rgba(0, 0, 0, 0.92)' : 'transparent',
        backdropFilter: scrolled ? 'blur(12px)' : 'none',
      }}
    >
      <div className="nav-inner">
        {/* Logo */}
        <Link to="/" aria-label="Hermes home" className="nav-logo">
          <span className="logo-mark" aria-hidden="true">▸</span>
          <span className="logo-text">HERMES</span>
        </Link>

        {/* Nav Divider */}
        <div className="nav-divider" aria-hidden="true" />

        {/* Label */}
        <span className="nav-label" aria-hidden="true">■ LIVE INTEL</span>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* CTA Buttons */}
        <div className="nav-actions" role="group" aria-label="Primary actions">
          <Link
            to="/login"
            id="nav-sign-in"
            className="btn-ghost"
            aria-label="Sign in to your account"
          >
            SIGN IN
          </Link>
          <Link
            to="/map"
            id="nav-launch-map"
            className="btn-primary"
            aria-label="Launch the intelligence map"
          >
            LAUNCH MAP
          </Link>
        </div>
      </div>
    </nav>
  )
}


// ─── Hero Section ─────────────────────────────────────────────────────────────

function Hero() {
  const line1 = useScramble('Real-time geospatial', 400)
  const line2 = useScramble('intelligence for a', 900)
  const line3 = useScramble('shifting world.', 1400)
  const sub = useScramble('Monitor global events as they unfold.', 2000)

  return (
    <section
      id="hero"
      aria-label="Hero section"
      className="hero-section"
      style={{
        backgroundImage: `url(${darkTextureImg})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    >
      {/* Noise overlay */}
      <div className="hero-overlay" aria-hidden="true" />

      {/* Scan line effect */}
      <div className="scanline" aria-hidden="true" />

      {/* Corner decorations */}
      <div className="corner corner-tl" aria-hidden="true" />
      <div className="corner corner-tr" aria-hidden="true" />
      <div className="corner corner-bl" aria-hidden="true" />
      <div className="corner corner-br" aria-hidden="true" />

      {/* Status bar */}
      <div className="hero-status" aria-hidden="true">
        <span className="status-dot" />
        <span>SYS NOMINAL</span>
        <span className="status-sep">|</span>
        <span>FEED ACTIVE</span>
        <span className="status-sep">|</span>
        <span>UPTIME 99.97%</span>
      </div>

      {/* Main content */}
      <div className="hero-content">
        <div className="hero-eyebrow" aria-hidden="true">
          <span className="eyebrow-line" />
          <span>HERMES INTELLIGENCE PLATFORM</span>
          <span className="eyebrow-line" />
        </div>

        <h1 className="hero-headline" aria-label="Real-time geospatial intelligence for a shifting world.">
          <span className="headline-line dim" aria-hidden="true">{line1}</span>
          <br />
          <span className="headline-line dim" aria-hidden="true">{line2}</span>
          <br />
          <span className="headline-line bright" aria-hidden="true">{line3}</span>
        </h1>

        <p className="hero-sub" aria-label="Monitor global events as they unfold.">{sub}</p>

        <div className="hero-actions" role="group" aria-label="Hero call to action">
          <Link
            to="/map"
            id="hero-launch-map"
            className="btn-primary btn-large"
            aria-label="Launch the intelligence map"
          >
            LAUNCH MAP
          </Link>
          <Link
            to="/login"
            id="hero-sign-in"
            className="btn-ghost btn-large"
            aria-label="Sign in to your account"
          >
            SIGN IN
          </Link>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="scroll-indicator" aria-hidden="true">
        <span>SCROLL</span>
        <div className="scroll-line" />
      </div>
    </section>
  )
}


// ─── Stats Section ────────────────────────────────────────────────────────────

function StatItem({ value, suffix, label, delay }: { value: number; suffix: string; label: string; delay: number }) {
  const { ref, inView } = useInView()
  const count = useCounter(inView ? value : 0, 2000, delay)

  return (
    <div ref={ref} className="stat-item">
      <div className="stat-value">
        {count.toLocaleString()}
        <span className="stat-suffix">{suffix}</span>
      </div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

function Stats() {
  return (
    <section id="stats" aria-label="Platform statistics" className="stats-section">
      <div className="stats-grid">
        <StatItem value={10000} suffix="+" label="EVENTS TRACKED" delay={0} />
        <StatItem value={120} suffix="+" label="NEWS SOURCES" delay={200} />
        <StatItem value={195} suffix="" label="COUNTRIES COVERED" delay={400} />
        <StatItem value={99} suffix=".97%" label="UPTIME SLA" delay={600} />
      </div>
    </section>
  )
}


// ─── Feature Cards ────────────────────────────────────────────────────────────

const FEATURES = [
  {
    id: 'feature-spatial',
    icon: '◈',
    title: 'SPATIAL INTELLIGENCE',
    body: 'Events are geocoded with sub-city accuracy using a PostGIS spatial engine. Browse by viewport — zoom in and hyper-local events populate in real time.',
  },
  {
    id: 'feature-consensus',
    icon: '◉',
    title: 'SOURCE CONSENSUS',
    body: 'Our ranking engine cross-references 120+ independent feeds. When multiple credible sources confirm an event, its signal rises — noise gets buried.',
  },
  {
    id: 'feature-timeline',
    icon: '▦',
    title: 'HISTORICAL LINEAGE',
    body: 'Trace any active event back through history. The Timeline Engine synthesizes Wikipedia milestones into a causal chain that leads to today.',
  },
  {
    id: 'feature-decay',
    icon: '◌',
    title: 'TIME DECAY ALGORITHM',
    body: 'Stale news disappears organically. A -10% hourly decay ensures only relevant, current events occupy the map — no lingering noise.',
  },
]

function FeatureCard({ id, icon, title, body, delay }: { id: string; icon: string; title: string; body: string; delay: number }) {
  const { ref, inView } = useInView()

  return (
    <article
      id={id}
      ref={ref}
      className="feature-card"
      style={{
        opacity: inView ? 1 : 0,
        transform: inView ? 'translateY(0)' : 'translateY(24px)',
        transition: `opacity 0.6s ease ${delay}ms, transform 0.6s ease ${delay}ms`,
      }}
    >
      <div className="feature-icon" aria-hidden="true">{icon}</div>
      <h3 className="feature-title">{title}</h3>
      <p className="feature-body">{body}</p>
    </article>
  )
}

function Features() {
  return (
    <section id="features" aria-label="Platform features" className="features-section">
      <div className="section-header">
        <div className="section-eyebrow" aria-hidden="true">
          <span className="eyebrow-line short" />
          <span>CAPABILITIES</span>
        </div>
        <h2 className="section-title">How it works</h2>
      </div>
      <div className="features-grid">
        {FEATURES.map((f, i) => (
          <FeatureCard key={f.id} {...f} delay={i * 120} />
        ))}
      </div>
    </section>
  )
}


// ─── Image Strip ──────────────────────────────────────────────────────────────

function ImageStrip() {
  const { ref, inView } = useInView(0.1)

  return (
    <section
      id="image-strip"
      ref={ref}
      aria-label="Visual showcase"
      className="image-strip"
      style={{
        opacity: inView ? 1 : 0,
        transition: 'opacity 0.8s ease',
      }}
    >
      <figure className="strip-image strip-large">
        <img
          src={mapChartImg}
          alt="Physical map charts on concrete surface showing geospatial data"
          loading="lazy"
          decoding="async"
          width={800}
          height={533}
        />
        <figcaption className="strip-caption">
          <span className="caption-label">■</span> DATA LAYER
        </figcaption>
      </figure>
      <figure className="strip-image strip-small">
        <img
          src={satelliteImg}
          alt="Satellite aerial view of terrain with grid overlays"
          loading="lazy"
          decoding="async"
          width={400}
          height={400}
        />
        <figcaption className="strip-caption">
          <span className="caption-label">■</span> SATELLITE VIEW
        </figcaption>
      </figure>
    </section>
  )
}


// ─── CTA Section ─────────────────────────────────────────────────────────────

function CTA() {
  const { ref, inView } = useInView()

  return (
    <section
      id="cta"
      ref={ref}
      aria-label="Call to action"
      className="cta-section"
      style={{
        opacity: inView ? 1 : 0,
        transform: inView ? 'translateY(0)' : 'translateY(32px)',
        transition: 'opacity 0.7s ease, transform 0.7s ease',
      }}
    >
      <div className="cta-inner">
        <div className="cta-eyebrow" aria-hidden="true">
          <span className="eyebrow-line short" />
          <span>READY TO DEPLOY</span>
        </div>
        <h2 className="cta-title">
          See the world{' '}
          <span className="cta-highlight">as it happens.</span>
        </h2>
        <p className="cta-sub">
          No scrolling. No noise. Just the events that matter, precisely where they happen.
        </p>
        <div className="cta-actions" role="group" aria-label="Launch actions">
          <Link
            to="/map"
            id="cta-launch-map"
            className="btn-primary btn-large"
            aria-label="Open the intelligence map"
          >
            OPEN MAP
          </Link>
          <Link
            to="/login"
            id="cta-sign-in"
            className="btn-ghost btn-large"
            aria-label="Create an account"
          >
            CREATE ACCOUNT
          </Link>
        </div>
      </div>
    </section>
  )
}


// ─── Footer ───────────────────────────────────────────────────────────────────

function Footer() {
  return (
    <footer id="footer" role="contentinfo" className="site-footer">
      <div className="footer-inner">
        <div className="footer-logo">
          <span className="logo-mark" aria-hidden="true">▸</span>
          <span className="logo-text">HERMES</span>
        </div>
        <p className="footer-copy">
          © {new Date().getFullYear()} Hermes Intelligence Platform. All rights reserved.
        </p>
        <nav aria-label="Footer navigation" className="footer-nav">
          <Link to="/map" id="footer-map" className="footer-link">Map</Link>
          <Link to="/login" id="footer-login" className="footer-link">Sign In</Link>
        </nav>
      </div>
    </footer>
  )
}


// ─── Landing Page ─────────────────────────────────────────────────────────────

export default function Landing() {
  return (
    <>
      <Nav />
      <main id="main-content">
        <Hero />
        <Stats />
        <Features />
        <ImageStrip />
        <CTA />
      </main>
      <Footer />
    </>
  )
}
