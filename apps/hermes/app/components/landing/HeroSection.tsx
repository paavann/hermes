import type React from 'react'
import earthOrbitImg from '../../assets/earth-orbit.jpg'





export function HeroSection(): React.JSX.Element {
  return (
    <section id="hero" className="relative w-full scroll-mt-16">
      <div className="w-full pl-5 md:pl-60 pr-5 md:pr-8 pt-6 md:pt-10 pb-8 md:pb-12 max-w-6xl ml-5">
        <div className="text-xs uppercase tracking-[0.2em] text-slate-muted/70 mb-4 flex items-center gap-2">
          <span className="text-neon-blue">■</span>
          <span>Hermes Intelligence</span>
        </div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-medium tracking-tight text-slate-muted leading-tight">
          Global event observability for{' '}
          <span className="text-ivory font-bold">
            the world's most critical decisions.
          </span>
        </h1>
      </div>


      <div className="relative w-full border-t border-b border-border-subtle bg-black overflow-hidden">
        <div className="relative w-full aspect-16/10 md:aspect-21/10 md:min-h-145 lg:min-h-160 overflow-hidden">
          <img
            src={earthOrbitImg}
            alt="Earth orbital satellite view"
            className="w-full h-full object-cover object-top opacity-85"
            loading="eager"
          />
          <div className="absolute inset-0 bg-linear-to-r from-obsidian/90 via-obsidian/40 to-transparent" />
          <div className="absolute inset-0 bg-linear-to-t from-obsidian via-transparent to-obsidian/30" />

          <div className="absolute inset-0 flex flex-col justify-between pl-5 md:pl-60 pr-5 md:pr-8 py-10 md:py-16 max-w-4xl z-10 pointer-events-auto">
            <div className="pt-2 md:pt-4">
              <p className="text-base sm:text-lg md:text-xl text-slate-muted leading-relaxed max-w-2xl md:max-w-2xl ml-5">
                I built Hermes to change how you experience the world. Instead of getting lost
                in overwhelming feeds and endless headlines, observe critical global events
                unfold in real time—with spatial context and quiet clarity.
              </p>
            </div>

            <div className="text-[10px] text-slate-muted/70 uppercase tracking-widest font-mono flex items-center gap-2 ml-5">
              <span className="w-1.5 h-1.5 bg-neon-blue inline-block animate-pulse" />
              <span>SYS // ORBITAL OBSERVABILITY • SRID 4326</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
