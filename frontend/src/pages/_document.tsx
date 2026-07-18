import { Html, Head, Main, NextScript } from 'next/document'

export default function Document() {
  return (
    // Force dark class immediately so Tailwind dark: variants work
    // before JS hydrates, preventing flash of wrong theme on dark OS
    <Html lang="en" className="dark">
      <Head />
      <body>
        {/* Inline script to apply theme BEFORE paint — prevents flash */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                var stored = localStorage.getItem('theme');
                var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                var theme = stored || (prefersDark ? 'dark' : 'light');
                if (theme === 'light') {
                  document.documentElement.classList.remove('dark');
                } else {
                  document.documentElement.classList.add('dark');
                }
              } catch(e) {}
            `,
          }}
        />
        <Main />
        <NextScript />
      </body>
    </Html>
  )
}
