import type { ActionFunctionArgs, LoaderFunctionArgs } from 'react-router'

const CLERK_FAPI_HOST = 'https://frontend-api.clerk.dev'

async function handleClerkProxy(request: Request): Promise<Response> {
  const url = new URL(request.url)
  const strippedPath = url.pathname.replace(/^\/__clerk/, '')
  const targetPath = strippedPath.startsWith('/') ? strippedPath : `/${strippedPath}`
  const targetUrl = `${CLERK_FAPI_HOST}${targetPath}${url.search}`

  const proxyUrl =
    process.env.CLERK_PROXY_URL ||
    process.env.VITE_CLERK_PROXY_URL ||
    `${url.origin}/__clerk`

  const secretKey = process.env.CLERK_SECRET_KEY

  const headers = new Headers(request.headers)
  headers.set('Clerk-Proxy-Url', proxyUrl)

  if (secretKey) {
    headers.set('Clerk-Secret-Key', secretKey)
  } else if (process.env.NODE_ENV === 'development') {
    console.warn('[Clerk Proxy] Warning: CLERK_SECRET_KEY is not defined in the environment.')
  }

  const rawClientIp =
    request.headers.get('x-forwarded-for') ||
    request.headers.get('x-real-ip') ||
    ''
  const clientIp = rawClientIp.split(',')[0].trim()
  if (clientIp) {
    headers.set('X-Forwarded-For', clientIp)
  }

  headers.delete('host')
  headers.delete('connection')

  const hasBody = request.method !== 'GET' && request.method !== 'HEAD'
  const body = hasBody ? await request.arrayBuffer() : undefined

  const response = await fetch(targetUrl, {
    method: request.method,
    headers,
    body,
    redirect: 'manual',
  })

  const responseHeaders = new Headers(response.headers)
  if (response.headers.get('content-encoding')) {
    responseHeaders.delete('content-encoding')
    responseHeaders.delete('content-length')
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  })
}

export async function loader({ request }: LoaderFunctionArgs) {
  return handleClerkProxy(request)
}

export async function action({ request }: ActionFunctionArgs) {
  return handleClerkProxy(request)
}
