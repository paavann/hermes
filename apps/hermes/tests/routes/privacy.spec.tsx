import type React from 'react';
import { createRoutesStub } from 'react-router';
import { render, screen } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import PrivacyRoute, { meta } from '../../app/routes/privacy';

let mockAuthState: 'signed-out' | 'signed-in' = 'signed-out';

vi.mock('@clerk/react-router', () => ({
  Show: ({ when, children }: { when: string; children: React.ReactNode }) =>
    when === mockAuthState ? children : null,
  SignOutButton: ({ children }: { children: React.ReactNode }) => children,
  SignInButton: ({ children }: { children: React.ReactNode }) => children,
  SignUpButton: ({ children }: { children: React.ReactNode }) => children,
}));

describe('Privacy Route', () => {
  beforeEach(() => {
    mockAuthState = 'signed-out';
  });

  const ReactRouterStub = createRoutesStub([
    {
      path: '/privacy',
      Component: PrivacyRoute,
    },
  ]);

  it('renders privacy title, key metadata, and maintainer without fancy tech jargon', () => {
    render(<ReactRouterStub initialEntries={['/privacy']} />);

    expect(screen.getByRole('heading', { level: 1, name: 'Privacy Policy' })).toBeTruthy();
    expect(screen.getAllByText(/Pavan/).length).toBeGreaterThan(0);
    expect(screen.getByText('Alpha Prototype')).toBeTruthy();
    expect(screen.getByText('October 26, 2026')).toBeTruthy();

    // Verify fancy tech jargon is completely removed
    expect(screen.queryByText(/SYS \/\//)).toBeNull();
    expect(screen.queryByText(/SPEC-PRIVACY/)).toBeNull();
    expect(screen.queryByText(/ALPHA PROTOTYPE NOTICE/)).toBeNull();
    expect(screen.queryByText(/CLEARANCE/)).toBeNull();
  }, 15000);

  it('renders all key protocol sections and plain-language commitments', () => {
    render(<ReactRouterStub initialEntries={['/privacy']} />);

    // Section headings
    expect(screen.getByRole('heading', { name: /1\.\s*Overview/ })).toBeTruthy();
    expect(screen.getByRole('heading', { name: /2\.\s*Information We Collect/ })).toBeTruthy();
    expect(screen.getByRole('heading', { name: /3\.\s*User Accounts & Authentication/ })).toBeTruthy();
    expect(screen.getByRole('heading', { name: /4\.\s*Map Data & Location Information/ })).toBeTruthy();
    expect(screen.getByRole('heading', { name: /5\.\s*Third-Party Services/ })).toBeTruthy();
    expect(screen.getByRole('heading', { name: /6\.\s*Privacy Commitments/ })).toBeTruthy();
    expect(screen.getByRole('heading', { name: /7\.\s*Cookies & Local Storage/ })).toBeTruthy();
    expect(screen.getByRole('heading', { name: /8\.\s*Your Rights & Account Deletion/ })).toBeTruthy();
    expect(screen.getByRole('heading', { name: /9\.\s*Contact & Open Source Code/ })).toBeTruthy();

    // Plain-language commitments
    expect(screen.getByText(/No Ads or Trackers:/)).toBeTruthy();
    expect(screen.getByText(/No Data Selling:/)).toBeTruthy();
    expect(screen.getByText(/No AI Model Training on Your Data:/)).toBeTruthy();

    // Third-party disclosures
    expect(screen.getAllByText('Clerk').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Mapbox').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/OpenStreetMap \/ Nominatim/).length).toBeGreaterThan(0);
  }, 15000);

  it('renders navigation links and brutalist footer', () => {
    render(<ReactRouterStub initialEntries={['/privacy']} />);

    expect(screen.getByRole('link', { name: 'Hermes Home' })).toBeTruthy();
    expect(screen.getByText('LAUNCH MAP')).toBeTruthy();

    // Footer
    expect(screen.getByText(/HERMES GEOINT INC/)).toBeTruthy();
    expect(screen.getAllByText('Privacy Protocol').length).toBeGreaterThan(0);
  }, 15000);

  it('renders LOGIN link when signed out and LOGOUT button when signed in', () => {
    const { unmount } = render(<ReactRouterStub initialEntries={['/privacy']} />);
    expect(screen.getByRole('link', { name: 'LOGIN' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'LOGOUT' })).toBeNull();
    unmount();

    mockAuthState = 'signed-in';
    render(<ReactRouterStub initialEntries={['/privacy']} />);
    expect(screen.getByRole('button', { name: 'LOGOUT' })).toBeTruthy();
    expect(screen.queryByRole('link', { name: 'LOGIN' })).toBeNull();
  }, 15000);

  it('exports valid metadata for SEO and social graphs', () => {
    const metadata = meta({} as Parameters<typeof meta>[0]);
    expect(metadata).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          title: 'Privacy Policy — Hermes Geospatial Intelligence',
        }),
        expect.objectContaining({ name: 'description' }),
      ]),
    );
  });
});
