import {
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
  type MetaFunction, 
  type LinksFunction
} from "react-router";



import stylesheetUrl from "../styles.css?url";

export const meta: MetaFunction = () => ([{
  title: "New Nx React Router App",
}]);

export const links: LinksFunction = () => [
  { rel: "stylesheet", href: stylesheetUrl },
  { rel: "preconnect", href: "https://fonts.googleapis.com" },
  {
    rel: "preconnect",
    href: "https://fonts.gstatic.com",
    crossOrigin: "anonymous",
  },
  {
    rel: "stylesheet",
    href: "https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,400..800;1,400..800&display=swap",
  },
];

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
  );
}

export default function App() {
    return <Outlet />;
}
