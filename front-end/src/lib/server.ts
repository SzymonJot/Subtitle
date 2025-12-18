import { createBrowserClient } from '@supabase/ssr'

export function createClient(request: Request) {
  // In SPA mode, we use createBrowserClient which handles cookies on the document automatically.
  // We ignore the request object and the manual header management intended for SSR.
  const supabase = createBrowserClient(
    import.meta.env.VITE_SUPABASE_URL!,
    import.meta.env.VITE_SUPABASE_PUBLISHABLE_OR_ANON_KEY!
  )

  // Return empty headers to satisfy the interface expected by the generated routes
  return { supabase, headers: new Headers() }
}
