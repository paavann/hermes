import type React from 'react';
import { useNavigate } from 'react-router';
import { HandleSSOCallback } from '@clerk/react-router';

export function SsoCallbackView(): React.JSX.Element {
  const navigate = useNavigate();

  return (
    <div className="w-full flex flex-col items-center py-12 space-y-6">
      <div className="w-10 h-10 border border-neon-blue/40 border-t-neon-blue animate-spin" />
      <div className="text-center space-y-2">
        <h1 className="text-xl font-bold text-ivory tracking-tight font-mono">
          AUTHENTICATING SSO SESSION
        </h1>
        <p className="text-xs text-slate-muted font-mono tracking-wider">
          [ SYSTEM // VERIFYING FEDERATED TOKENS ]
        </p>
      </div>
      <HandleSSOCallback
        navigateToApp={({ decorateUrl }) => {
          const destination = decorateUrl('/map');
          if (destination.startsWith('http')) {
            window.location.href = destination;
            return;
          }
          navigate(destination, { replace: true });
        }}
        navigateToSignIn={() => {
          navigate('/auth', { replace: true });
        }}
        navigateToSignUp={() => {
          navigate('/auth', { replace: true });
        }}
      />
    </div>
  );
}
