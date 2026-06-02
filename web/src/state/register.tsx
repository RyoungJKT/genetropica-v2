import { createContext, useContext, useState, type ReactNode } from 'react'

type Register = 'plain' | 'sci'

const Ctx = createContext<{ reg: Register; setReg: (r: Register) => void }>({
  reg: 'plain',
  setReg: () => {},
})

export function RegisterProvider({ children }: { children: ReactNode }) {
  const [reg, setReg] = useState<Register>('plain')
  return <Ctx.Provider value={{ reg, setReg }}>{children}</Ctx.Provider>
}

export const useRegister = () => useContext(Ctx)

/** pick plain-English vs scientific copy for the current register */
export const say = (reg: Register, plain: string, sci: string) => (reg === 'plain' ? plain : sci)
