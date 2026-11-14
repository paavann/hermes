import { createContext, useContext, type ReactNode } from 'react'

export interface ChatConfig {
  baseUrl: string
  apiVer: string
}

interface ChatConfigProviderProps {
  config: ChatConfig
  children: ReactNode
}



const ChatConfigContext = createContext<ChatConfig | null>(null)

export function ChatConfigProvider({
  config, children,
}: ChatConfigProviderProps): React.JSX.Element {
  return (
    <ChatConfigContext.Provider value={config}>
      {children}
    </ChatConfigContext.Provider>
  )
}

export function useChatConfig(): ChatConfig {
  const config = useContext(ChatConfigContext)
  if (!config) {
    throw new Error('useChatConfig must be used within a ChatConfigProvider')
  }
  return config
}
