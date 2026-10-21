import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import {
  ArrowDownRight,
  ArrowUpRight,
  Bike,
  BusFront,
  CarFront,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Coins,
  Compass,
  Gift,
  Leaf,
  LoaderCircle,
  LogOut,
  Menu,
  Plus,
  Recycle,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Footprints,
  Wallet,
  X,
} from 'lucide-react'
import {
  completeEmailSignIn,
  createEmailAccount,
  requestPasswordReset,
  resendVerificationEmail,
  signInWithEmail,
  type PendingSignIn,
  type WebUser,
} from './auth'
import {
  api,
  type HomeSummary,
  type Trip,
  type TripStats,
  type Voucher,
  type WalletSummary,
} from './data'
import './App.css'

type Page = 'Overview' | 'Trips' | 'Wallet' | 'Rewards' | 'Settings'
type Session = { apiToken: string; user: WebUser }

const navigation: { name: Page; icon: typeof Compass }[] = [
  { name: 'Overview', icon: Compass },
  { name: 'Trips', icon: BusFront },
  { name: 'Wallet', icon: Wallet },
  { name: 'Rewards', icon: Gift },
  { name: 'Settings', icon: Settings },
]

const transportModes = [
  'Walking',
  'Bicycle',
  'E-Bus',
  'Bus',
  'E-Motorbike',
  'Motorbike',
  'Car',
  'E-Car',
]

function messageFor(error: unknown) {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}

function App() {
  const [currentDate] = useState(() => new Date())
  const [session, setSession] = useState<Session | null>(() => {
    const saved = sessionStorage.getItem('carbon-web-session')
    if (!saved) return null
    try {
      return JSON.parse(saved) as Session
    } catch {
      sessionStorage.removeItem('carbon-web-session')
      return null
    }
  })
  const [page, setPage] = useState<Page>('Overview')
  const [pendingSignIn, setPendingSignIn] = useState<PendingSignIn | null>(null)
  const [authMessage, setAuthMessage] = useState('')
  const [authBusy, setAuthBusy] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login')
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [pageError, setPageError] = useState('')
  const [home, setHome] = useState<HomeSummary | null>(null)
  const [stats, setStats] = useState<TripStats | null>(null)
  const [wallet, setWallet] = useState<WalletSummary | null>(null)
  const [trips, setTrips] = useState<Trip[]>([])
  const [vouchers, setVouchers] = useState<Voucher[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [tripDialogOpen, setTripDialogOpen] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')

  const loadData = useCallback(async () => {
    if (!session) return
    setLoading(true)
    setPageError('')
    try {
      const [homeData, tripData, tripStats, walletData, voucherData] =
        await Promise.all([
          api.get<HomeSummary>(`/homepage/summary?user_id=${session.user.id}`),
          api.get<Trip[]>(`/trips?user_id=${session.user.id}`),
          api.get<TripStats>(`/trips/stats?user_id=${session.user.id}`),
          api.get<WalletSummary>(`/wallet/summary?user_id=${session.user.id}`),
          api.get<Voucher[]>('/vouchers'),
        ])
      setHome(homeData)
      setTrips(tripData)
      setStats(tripStats)
      setWallet(walletData)
      setVouchers(voucherData)
    } catch (error) {
      setPageError(messageFor(error))
    } finally {
      setLoading(false)
    }
  }, [session])

  useEffect(() => {
    const timer = window.setTimeout(() => void loadData(), 0)
    return () => window.clearTimeout(timer)
  }, [loadData])

  const signIn = async (email: string, password: string) => {
    setAuthBusy(true)
    setAuthMessage('')
    try {
      const pending = await signInWithEmail(email, password)
      setPendingSignIn(pending)
      if (!pending.emailVerified) {
        setAuthMessage('Your email is not verified yet. Open the verification email, then return and choose “I verified my email”.')
        return
      }
      await finishSignIn(pending)
    } catch (error) {
      setAuthMessage(messageFor(error))
    } finally {
      setAuthBusy(false)
    }
  }

  const finishSignIn = async (pending: PendingSignIn) => {
    setAuthBusy(true)
    setAuthMessage('')
    try {
      const result = await completeEmailSignIn(pending)
      const nextSession = { apiToken: result.access_token, user: result.user }
      sessionStorage.setItem('carbon-web-session', JSON.stringify(nextSession))
      setSession(nextSession)
      setPendingSignIn(null)
    } catch (error) {
      setAuthMessage(messageFor(error))
    } finally {
      setAuthBusy(false)
    }
  }

  const resendVerification = async () => {
    if (!pendingSignIn) return
    setAuthBusy(true)
    try {
      await resendVerificationEmail(pendingSignIn.idToken)
      setAuthMessage('Verification email sent. Check your inbox and spam folder.')
    } catch (error) {
      setAuthMessage(messageFor(error))
    } finally {
      setAuthBusy(false)
    }
  }

  const resetPassword = async (email: string) => {
    setAuthBusy(true)
    setAuthMessage('')
    try {
      await requestPasswordReset(email)
      setAuthMessage('If a Firebase account exists for this email, password reset instructions have been sent. Check your inbox and spam folder.')
    } catch (error) {
      setAuthMessage(messageFor(error))
    } finally {
      setAuthBusy(false)
    }
  }

  const register = async (name: string, email: string, password: string) => {
    setAuthBusy(true)
    setAuthMessage('')
    try {
      const pending = await createEmailAccount(name, email, password)
      setPendingSignIn(pending)
      setAuthMode('login')
      setAuthMessage('Account created. We sent a verification link to your email. Verify it, then choose “I verified my email”.')
    } catch (error) {
      setAuthMessage(messageFor(error))
    } finally {
      setAuthBusy(false)
    }
  }

  const signOut = () => {
    sessionStorage.removeItem('carbon-web-session')
    setSession(null)
    setHome(null)
    setTrips([])
    setWallet(null)
  }

  const redeemVoucher = async (voucher: Voucher) => {
    if (!session) return
    setSuccessMessage('')
    try {
      await api.post(`/vouchers/${voucher.id}/redeem`, { user_id: session.user.id })
      setSuccessMessage(`${voucher.title} redeemed successfully.`)
      await loadData()
    } catch (error) {
      setPageError(messageFor(error))
    }
  }

  const createTrip = async (distance: number, mode: string) => {
    if (!session) return
    const today = new Date()
    const date = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
    await api.post('/trips', {
      user_id: session.user.id,
      date,
      distance_km: distance,
      transport_modes: [mode],
    })
    setTripDialogOpen(false)
    setSuccessMessage('Trip saved. Your dashboard has been updated.')
    await loadData()
  }

  if (!session) {
    return (
      <AuthScreen
        mode={authMode}
        busy={authBusy}
        message={authMessage}
        pending={pendingSignIn}
        onModeChange={setAuthMode}
        onSignIn={(email, password) => void signIn(email, password)}
        onSignUp={(name, email, password) => void register(name, email, password)}
        onPasswordReset={(email) => void resetPassword(email)}
        onResend={() => void resendVerification()}
        onContinue={() => pendingSignIn && void finishSignIn(pendingSignIn)}
      />
    )
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNavOpen ? 'sidebar-open' : ''}`}>
        <a className="brand" href="#" onClick={(event) => { event.preventDefault(); setPage('Overview') }}>
          <span className="brand-mark"><Leaf size={21} fill="currentColor" /></span>
          <span>carbon<span className="brand-light">track</span></span>
        </a>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="main-nav" aria-label="Main navigation">
          {navigation.map(({ name, icon: Icon }) => (
            <button
              className={`nav-item ${page === name ? 'active' : ''}`}
              key={name}
              onClick={() => { setPage(name); setMobileNavOpen(false); setSuccessMessage(''); setPageError('') }}
            >
              <Icon size={19} strokeWidth={1.8} />
              <span>{name}</span>
              {name === 'Rewards' && <span className="nav-count">{vouchers.length}</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="eco-tip">
            <span className="tip-icon"><Sparkles size={17} /></span>
            <strong>Small steps matter</strong>
            <p>Every greener trip makes a difference.</p>
          </div>
          <button className="profile-button" onClick={() => setPage('Settings')}>
            <span className="avatar">{initials(session.user.full_name)}</span>
            <span className="profile-copy"><strong>{session.user.full_name}</strong><small>{session.user.email}</small></span>
            <ChevronDown size={16} />
          </button>
        </div>
      </aside>

      {mobileNavOpen && <button className="nav-backdrop" aria-label="Close menu" onClick={() => setMobileNavOpen(false)} />}

      <main className="main-area">
        <header className="topbar">
          <button className="mobile-menu icon-button" aria-label="Open menu" onClick={() => setMobileNavOpen(true)}><Menu size={20} /></button>
          <div className="breadcrumb"><span>Workspace</span><span className="crumb-slash">/</span><strong>{page}</strong></div>
          <div className="top-actions">
            <div className="api-status"><span className="status-dot" /> Data connected</div>
            <button className="icon-button" aria-label="Help"><CircleHelp size={19} /></button>
            <button className="avatar small-avatar" title={session.user.full_name} onClick={() => setPage('Settings')}>{initials(session.user.full_name)}</button>
          </div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">{dateLabel(currentDate)}</div>
              <h1>{page === 'Overview' ? `Good day, ${firstName(session.user.full_name)}` : page}</h1>
              <p className="page-subtitle">{headingSubtitle(page)}</p>
            </div>
            {page === 'Trips' && <button className="primary-button" onClick={() => setTripDialogOpen(true)}><Plus size={18} /> Log a trip</button>}
            {page === 'Overview' && <button className="secondary-button" onClick={() => void loadData()} disabled={loading}><Recycle size={17} className={loading ? 'spin' : ''} /> Refresh data</button>}
          </div>

          {pageError && <div className="notice error-notice"><strong>Could not load data.</strong> {pageError} <button onClick={() => void loadData()}>Try again</button></div>}
          {successMessage && <div className="notice success-notice"><Check size={17} /> {successMessage}<button aria-label="Dismiss" onClick={() => setSuccessMessage('')}><X size={16} /></button></div>}
          {loading && !home && <div className="loading-state"><LoaderCircle className="spin" size={28} /><span>Loading your account data…</span></div>}

          {page === 'Overview' && <Overview home={home} stats={stats} trips={trips} wallet={wallet} today={currentDate} onTrips={() => setPage('Trips')} />}
          {page === 'Trips' && <TripsPage trips={trips} search={searchTerm} onSearch={setSearchTerm} />}
          {page === 'Wallet' && <WalletPage wallet={wallet} />}
          {page === 'Rewards' && <RewardsPage vouchers={vouchers} balance={wallet?.balance_credits ?? 0} onRedeem={(voucher) => void redeemVoucher(voucher)} />}
          {page === 'Settings' && <SettingsPage user={session.user} onSignOut={signOut} />}
        </div>
      </main>

      {tripDialogOpen && <TripDialog busy={loading} onClose={() => setTripDialogOpen(false)} onSave={(distance, mode) => void createTrip(distance, mode).catch((error: unknown) => setPageError(messageFor(error)))} />}
    </div>
  )
}

function AuthScreen(props: {
  mode: 'login' | 'signup'
  busy: boolean
  message: string
  pending: PendingSignIn | null
  onModeChange: (mode: 'login' | 'signup') => void
  onSignIn: (email: string, password: string) => void
  onSignUp: (name: string, email: string, password: string) => void
  onPasswordReset: (email: string) => void
  onResend: () => void
  onContinue: () => void
}) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const signup = props.mode === 'signup'
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (signup) props.onSignUp(name.trim(), email.trim(), password)
    else props.onSignIn(email.trim(), password)
  }

  return (
    <div className="auth-layout">
      <section className="auth-visual">
        <a className="brand auth-brand" href="#"><span className="brand-mark"><Leaf size={21} fill="currentColor" /></span><span>carbon<span className="brand-light">track</span></span></a>
        <div className="auth-visual-copy">
          <span className="pill-light"><Sparkles size={14} /> YOUR IMPACT, IN FOCUS</span>
          <h1>Make every<br />journey count.</h1>
          <p>Track your trips, celebrate the carbon you save, and turn small choices into lasting change.</p>
          <div className="auth-art" aria-hidden="true">
            <div className="orbit orbit-one" /><div className="orbit orbit-two" />
            <div className="earth"><Leaf size={76} fill="currentColor" strokeWidth={1.2} /></div>
            <span className="float-leaf leaf-one"><Leaf size={22} /></span><span className="float-leaf leaf-two"><Leaf size={17} /></span>
            <span className="art-stat"><strong>−2.4 kg</strong><small>CO₂ saved today</small></span>
          </div>
        </div>
        <div className="visual-foot"><span>BETTER MOVES. BRIGHTER FUTURE.</span><span>01 / 02</span></div>
      </section>
      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-mobile-brand"><span className="brand-mark"><Leaf size={20} fill="currentColor" /></span><span>carbon<span className="brand-light">track</span></span></div>
          <span className="eyebrow">{signup ? 'GET STARTED' : 'WELCOME BACK'}</span>
          <h2>{signup ? 'Create your account' : 'Sign in to your account'}</h2>
          <p className="auth-caption">{signup ? 'Start building a greener journey today.' : 'Your sustainability journey is waiting.'}</p>
          <form onSubmit={submit} className="auth-form">
            {signup && <label>Full name<input autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" required /></label>}
            <label>Email address<input autoComplete="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" required /></label>
            <label>Password
              <span className="password-field"><input autoComplete={signup ? 'new-password' : 'current-password'} type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={signup ? 'At least 6 characters' : 'Enter your password'} minLength={6} required /><button type="button" onClick={() => setShowPassword(!showPassword)}>{showPassword ? 'Hide' : 'Show'}</button></span>
            </label>
            {!signup && <button className="forgot-password" type="button" disabled={props.busy || !email.trim()} onClick={() => props.onPasswordReset(email.trim())}>Forgot password?</button>}
            {!signup && <div className="form-meta"><span>Use your mobile app account</span><ShieldCheck size={15} /></div>}
            <button className="primary-button auth-submit" disabled={props.busy}>{props.busy ? <><LoaderCircle className="spin" size={18} /> Please wait…</> : signup ? 'Create account' : 'Sign in'}<ArrowUpRight size={17} /></button>
          </form>
          {props.message && <div className={`auth-notice ${props.pending && !props.pending.emailVerified ? 'verify-notice' : ''}`} role="status">
            <span>{props.message}</span>
            {props.pending && !props.pending.emailVerified && <div className="verify-actions"><button onClick={props.onContinue} disabled={props.busy}>{props.busy ? 'Checking…' : 'I verified my email'}</button><button onClick={props.onResend} disabled={props.busy}>Resend verification email</button></div>}
          </div>}
          <div className="auth-switch">{signup ? 'Already have an account?' : "Don't have an account?"} <button onClick={() => { props.onModeChange(signup ? 'login' : 'signup'); }}>{signup ? 'Sign in' : 'Create account'}</button></div>
          <div className="auth-security"><ShieldCheck size={16} /> Secure sign-in with Firebase Authentication</div>
        </div>
      </section>
    </div>
  )
}

function Overview({ home, stats, trips, wallet, today, onTrips }: { home: HomeSummary | null; stats: TripStats | null; trips: Trip[]; wallet: WalletSummary | null; today: Date; onTrips: () => void }) {
  const recentTrips = trips.slice(0, 5)
  const maxCredits = Math.max(1, ...(stats?.weekly ?? []).map((point) => point.credits))
  return (
    <>
      <section className="hero-card">
        <div className="hero-copy"><span className="hero-kicker"><Leaf size={15} /> YOUR MONTHLY IMPACT</span><h2>Every greener mile<br />adds up to something.</h2><p>Your daily choices are building a lighter footprint.</p><button className="hero-button" onClick={onTrips}>Explore your trips <ArrowUpRight size={16} /></button></div>
        <div className="hero-illustration" aria-hidden="true"><span className="hero-sun" /><span className="hero-hill hill-back" /><span className="hero-hill hill-front" /><span className="hero-tree tree-a" /><span className="hero-tree tree-b" /><span className="hero-path" /><span className="hero-badge"><Leaf size={16} /> Positive impact</span></div>
      </section>
      <div className="metrics-grid">
        <MetricCard icon={<Leaf size={19} />} label="CO₂ SAVED" value={`${(home?.co2_saved_kg ?? 0).toFixed(2)} kg`} detail="This month" accent="green" />
        <MetricCard icon={<Compass size={19} />} label="DISTANCE" value={`${(home?.distance_km ?? 0).toFixed(2)} km`} detail="This month" accent="blue" />
        <MetricCard icon={<Coins size={19} />} label="CREDIT BALANCE" value={String(wallet?.balance_credits ?? 0)} detail={`+${wallet?.credits_this_week ?? 0} this week`} accent="gold" />
        <MetricCard icon={<BusFront size={19} />} label="TRIPS LOGGED" value={String(stats?.total_trips ?? trips.length)} detail={`${stats?.total_distance_km?.toFixed(2) ?? '0.00'} km in total`} accent="purple" />
      </div>
      <div className="dashboard-grid">
        <section className="panel chart-panel">
          <div className="panel-heading"><div><h3>Your weekly rhythm</h3><p>Credits earned throughout the week</p></div><span className="panel-badge">THIS WEEK <ChevronDown size={14} /></span></div>
          <div className="chart-legend"><span><i /> Credits</span><strong>{stats?.daily.reduce((sum, point) => sum + point.credits, 0) ?? 0} credits</strong></div>
          <div className="bar-chart">{(stats?.daily ?? []).map((point, index) => <div className="bar-column" key={`${point.label}-${index}`}><span className="bar-value">{point.credits || ''}</span><div className="bar-track"><div className={`bar-fill ${index === (today.getDay() + 6) % 7 ? 'today' : ''}`} style={{ height: `${Math.max(point.credits ? 10 : 3, (point.credits / maxCredits) * 100)}%` }} /></div><span className="bar-label">{point.label.slice(0, 3)}</span></div>)}</div>
        </section>
        <section className="panel impact-panel">
          <div className="panel-heading"><div><h3>Your impact</h3><p>A little progress goes a long way</p></div><span className="impact-icon"><Leaf size={19} /></span></div>
          <div className="impact-total">{(home?.co2_saved_kg ?? 0).toFixed(2)} <small>kg CO₂</small></div>
          <p className="impact-description">saved this month by choosing lower-carbon ways to get around.</p>
          <div className="impact-progress"><span style={{ width: `${Math.min(100, (home?.co2_saved_kg ?? 0) * 10)}%` }} /></div><div className="impact-goal"><span>Monthly goal</span><strong>10 kg</strong></div>
          <div className="impact-note"><Sparkles size={16} /><span>Keep going — every trip makes a difference.</span></div>
        </section>
      </div>
      <section className="panel recent-panel">
        <div className="panel-heading"><div><h3>Recent trips</h3><p>Your latest journeys and their impact</p></div><button className="text-button" onClick={onTrips}>View all <ArrowUpRight size={15} /></button></div>
        <TripTable trips={recentTrips} compact />
      </section>
    </>
  )
}

function MetricCard({ icon, label, value, detail, accent }: { icon: ReactNode; label: string; value: string; detail: string; accent: string }) {
  return <article className="metric-card"><span className={`metric-icon ${accent}`}>{icon}</span><span className="metric-label">{label}</span><strong className="metric-value">{value}</strong><span className="metric-detail">{detail}</span><span className="metric-spark"><ArrowUpRight size={15} /></span></article>
}

function TripsPage({ trips, search, onSearch }: { trips: Trip[]; search: string; onSearch: (value: string) => void }) {
  const filtered = useMemo(() => trips.filter((trip) => trip.transport_modes.join(' ').toLowerCase().includes(search.toLowerCase()) || trip.date.toLowerCase().includes(search.toLowerCase())), [trips, search])
  return <section className="panel table-panel"><div className="table-toolbar"><div><h3>Trip history</h3><p>{trips.length} journeys recorded</p></div><label className="search-box"><Search size={16} /><input value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Search trips..." /></label></div><TripTable trips={filtered} /></section>
}

function TripTable({ trips, compact = false }: { trips: Trip[]; compact?: boolean }) {
  if (!trips.length) return <div className="empty-state"><Compass size={25} /><strong>No trips yet</strong><span>Trips saved in the mobile app will appear here.</span></div>
  return <div className="table-scroll"><table><thead><tr><th>JOURNEY</th><th>DATE</th><th>DISTANCE</th><th>MODE</th><th>CREDITS</th>{!compact && <th>STATUS</th>}</tr></thead><tbody>{trips.map((trip) => <tr key={trip.id}><td><span className="journey-cell"><span className="journey-icon"><RouteIcon modes={trip.transport_modes} /></span><span><strong>Trip #{trip.id}</strong><small>Carbon Tracker journey</small></span></span></td><td>{formatDate(trip.date)}</td><td><strong>{trip.distance_km.toFixed(2)} km</strong></td><td><span className="mode-pill">{trip.transport_modes.join(', ') || '—'}</span></td><td><strong className="credit-positive">+{trip.credits}</strong></td>{!compact && <td><span className="status-pill"><i /> Completed</span></td>}</tr>)}</tbody></table></div>
}

function RouteIcon({ modes }: { modes: string[] }) {
  const mode = modes[0]
  if (mode === 'Walking') return <Footprints size={17} />
  if (mode === 'Bicycle') return <Bike size={17} />
  if (mode?.includes('Car')) return <CarFront size={17} />
  return <BusFront size={17} />
}

function WalletPage({ wallet }: { wallet: WalletSummary | null }) {
  return <><div className="wallet-summary"><div className="wallet-balance"><span className="wallet-medallion"><Coins size={24} /></span><span><small>AVAILABLE BALANCE</small><strong>{wallet?.balance_credits ?? 0} <em>credits</em></strong></span><span className="wallet-leaf"><Leaf size={74} /></span></div><div className="wallet-mini"><span className="mini-icon"><ArrowUpRight size={18} /></span><small>THIS WEEK</small><strong>{wallet?.credits_this_week ?? 0}</strong><span>Credits earned</span></div><div className="wallet-mini"><span className="mini-icon blue-mini"><Clock3 size={18} /></span><small>THIS MONTH</small><strong>{wallet?.credits_this_month ?? 0}</strong><span>Credits earned</span></div></div><section className="panel table-panel"><div className="panel-heading"><div><h3>Transaction history</h3><p>Credits earned and redeemed</p></div><span className="panel-badge">ALL ACTIVITY <ChevronDown size={14} /></span></div><div className="transaction-list">{wallet?.history.map((entry, index) => <div className="transaction" key={`${entry.date}-${index}`}><span className={`transaction-icon ${entry.amount < 0 ? 'spent' : ''}`}>{entry.amount < 0 ? <ArrowDownRight size={18} /> : <ArrowUpRight size={18} />}</span><span className="transaction-copy"><strong>{entry.title}</strong><small>{formatDateTime(entry.date)}</small></span><strong className={entry.amount < 0 ? 'credit-negative' : 'credit-positive'}>{entry.amount > 0 ? '+' : ''}{entry.amount}</strong></div>)}{!wallet?.history.length && <div className="empty-state"><Wallet size={25} /><strong>No wallet activity yet</strong><span>Your credits will show here.</span></div>}</div></section></>
}

function RewardsPage({ vouchers, balance, onRedeem }: { vouchers: Voucher[]; balance: number; onRedeem: (voucher: Voucher) => void }) {
  return <><div className="reward-banner"><span className="reward-icon"><Gift size={24} /></span><span><strong>Your credits unlock good things.</strong><small>You have {balance} credits ready to use.</small></span><Sparkles size={25} /></div><div className="voucher-grid">{vouchers.map((voucher, index) => { const available = voucher.status !== 'redeemed' && voucher.status !== 'expired'; return <article className="voucher-card" key={voucher.id}><div className={`voucher-art voucher-art-${index % 4}`}><span className="voucher-tag">{voucher.category || 'GREEN REWARD'}</span><Gift size={36} /></div><div className="voucher-copy"><div className="voucher-rating">★ {voucher.rating.toFixed(1)} <span>· {voucher.availability}</span></div><h3>{voucher.title}</h3><p>{voucher.description}</p><div className="voucher-footer"><strong><Coins size={16} /> {voucher.credits} credits</strong><button className="redeem-button" disabled={!available || balance < voucher.credits} onClick={() => onRedeem(voucher)}>{available ? balance < voucher.credits ? 'Not enough' : 'Redeem' : voucher.status}</button></div></div></article> })}{!vouchers.length && <div className="empty-state"><Gift size={25} /><strong>No rewards available</strong><span>Check back later for new vouchers.</span></div>}</div></>
}

function SettingsPage({ user, onSignOut }: { user: WebUser; onSignOut: () => void }) {
  return <section className="panel settings-panel"><div className="settings-profile"><span className="avatar profile-avatar">{initials(user.full_name)}</span><span><strong>{user.full_name}</strong><small>{user.role} account</small></span></div><div className="settings-divider" /><div className="settings-row"><span><strong>Full name</strong><small>Your display name in Carbon Tracker</small></span><strong>{user.full_name}</strong></div><div className="settings-row"><span><strong>Email address</strong><small>Verified Firebase account</small></span><strong>{user.email}</strong></div><div className="settings-row"><span><strong>Data connection</strong><small>Mobile and web share the same API account</small></span><span className="status-pill"><i /> Connected</span></div><button className="signout-button" onClick={onSignOut}><LogOut size={17} /> Sign out</button></section>
}

function TripDialog({ busy, onClose, onSave }: { busy: boolean; onClose: () => void; onSave: (distance: number, mode: string) => void }) {
  const [distance, setDistance] = useState('')
  const [mode, setMode] = useState('Walking')
  const [error, setError] = useState('')
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><form className="trip-modal" onSubmit={(event) => { event.preventDefault(); const parsed = Number(distance); if (!Number.isFinite(parsed) || parsed <= 0) { setError('Enter a distance greater than zero.'); return } onSave(parsed, mode) }}><div className="modal-heading"><span className="metric-icon green"><Plus size={19} /></span><button type="button" className="icon-button" onClick={onClose}><X size={19} /></button></div><h2>Log a trip</h2><p>Save a journey to the same account used by your mobile app.</p><label>Distance in kilometers<input type="number" min="0.01" step="0.01" value={distance} onChange={(event) => setDistance(event.target.value)} placeholder="e.g. 2.5" required /></label><label>Transport mode<select value={mode} onChange={(event) => setMode(event.target.value)}>{transportModes.map((option) => <option key={option}>{option}</option>)}</select></label>{error && <div className="field-error">{error}</div>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <Check size={17} />} Save trip</button></div></form></div>
}

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'CT'
}
function firstName(name: string) { return name.trim().split(/\s+/)[0] || 'there' }
function dateLabel(date: Date) { return new Intl.DateTimeFormat('en', { weekday: 'long', month: 'long', day: 'numeric' }).format(date).toUpperCase() }
function formatDate(date: string) { const parsed = new Date(`${date}T00:00:00`); return Number.isNaN(parsed.getTime()) ? date : new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(parsed) }
function formatDateTime(date: string) { const parsed = new Date(date); return Number.isNaN(parsed.getTime()) ? date : new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(parsed) }
function headingSubtitle(page: Page) { return ({ Overview: 'Here’s a snapshot of your greener choices.', Trips: 'A record of the journeys you have taken.', Wallet: 'Your eco-credits and account activity.', Rewards: 'Turn your saved credits into something meaningful.', Settings: 'Your account and connection preferences.' })[page] }

export default App
