import type React from 'react'
import { Link, redirect } from 'react-router'
import type { MetaFunction, LoaderFunctionArgs } from 'react-router'
import { getAuth } from '@clerk/react-router/server'
import { HermesWordmark, cn } from '@hermes/ui-components'
import {
  AuthCheckerboardPattern,
  EmailStep,
  OtpStep,
  SetupStep,
  SsoCallbackView,
  useAuthWorkflow,
} from '../components/auth'

export async function loader(args: LoaderFunctionArgs) {
  const { userId } = await getAuth(args)
  if (userId) {
    return redirect('/map')
  }
  return {}
}

export const meta: MetaFunction = ({ location }) => {
  const isSso = location?.pathname?.includes('/sso-callback')
  return [
    {
      title: isSso
        ? 'SSO Verification — Hermes Geospatial Intelligence'
        : 'Authenticate — Hermes Geospatial Intelligence',
    },
    {
      name: 'description',
      content: 'Authenticate into the Hermes geospatial intelligence platform.',
    },
  ]
}

export default function Auth(): React.JSX.Element {
  const auth = useAuthWorkflow()

  return (
    <div
      className={cn(
        'w-full bg-obsidian text-slate-muted font-mono selection:bg-neon-blue/20 selection:text-neon-blue flex flex-col lg:flex-row',
        auth.currentMode === 'setup'
          ? 'h-screen max-h-screen overflow-hidden'
          : 'min-h-screen overflow-x-hidden'
      )}
    >
      {/* Left Side: Header + Centered Progressive Auth Form (~70% width on desktop) */}
      <div
        className={cn(
          'w-full lg:w-[70%] flex flex-col justify-between px-6 sm:px-12 md:px-16 py-7 relative z-10',
          auth.currentMode === 'setup'
            ? 'h-screen max-h-screen overflow-hidden py-4 sm:py-6'
            : 'min-h-screen'
        )}
      >
        <header role="banner" className="flex items-center">
          <Link
            to="/"
            aria-label="Hermes Home"
            className="font-bold tracking-[0.25em] text-sm text-ivory hover:text-white transition-colors"
          >
            HERMES
          </Link>
        </header>

        <main
          className={cn(
            'w-full max-w-[390px] mx-auto my-auto flex flex-col items-center',
            auth.currentMode === 'setup' ? 'py-2 sm:py-4' : 'py-12'
          )}
        >
          <HermesWordmark className="w-[185px] sm:w-[205px] mb-6 text-[#8F8C7C]" />

          <div ref={auth.modeContainerRef} className="w-full flex flex-col items-center">
            {auth.isSsoCallback ? (
              <SsoCallbackView />
            ) : auth.currentMode === 'email' || auth.currentMode === 'login' ? (
              <EmailStep
                mode={auth.currentMode}
                email={auth.email}
                password={auth.password}
                isBusy={auth.isBusy}
                status={auth.status}
                activeOAuth={auth.activeOAuth}
                errorMsg={auth.errorMsg}
                onEmailChange={auth.setEmail}
                onPasswordChange={auth.setPassword}
                onSubmit={
                  auth.currentMode === 'login'
                    ? auth.handlePasswordSubmit
                    : auth.handleEmailSubmit
                }
                onSelectOAuth={auth.handleOAuthClick}
                onChangeEmail={auth.handleChangeEmail}
                onForgotPassword={auth.handleSwitchToOtpFromLogin}
              />
            ) : auth.currentMode === 'otp' ? (
              <OtpStep
                email={auth.email}
                otpDigits={auth.otpDigits}
                otpInputRefs={auth.otpInputRefs}
                isBusy={auth.isBusy}
                status={auth.status}
                resendCooldown={auth.resendCooldown}
                errorMsg={auth.errorMsg}
                onOtpChange={auth.handleOtpChange}
                onOtpKeyDown={auth.handleOtpKeyDown}
                onOtpPaste={auth.handleOtpPaste}
                onSubmit={auth.handleOtpSubmit}
                onResend={auth.handleResendOtp}
                onChangeEmail={auth.handleChangeEmail}
              />
            ) : (
              <SetupStep
                email={auth.email}
                fullName={auth.fullName}
                password={auth.password}
                confirmPassword={auth.confirmPassword}
                isBusy={auth.isBusy}
                status={auth.status}
                errorMsg={auth.errorMsg}
                onFullNameChange={auth.setFullName}
                onPasswordChange={auth.setPassword}
                onConfirmPasswordChange={auth.setConfirmPassword}
                onSubmit={auth.handleSetupSubmit}
              />
            )}
          </div>
        </main>

        <div className="h-5" aria-hidden="true" />
      </div>

      {/* Right Side: Alternating Corner-Connected 1:1 Squares (~30% width) */}
      <aside
        aria-label="Geometric pattern panel"
        className="hidden lg:block lg:w-[30%] h-screen sticky top-0 overflow-hidden"
      >
        <AuthCheckerboardPattern />
      </aside>
    </div>
  )
}
