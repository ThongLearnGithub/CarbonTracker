import { getApp, getApps, initializeApp } from 'firebase/app'
import { getAuth } from 'firebase/auth'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  appId: '1:222326956435:web:7dc798c52258710249c866',
  authDomain: 'carbon-tracker-622b1.firebaseapp.com',
  messagingSenderId: '222326956435',
  projectId: 'carbon-tracker-622b1',
  storageBucket: 'carbon-tracker-622b1.firebasestorage.app',
}

const firebaseApp = getApps().length ? getApp() : initializeApp(firebaseConfig)

export const firebaseAuth = getAuth(firebaseApp)
