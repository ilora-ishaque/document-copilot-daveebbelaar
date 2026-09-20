interface Env {
  apiBaseUrl: string
  supabaseUrl: string
  supabaseAnonKey: string
}

function readEnvVar(key: keyof ImportMetaEnv): string {
  const value = import.meta.env[key]
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`)
  }
  return value
}

export const env: Env = {
  apiBaseUrl: readEnvVar('VITE_API_BASE_URL'),
  supabaseUrl: readEnvVar('VITE_SUPABASE_URL'),
  supabaseAnonKey: readEnvVar('VITE_SUPABASE_ANON_KEY'),
}
