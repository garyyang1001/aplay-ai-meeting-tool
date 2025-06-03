/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_OPENROUTER_API_KEY: string
  // 可以在此添加更多環境變數
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}