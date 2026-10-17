import { test, expect } from 'vitest';
import { createRoutesStub } from 'react-router';
import { render, screen, fireEvent } from '@testing-library/react';
import Login from '../../app/routes/login';

test('renders login route with fixed pattern and password eye toggle', () => {
  const ReactRouterStub = createRoutesStub([
    {
      path: '/login',
      Component: Login,
    },
  ]);

  render(<ReactRouterStub initialEntries={['/login']} />);

  // Heading and form fields
  expect(screen.getByText('Welcome back!')).toBeTruthy();
  expect(screen.getByLabelText(/Email/i)).toBeTruthy();

  const passwordInput = screen.getByLabelText(/^Password$/i) as HTMLInputElement;
  expect(passwordInput).toBeTruthy();
  expect(passwordInput.type).toBe('password');

  // Eye toggle button
  const toggleBtn = screen.getByRole('button', { name: /Show password/i });
  expect(toggleBtn).toBeTruthy();

  // Toggle visibility
  fireEvent.click(toggleBtn);
  expect(passwordInput.type).toBe('text');
  fireEvent.click(toggleBtn);
  expect(passwordInput.type).toBe('password');

  // Submit button
  expect(screen.getByRole('button', { name: /Log in/i })).toBeTruthy();

  // Pattern panel is fixed
  const patternAside = screen.getByLabelText('Geometric pattern panel');
  expect(patternAside.className).toContain('fixed');
}, 15000);

test('validates required fields on login', () => {
  const ReactRouterStub = createRoutesStub([
    {
      path: '/login',
      Component: Login,
    },
  ]);

  render(<ReactRouterStub initialEntries={['/login']} />);

  fireEvent.click(screen.getByRole('button', { name: /Log in/i }));

  expect(screen.getByText(/Email and password are required/i)).toBeTruthy();
}, 15000);
