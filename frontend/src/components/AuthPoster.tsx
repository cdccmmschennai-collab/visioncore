import { APP_TITLE, COMPANY_NAME, TAGLINE } from '@/config'

/** The decorative right-hand panel shared by Login and Forgot Password. */
export default function AuthPoster() {
  return (
    <div className="login-poster">
      <div className="login-poster-scrim" />
      <div className="login-poster-content">
        <span className="eyebrow login-poster-eyebrow">{COMPANY_NAME}</span>
        <h1 className="login-title">
          {APP_TITLE}
          <span className="login-title-dot">.</span>
        </h1>
        <p className="login-tagline">{TAGLINE}</p>

        <ul className="login-steps">
          <li><span aria-hidden="true">01</span> Photograph the nameplate</li>
          <li><span aria-hidden="true">02</span> AI reads every field</li>
          <li><span aria-hidden="true">03</span> Review, correct, export</li>
        </ul>
      </div>
    </div>
  )
}
