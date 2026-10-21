import React from 'react'
import { clerkMiddleware, rootAuthLoader } from '@clerk/react-router/server' 
import { ClerkProvider } from '@clerk/react-router'
import type { MetaFunction, LinksFunction, MiddlewareFunction, LoaderFunctionArgs } from 'react-router'
import { Links, Meta, Outlet, Scripts, ScrollRestoration, isRouteErrorResponse } from 'react-router'
import stylesheetUrl from '../styles.css?url'


interface RootErrorBoundaryProps {
  error: unknown
}

interface AppProps {
  loaderData?: Awaited<ReturnType<typeof loader>>
}


export const middleware: MiddlewareFunction<Response>[] = [clerkMiddleware()]
export const loader = (args: LoaderFunctionArgs) => rootAuthLoader(args)

export const meta: MetaFunction = () => [
  { title: 'Hermes — Geospatial Intelligence' },
]

export const links: LinksFunction = () => [
  { rel: 'icon', href: 'data:,' },
  { rel: 'stylesheet', href: stylesheetUrl },
  { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
  { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossOrigin: 'anonymous' },
  { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,400..800;1,400..800&display=swap' },
]



export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  )
}

export default function App({ loaderData }: AppProps) {
  return (
    <ClerkProvider
      loaderData={loaderData}
      publishableKey={import.meta.env.VITE_CLERK_PUBLISHABLE_KEY}
    >
      <Outlet />
    </ClerkProvider>
  )
}



export function ErrorBoundary({error}: RootErrorBoundaryProps): React.JSX.Element {
  let message = "Oops!"
  let details = "An unexpected error occurred."
  let stack: string | undefined

  if (isRouteErrorResponse(error)) {
    message = error.status === 404 ? '404' : 'Error'
    details = error.status === 404 ? 'The requested page could not be found.' : error.statusText || details
  } else if (import.meta.env.DEV && error && error instanceof Error) {
    details = error.message
    stack = error.stack
  }

  return (
    <main className="pt-16 p-4 container mx-auto">
      <h1>{message}</h1>
      <p>{details}</p>
      {stack && (
        <pre className="w-full p-4 overflow-x-auto">
          <code>{stack}</code>
        </pre>
      )}
    </main>
  )
}
