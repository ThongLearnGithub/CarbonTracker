import {
  createUserWithEmailAndPassword,
  getIdToken,
  reload,
  sendEmailVerification,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signOut,
  updateProfile,
} from 'firebase/auth'
import { firebaseAuth } from './firebase'

const firebaseApiKey = import.meta.env.VITE_FIREBASE_API_KEY ?? ''
const identityToolkitUrl = 'https://identitytoolkit.googleapis.com/v1'

export type WebUser = {
  id: number
  email: string
  full_name: string
  role: string
}

export type PendingSignIn = {
  idToken: string
  email: string
  emailVerified: boolean
  verificationError?: string
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

function firebaseErrorCode(error: unknown) {
  if (typeof error === 'object' && error !== null && 'code' in error) {
    return String(error.code)
  }
  return undefined
}

function firebaseErrorMessage(code?: string) {
  switch (code) {
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
    case 'auth/user-not-found':
    case 'EMAIL_NOT_FOUND':
    case 'INVALID_LOGIN_CREDENTIALS':
    case 'INVALID_PASSWORD':
      return 'Firebase could not sign in with those details. Check the exact email used in the mobile app or use “Forgot password?”. If this account was created before Firebase sign-in was added, create a Firebase account with the same email to link it to your app data.'
    case 'auth/email-already-in-use':
    case 'EMAIL_EXISTS':
      return 'An account already exists for this email. Sign in instead.'
    case 'auth/invalid-email':
    case 'INVALID_EMAIL':
      return 'Please enter a valid email address.'
    case 'auth/weak-password':
    case 'WEAK_PASSWORD':
      return 'Choose a stronger password (at least 6 characters).'
    case 'auth/too-many-requests':
    case 'TOO_MANY_ATTEMPTS_TRY_LATER':
      return 'Firebase temporarily blocked sign-in after too many attempts. Wait before trying again.'
    case 'auth/operation-not-allowed':
    case 'OPERATION_NOT_ALLOWED':
      return 'Email and password sign-in is disabled in Firebase Authentication settings.'
    case 'auth/invalid-api-key':
    case 'API_KEY_INVALID':
    case 'INVALID_API_KEY':
      return 'Firebase API key is invalid. Check VITE_FIREBASE_API_KEY.'
    case 'RESET_PASSWORD_EXCEED_LIMIT':
    case 'auth/quota-exceeded':
      return 'Firebase Authentication has reached a request limit. Try again later or check the Firebase project limits.'
    case 'auth/user-disabled':
    case 'USER_DISABLED':
      return 'This account has been disabled. Contact the app administrator.'
    case 'auth/network-request-failed':
      return 'Could not connect to Firebase. Check your internet connection and try again.'
    case 'auth/invalid-user-token':
    case 'auth/user-token-expired':
    case 'INVALID_ID_TOKEN':
      return 'Your Firebase sign-in session expired. Sign in again, then retry.'
    default:
      return code?.replace(/^auth\//, '').replaceAll('_', ' ') ?? 'Firebase authentication failed.'
  }
}

export async function signInWithEmail(email: string, password: string): Promise<PendingSignIn> {
  try {
    const credential = await signInWithEmailAndPassword(firebaseAuth, email, password)
    await reload(credential.user)
    return {
      idToken: await getIdToken(credential.user, true),
      email: credential.user.email ?? email,
      emailVerified: credential.user.emailVerified,
    }
  } catch (error) {
    throw new Error(firebaseErrorMessage(firebaseErrorCode(error)))
  }
}

export async function createEmailAccount(
  name: string,
  email: string,
  password: string,
): Promise<PendingSignIn> {
  const credential = await createUserWithEmailAndPassword(firebaseAuth, email, password)
    .catch((error: unknown) => {
      throw new Error(firebaseErrorMessage(firebaseErrorCode(error)))
    })
  const user = credential.user

  try {
    await updateProfile(user, { displayName: name })
  } catch (error) {
    await signOut(firebaseAuth)
    throw new Error(`The Firebase account was created, but its profile could not be completed: ${firebaseErrorMessage(firebaseErrorCode(error))}. Sign in with this email and password to continue.`)
  }

  const idToken = await getIdToken(user, true)
  try {
    await sendEmailVerification(user)
  } catch (error) {
    return {
      idToken,
      email: user.email ?? email,
      emailVerified: false,
      verificationError: firebaseErrorMessage(firebaseErrorCode(error)),
    }
  }

  await signOut(firebaseAuth)
  return { idToken, email: user.email ?? email, emailVerified: false }
}

export async function resendVerificationEmail(pending: PendingSignIn): Promise<boolean> {
  const currentUser = firebaseAuth.currentUser
  if (currentUser?.email?.toLowerCase() === pending.email.toLowerCase()) {
    await reload(currentUser)
    if (currentUser.emailVerified) return true
    await sendEmailVerification(currentUser)
    return false
  }

  await firebasePost<{ email: string }>('accounts:sendOobCode', {
    requestType: 'VERIFY_EMAIL',
    idToken: pending.idToken,
  })
  return false
}

export async function requestPasswordReset(email: string) {
  try {
    await sendPasswordResetEmail(firebaseAuth, email)
  } catch (error) {
    throw new Error(firebaseErrorMessage(firebaseErrorCode(error)))
  }
}

export async function completeEmailSignIn(pending: PendingSignIn) {
  const currentUser = firebaseAuth.currentUser
  if (!currentUser || currentUser.email?.toLowerCase() !== pending.email.toLowerCase()) {
    throw new Error('Your Firebase sign-in session expired. Enter your email and password again.')
  }

  await reload(currentUser)
  if (!currentUser.emailVerified) {
    throw new Error('Firebase still reports this email as unverified. Open the latest verification link, then try again.')
  }
  const idToken = await getIdToken(currentUser, true)

  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000')
    .replace(/\/+$/, '')
  const response = await fetch(`${apiBaseUrl}/auth/firebase`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id_token: idToken }),
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

export function signOutFromFirebase() {
  return signOut(firebaseAuth)
}
