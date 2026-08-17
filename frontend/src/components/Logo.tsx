import logoUrl from '@/assets/cdc logo.jpg'
import { COMPANY_NAME } from '@/config'

interface Props {
  size?: number
  showName?: boolean
  name?: string
}

/** Swap `src/assets/cdc logo.jpg` to change this everywhere. */
export default function Logo({ size = 36, showName = true, name = COMPANY_NAME }: Props) {
  return (
    <span className="logo">
      <img src={logoUrl} style={{ height: size, width: 'auto' }} alt="" aria-hidden="true" />
      {showName && <span className="logo-name">{name}</span>}
    </span>
  )
}
