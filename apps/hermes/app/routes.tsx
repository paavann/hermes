import { index, route, type RouteConfig } from '@react-router/dev/routes'

export default [
  index('./routes/landing.tsx'),
  route('map', './routes/map.tsx'),
  route('about', './routes/about.tsx'),
  route('auth/*', './routes/auth.tsx'),
] satisfies RouteConfig
