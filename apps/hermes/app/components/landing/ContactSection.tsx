import { useState } from 'react';
import type React from 'react';
import { useForm, ValidationError } from '@formspree/react';
import { ArrowUpRight } from '@phosphor-icons/react';
import { Link } from 'react-router';

import {
  Input,
  Textarea,
  Label,
  TacticalActionBtn,
} from '@hermes/ui-components';

import { SectionHeading, SectionRail } from './SectionChrome';

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

const DIRECT_CHANNELS: readonly {
  readonly index: string;
  readonly label: string;
  readonly detail: string;
  readonly href: string;
  readonly external: boolean;
}[] = [
  {
    index: '01',
    label: 'GITHUB',
    detail: 'Source & engineering notes',
    href: 'https://github.com/paavann/hermes',
    external: true,
  },
  {
    index: '02',
    label: 'LIVE MAP',
    detail: 'Observe the current event surface',
    href: '/map',
    external: false,
  },
  {
    index: '03',
    label: 'PRIVACY PROTOCOL',
    detail: 'How data is handled',
    href: '/privacy',
    external: false,
  },
] as const;

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
        formData.subject.trim() ||
        `Inquiry from ${formData.name.trim() || 'Visitor'} via Hermes`,
    },
  });

  const onSubmit = async (
    e: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
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
    <section
      id="contact"
      className="relative w-full border-b border-border-subtle bg-obsidian scroll-mt-16"
    >
      <span id="access" className="absolute -top-20" aria-hidden="true" />

      <div className="mx-auto flex w-full max-w-[1600px] flex-col md:flex-row">
        <SectionRail index="04" label="Contact" meta="Direct channel">
          <div className="mt-10 border-t border-border-subtle pt-4">
            <p className="text-[9px] uppercase leading-relaxed tracking-[0.18em] text-slate-muted/45">
              Messages are read directly. No routing layer, no queue.
            </p>
          </div>
          <div className="mt-8 flex items-center gap-2 text-[9px] uppercase tracking-[0.18em] text-slate-muted/35">
            <span className="h-1 w-1 bg-signal-amber" aria-hidden="true" />
            <span>HTTPS / TLS</span>
          </div>
        </SectionRail>

        <div className="min-w-0 flex-1 border-border-subtle/60 px-5 py-12 md:border-l md:py-16 md:pl-10 md:pr-12 lg:pl-14 lg:pr-16">
          <SectionHeading
            index="04"
            label="Contact"
            meta="Get in touch"
            className="md:hidden"
          />

          <div className="mt-10 grid grid-cols-1 items-start gap-12 md:mt-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)] lg:gap-16">
            <div className="space-y-9">
              <h3 className="max-w-xl font-display text-[clamp(2.1rem,3.6vw,3.5rem)] font-medium leading-[1.02] tracking-[-0.03em] text-bone/55">
                Have questions or feedback?{' '}
                <span className="block text-ivory">
                  Get in touch with me.
                </span>
              </h3>

              <p className="max-w-lg text-sm leading-relaxed text-slate-muted">
                Whether you&apos;re interested in spatial data architecture,
                collaboration on Hermes, research inquiries, or exploring the
                live maps — feel free to reach out. I read all messages
                directly.
              </p>

              <div>
                <div className="mb-3 flex items-center justify-between text-[9px] uppercase tracking-[0.18em] text-slate-muted/40">
                  <span>DIRECT CHANNELS</span>
                  <span>03</span>
                </div>
                <div className="border-t border-border-subtle">
                  {DIRECT_CHANNELS.map((channel) => {
                    const content = (
                      <>
                        <span className="tabular-nums text-[9px] text-slate-muted/35">
                          {channel.index}
                        </span>
                        <span className="flex min-w-0 flex-col">
                          <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-ivory">
                            {channel.label}
                          </span>
                          <span className="mt-0.5 text-[10px] leading-relaxed text-slate-muted/55">
                            {channel.detail}
                          </span>
                        </span>
                        <ArrowUpRight
                          size={13}
                          weight="bold"
                          aria-hidden="true"
                          className="ml-auto shrink-0 text-slate-muted/40 transition-colors group-hover:text-neon-blue"
                        />
                      </>
                    );

                    const className =
                      'group flex items-center gap-4 border-b border-border-subtle/60 py-3.5 transition-colors hover:bg-white/[0.02] focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2';

                    return channel.external ? (
                      <a
                        key={channel.index}
                        href={channel.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={className}
                      >
                        {content}
                      </a>
                    ) : (
                      <Link key={channel.index} to={channel.href} className={className}>
                        {content}
                      </Link>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="w-full border border-border-subtle bg-onyx">
              <div className="flex h-10 items-center justify-between border-b border-border-subtle bg-black px-4">
                <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.2em] text-bone/60">
                  <span className="h-1.5 w-1.5 bg-neon-blue" aria-hidden="true" />
                  <span>SECURE TRANSMISSION</span>
                </div>
                <span className="text-[9px] uppercase tracking-[0.18em] text-slate-muted/35 tabular-nums">
                  FORM / 01
                </span>
              </div>

              {state.succeeded ? (
                <div className="space-y-5 p-6 md:p-8">
                  <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-neon-blue">
                    <span className="h-2 w-2 animate-pulse bg-neon-blue" aria-hidden="true" />
                    <span>MESSAGE RECEIVED</span>
                  </div>
                  <p className="text-sm leading-relaxed text-ivory">
                    Thank you for reaching out. Your message has been received.
                    I&apos;ll get back to you shortly at{' '}
                    <strong className="font-mono text-neon-blue">
                      {formData.email}
                    </strong>
                    .
                  </p>
                  <div className="border-t border-border-subtle pt-4">
                    <button
                      type="button"
                      onClick={handleReset}
                      className="cursor-pointer text-[10px] uppercase tracking-[0.18em] text-slate-muted underline-offset-4 transition-colors hover:text-ivory hover:underline"
                    >
                      Send another message →
                    </button>
                  </div>
                </div>
              ) : (
                <form onSubmit={onSubmit} className="space-y-5 p-5 md:p-6" noValidate>
                  <input
                    type="text"
                    name="_gotcha"
                    tabIndex={-1}
                    autoComplete="off"
                    className="hidden"
                    aria-hidden="true"
                  />

                  <div>
                    <Label
                      htmlFor="contact-name"
                      className="flex items-center justify-between"
                    >
                      <span>NAME *</span>
                      <span className="font-normal tabular-nums text-slate-muted/30">
                        01
                      </span>
                    </Label>
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
                      className="mt-1 font-mono text-[10px] tracking-wide text-danger-bright"
                    />
                  </div>

                  <div>
                    <Label
                      htmlFor="contact-email"
                      className="flex items-center justify-between"
                    >
                      <span>EMAIL ADDRESS *</span>
                      <span className="font-normal tabular-nums text-slate-muted/30">
                        02
                      </span>
                    </Label>
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
                      className="mt-1 font-mono text-[10px] tracking-wide text-danger-bright"
                    />
                  </div>

                  <div>
                    <Label
                      htmlFor="contact-subject"
                      className="flex items-center justify-between"
                    >
                      <span>SUBJECT</span>
                      <span className="font-normal tabular-nums text-slate-muted/30">
                        03
                      </span>
                    </Label>
                    <Input
                      id="contact-subject"
                      name="subject"
                      type="text"
                      value={formData.subject}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          subject: e.target.value,
                        }))
                      }
                      placeholder="Collaboration, question, feedback..."
                    />
                    <ValidationError
                      prefix="Subject"
                      field="subject"
                      errors={state.errors}
                      className="mt-1 font-mono text-[10px] tracking-wide text-danger-bright"
                    />
                  </div>

                  <div>
                    <Label
                      htmlFor="contact-message"
                      className="flex items-center justify-between"
                    >
                      <span>MESSAGE *</span>
                      <span className="font-normal tabular-nums text-slate-muted/30">
                        04
                      </span>
                    </Label>
                    <Textarea
                      id="contact-message"
                      name="message"
                      rows={4}
                      required
                      value={formData.message}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          message: e.target.value,
                        }))
                      }
                      placeholder="Write your message here..."
                    />
                    <ValidationError
                      prefix="Message"
                      field="message"
                      errors={state.errors}
                      className="mt-1 font-mono text-[10px] tracking-wide text-danger-bright"
                    />
                  </div>

                  {clientError !== null ? (
                    <div className="text-center font-mono text-[10px] tracking-wide text-danger-bright">
                      {clientError}
                    </div>
                  ) : null}

                  <ValidationError
                    errors={state.errors}
                    className="text-center font-mono text-[10px] tracking-wide text-danger-bright"
                  />

                  <SendMessageBtn
                    isSubmitting={state.submitting}
                    disabled={state.submitting}
                  />

                  <p className="text-[9px] uppercase tracking-[0.16em] text-slate-muted/35">
                    TRANSMITTED OVER HTTPS
                  </p>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// Alias for backward compatibility
export const AccessSection = ContactSection;
