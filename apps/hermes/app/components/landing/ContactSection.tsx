import { useState } from 'react';
import type React from 'react';
import { useForm, ValidationError } from '@formspree/react';
import {
  Input,
  Textarea,
  Label,
  TacticalActionBtn,
} from '@hermes/ui-components';

export interface SendMessageBtnProps {
  readonly isSubmitting?: boolean;
  readonly disabled?: boolean;
  readonly className?: string;
}

export function SendMessageBtn({
  isSubmitting = false,
  disabled = false,
  className,
}: SendMessageBtnProps): React.JSX.Element {
  return (
    <TacticalActionBtn
      label="SEND MESSAGE"
      loadingLabel="SENDING..."
      isSubmitting={isSubmitting}
      disabled={disabled}
      variant="slide"
      ariaLabel="Send message"
      className={className}
    />
  );
}

export interface ContactFormData {
  readonly name: string;
  readonly email: string;
  readonly subject: string;
  readonly message: string;
}

export function ContactSection(): React.JSX.Element {
  const [formData, setFormData] = useState<ContactFormData>({
    name: '',
    email: '',
    subject: '',
    message: '',
  });
  const [clientError, setClientError] = useState<string | null>(null);

  const [state, handleSubmit, reset] = useForm('mqpppqar', {
    data: {
      _subject: () =>
        formData.subject.trim() || `Inquiry from ${formData.name.trim() || 'Visitor'} via Hermes`,
    },
  });

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.email.trim() || !formData.message.trim()) {
      setClientError('Name, email, and message are required.');
      return;
    }
    setClientError(null);
    await handleSubmit(e);
  };

  const handleReset = (): void => {
    setFormData({ name: '', email: '', subject: '', message: '' });
    setClientError(null);
    reset();
  };

  return (
    <section id="contact" className="relative w-full border-b border-border-subtle bg-obsidian scroll-mt-16 pt-10">
      {/* Anchor for backward compatibility if navigated from #access */}
      <span id="access" className="absolute -top-20" aria-hidden="true" />

      {/* Left Column (Sticky Sidebar Track aligned with 180px/220px vertical line) */}
      <div className="hidden md:block absolute top-0 bottom-0 left-0 w-45 md:w-55 z-30 pointer-events-none mt-5">
        <div className="sticky top-24 p-5 md:p-8 pointer-events-auto">
          <h2 className="text-xs uppercase tracking-widest text-ivory flex items-center gap-2">
            <span className="text-neon-blue">■</span>
            <span>Contact</span>
          </h2>
          <div className="mt-4 text-[10px] text-slate-muted/50 tracking-widest font-mono">
            03 // GET IN TOUCH
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="relative z-10 w-full pl-10 md:pl-60 ml-5 pr-5 md:pr-12 lg:pr-16 pt-10 md:pt-8 pb-16 md:pb-24 max-w-7xl">
        {/* Mobile Section Header */}
        <div className="md:hidden mb-6 flex items-center gap-2 text-xs uppercase tracking-widest text-ivory">
          <span className="text-neon-blue">■</span>
          <span>Contact</span>
        </div>

        {/* Section Tag */}
        <div className="text-xs uppercase tracking-widest text-slate-muted/70 mb-6 md:mb-8 flex items-center gap-2">
          <span className="text-neon-blue">■</span>
          <span>03 // CONTACT</span>
        </div>

        {/* Two-Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start">
          {/* Left Column: Headline, Narrative & Security Badges */}
          <div className="space-y-8 max-w-xl">
            <h3 className="text-3xl sm:text-4xl md:text-5xl font-medium tracking-tight text-slate-muted leading-tight">
              Have questions or feedback?{' '}
              <span className="text-ivory font-bold block mt-2">
                Get in touch with me.
              </span>
            </h3>

            <p className="text-base sm:text-lg text-slate-muted leading-relaxed">
              Whether you're interested in spatial data architecture, collaboration on Hermes,
              research inquiries, or exploring the live maps—feel free to reach out. I read all
              messages directly.
            </p>
          </div>

          {/* Right Column: Brutalist Tactical Form */}
          <div className="w-full max-w-lg">
            {state.succeeded ? (
              <div className="border border-neon-blue/40 bg-neon-blue/5 p-6 md:p-8 space-y-5">
                <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-neon-blue">
                  <span className="w-2 h-2 bg-neon-blue inline-block animate-pulse" />
                  <span>MESSAGE RECEIVED</span>
                </div>
                <p className="text-sm text-ivory leading-relaxed">
                  Thank you for reaching out! Your message has been received. I'll get back to you shortly at{' '}
                  <strong className="text-neon-blue font-mono">{formData.email}</strong>.
                </p>
                <div className="pt-4 border-t border-neon-blue/20">
                  <button
                    type="button"
                    onClick={handleReset}
                    className="text-xs uppercase tracking-widest text-slate-muted hover:text-ivory transition-colors underline underline-offset-4 cursor-pointer"
                  >
                    Send another message →
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={onSubmit} className="space-y-5" noValidate>
                {/* Honeypot anti-spam field (hidden from human visitors) */}
                <input
                  type="text"
                  name="_gotcha"
                  tabIndex={-1}
                  autoComplete="off"
                  className="hidden"
                  aria-hidden="true"
                />

                <div>
                  <Label htmlFor="contact-name">NAME *</Label>
                  <Input
                    id="contact-name"
                    name="name"
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, name: e.target.value }))
                    }
                    placeholder="Your name"
                  />
                  <ValidationError
                    prefix="Name"
                    field="name"
                    errors={state.errors}
                    className="text-xs text-rose-400 font-mono tracking-wide mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="contact-email">EMAIL ADDRESS *</Label>
                  <Input
                    id="contact-email"
                    name="email"
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, email: e.target.value }))
                    }
                    placeholder="name@example.com"
                  />
                  <ValidationError
                    prefix="Email"
                    field="email"
                    errors={state.errors}
                    className="text-xs text-rose-400 font-mono tracking-wide mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="contact-subject">SUBJECT</Label>
                  <Input
                    id="contact-subject"
                    name="subject"
                    type="text"
                    value={formData.subject}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, subject: e.target.value }))
                    }
                    placeholder="e.g. Collaboration, Question, Feedback..."
                  />
                  <ValidationError
                    prefix="Subject"
                    field="subject"
                    errors={state.errors}
                    className="text-xs text-rose-400 font-mono tracking-wide mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="contact-message">MESSAGE *</Label>
                  <Textarea
                    id="contact-message"
                    name="message"
                    rows={4}
                    required
                    value={formData.message}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, message: e.target.value }))
                    }
                    placeholder="Write your message here..."
                  />
                  <ValidationError
                    prefix="Message"
                    field="message"
                    errors={state.errors}
                    className="text-xs text-rose-400 font-mono tracking-wide mt-1"
                  />
                </div>

                {clientError && (
                  <div className="text-xs text-rose-400 font-mono tracking-wide text-center">
                    {clientError}
                  </div>
                )}

                <ValidationError
                  errors={state.errors}
                  className="text-xs text-rose-400 font-mono tracking-wide text-center"
                />

                <SendMessageBtn isSubmitting={state.submitting} disabled={state.submitting} />
              </form>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

// Alias for backward compatibility
export const AccessSection = ContactSection;
