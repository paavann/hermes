import { test, expect } from 'vitest';
import { createRoutesStub } from 'react-router';
import { render, screen, fireEvent } from '@testing-library/react';
import Signup from '../../app/routes/sign-up';

test('renders sign-up route with fixed pattern, eye toggle, and social logins', () => {
  const ReactRouterStub = createRoutesStub([
    {
      path: '/sign-up',
      Component: Signup,
    },
  ]);

  render(<ReactRouterStub initialEntries={['/sign-up']} />);

  // Heading and form fields
  expect(screen.getByText('Create your account')).toBeTruthy();
  expect(screen.getByLabelText(/Full Name/i)).toBeTruthy();
  expect(screen.getByLabelText(/Email/i)).toBeTruthy();

  const passwordInput = screen.getByLabelText(/^Password$/i) as HTMLInputElement;
  const confirmPasswordInput = screen.getByLabelText(/^Confirm Password$/i) as HTMLInputElement;
  expect(passwordInput).toBeTruthy();
  expect(confirmPasswordInput).toBeTruthy();
  expect(passwordInput.type).toBe('password');
  expect(confirmPasswordInput.type).toBe('password');

  // Eye toggles
  const showPasswordBtn = screen.getByRole('button', { name: 'Show password' });
  const showConfirmPasswordBtn = screen.getByRole('button', { name: 'Show confirm password' });
  expect(showPasswordBtn).toBeTruthy();
  expect(showConfirmPasswordBtn).toBeTruthy();

  // Toggle password visibility
  fireEvent.click(showPasswordBtn);
  expect(passwordInput.type).toBe('text');
  fireEvent.click(showPasswordBtn);
  expect(passwordInput.type).toBe('password');

  // Social options located below divider
  expect(screen.getByText('OR CONTINUE WITH')).toBeTruthy();
  expect(screen.getByRole('button', { name: /Sign up with Google/i })).toBeTruthy();
  expect(screen.getByRole('button', { name: /Sign up with X \/ Twitter/i })).toBeTruthy();
  expect(screen.getByRole('button', { name: /Sign up with Microsoft/i })).toBeTruthy();
  expect(screen.getByRole('button', { name: /Sign up with Apple/i })).toBeTruthy();

  // Pattern panel is fixed
  const patternAside = screen.getByLabelText('Geometric pattern panel');
  expect(patternAside.className).toContain('fixed');
}, 15000);

test('validates password mismatch on sign-up', () => {
  const ReactRouterStub = createRoutesStub([
    {
      path: '/sign-up',
      Component: Signup,
    },
  ]);

  render(<ReactRouterStub initialEntries={['/sign-up']} />);

  fireEvent.change(screen.getByLabelText(/Full Name/i), { target: { value: 'Operator One' } });
  fireEvent.change(screen.getByLabelText(/Email/i), { target: { value: 'test@hermes.intel' } });
  fireEvent.change(screen.getByLabelText(/^Password$/i), { target: { value: 'Password123' } });
  fireEvent.change(screen.getByLabelText(/^Confirm Password$/i), { target: { value: 'DifferentPassword123' } });

  fireEvent.click(screen.getByRole('button', { name: /Create account/i }));

  expect(screen.getByText(/Passwords do not match/i)).toBeTruthy();
}, 15000);
