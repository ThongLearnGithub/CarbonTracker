const firebaseApiKey = import.meta.env.VITE_FIREBASE_API_KEY ?? ''
const identityToolkitUrl = 'https://identitytoolkit.googleapis.com/v1'
const secureTokenUrl = 'https://securetoken.googleapis.com/v1'

export type WebUser = {
  id: number
  email: string
  full_name: string
  role: string
}

export type PendingSignIn = {
  idToken: string
  refreshToken: string
  email: string
  emailVerified: boolean
}

type FirebaseTokenResponse = {
  idToken: string
  refreshToken: string
  localId: string
  email: string
}

type FirebaseErrorResponse = {
  error?: { message?: string }
}

function firebaseUrl(path: string) {
  if (!firebaseApiKey) {
    throw new Error('Firebase is not configured. Set VITE_FIREBASE_API_KEY in .env.local.')
  }
  return `${identityToolkitUrl}/${path}?key=${encodeURIComponent(firebaseApiKey)}`
}

async function firebasePost<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(firebaseUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const result = (await response.json()) as T & FirebaseErrorResponse
  if (!response.ok) throw new Error(firebaseErrorMessage(result.error?.message))
  return result
}

function firebaseErrorMessage(code?: string) {
  switch (code) {
    case 'EMAIL_NOT_FOUND':
    case 'INVALID_LOGIN_CREDENTIALS':
    case 'INVALID_PASSWORD':
      return 'Firebase could not sign in with those details. Check the exact email used in the mobile app or use “Forgot password?”. If this account was created before Firebase sign-in was added, create a Firebase account with the same email to link it to your app data.'
    case 'EMAIL_EXISTS':
      return 'An account already exists for this email. Sign in instead.'
    case 'INVALID_EMAIL':
      return 'Please enter a valid email address.'
    case 'WEAK_PASSWORD':
      return 'Choose a stronger password (at least 6 characters).'
    case 'TOO_MANY_ATTEMPTS_TRY_LATER':
      return 'Firebase temporarily blocked sign-in after too many attempts. Wait before trying again.'
    case 'OPERATION_NOT_ALLOWED':
      return 'Email and password sign-in is disabled in Firebase Authentication settings.'
    case 'API_KEY_INVALID':
    case 'INVALID_API_KEY':
      return 'Firebase API key is invalid. Check VITE_FIREBASE_API_KEY.'
    case 'RESET_PASSWORD_EXCEED_LIMIT':
      return 'Firebase temporarily limited requests. Wait before trying again.'
    case 'USER_DISABLED':
      return 'This account has been disabled. Contact the app administrator.'
    default:
      return code?.replaceAll('_', ' ') ?? 'Firebase authentication failed.'
  }
}

async function lookupEmailVerified(idToken: string) {
  const response = await firebasePost<{ users?: { emailVerified?: boolean }[] }>(
    'accounts:lookup',
    { idToken },
  )
  return response.users?.[0]?.emailVerified === true
}

export async function signInWithEmail(email: string, password: string): Promise<PendingSignIn> {
  const result = await firebasePost<FirebaseTokenResponse>('accounts:signInWithPassword', {
    email,
    password,
    returnSecureToken: true,
  })
  return {
    idToken: result.idToken,
    refreshToken: result.refreshToken,
    email: result.email,
    emailVerified: await lookupEmailVerified(result.idToken),
  }
}

export async function createEmailAccount(
  name: string,
  email: string,
  password: string,
): Promise<PendingSignIn> {
  const result = await firebasePost<FirebaseTokenResponse>('accounts:signUp', {
    email,
    password,
    returnSecureToken: true,
  })

  const token = await firebasePost<FirebaseTokenResponse>('accounts:update', {
    idToken: result.idToken,
    displayName: name,
    returnSecureToken: true,
  })
  await resendVerificationEmail(token.idToken)
  return {
    idToken: token.idToken,
    refreshToken: token.refreshToken,
    email: token.email,
    emailVerified: false,
  }
}

export async function resendVerificationEmail(idToken: string) {
  await firebasePost<{ email: string }>('accounts:sendOobCode', {
    requestType: 'VERIFY_EMAIL',
    idToken,
  })
}

export async function requestPasswordReset(email: string) {
  await firebasePost<{ email: string }>('accounts:sendOobCode', {
    requestType: 'PASSWORD_RESET',
    email,
  })
}

async function refreshPendingSignIn(pending: PendingSignIn): Promise<PendingSignIn> {
  const response = await fetch(
    `${secureTokenUrl}/token?key=${encodeURIComponent(firebaseApiKey)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: pending.refreshToken,
      }),
    },
  )
  const result = (await response.json()) as {
    id_token?: string
    refresh_token?: string
    error?: { message?: string }
  }
  if (!response.ok || !result.id_token || !result.refresh_token) {
    throw new Error(firebaseErrorMessage(result.error?.message))
  }
  return {
    ...pending,
    idToken: result.id_token,
    refreshToken: result.refresh_token,
  }
}

export async function completeEmailSignIn(pending: PendingSignIn) {
  let current = pending
  let verified: boolean
  try {
    verified = await lookupEmailVerified(current.idToken)
  } catch {
    current = await refreshPendingSignIn(current)
    verified = await lookupEmailVerified(current.idToken)
  }
  if (!verified) {
    throw new Error('Firebase still reports this email as unverified. Open the latest verification link, then try again.')
  }

  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000')
    .replace(/\/+$/, '')
  const response = await fetch(`${apiBaseUrl}/auth/firebase`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id_token: current.idToken }),
  })
  const data = (await response.json()) as {
    access_token?: string
    user?: WebUser
    detail?: string
  }
  if (!response.ok || !data.access_token || !data.user) {
    throw new Error(data.detail || 'Could not connect this account to Carbon Tracker.')
  }
  if (data.user.role.toLowerCase() !== 'user') {
    throw new Error(`Only user accounts can access this app (current role: ${data.user.role}).`)
  }
  return { access_token: data.access_token, user: data.user }
}
