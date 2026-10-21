import 'package:flutter/material.dart';
import '../main.dart';
import 'signup.dart';
import 'home_shell.dart';

import '../services/auth_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _remember = false;
  bool _obscure = true;

  final AuthService _auth = AuthService();
  bool _isLoading = false;
  bool _isResendingVerification = false;
  bool _requiresEmailVerification = false;
  String? _authMessage;
  String? _verificationMessage;

  @override
  void dispose() {
    _userCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    final email = _userCtrl.text.trim();
    final password = _passCtrl.text;

    if (email.isEmpty || password.isEmpty) {
      setState(() {
        _authMessage = 'Please enter email and password.';
        _requiresEmailVerification = false;
        _verificationMessage = null;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _authMessage = null;
      _requiresEmailVerification = false;
      _verificationMessage = null;
    });

    try {
      final result = await _auth.signInWithEmail(
        email: email,
        password: password,
      );

      if (result.user.role.toLowerCase() != 'user') {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Only user accounts can log in on this app (current role: ${result.user.role})',
            ),
          ),
        );
      } else {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => HomeShell(user: result.user)),
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _authMessage = 'Login failed: $e';
        _requiresEmailVerification =
            e is AuthFlowException && e.requiresEmailVerification;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _resendEmailVerification() async {
    if (_isResendingVerification) return;
    setState(() {
      _isResendingVerification = true;
      _verificationMessage = null;
    });

    try {
      final alreadyVerified = await _auth.resendEmailVerification();
      if (!mounted) return;
      setState(() {
        _verificationMessage = alreadyVerified
            ? 'Your email is verified. Please log in again.'
            : 'Verification email sent. Check your inbox and spam folder.';
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _verificationMessage = 'Could not resend verification email: $error';
      });
    } finally {
      if (mounted) {
        setState(() => _isResendingVerification = false);
      }
    }
  }

  Future<void> _continueAfterEmailVerification() async {
    if (_isLoading) return;
    setState(() {
      _isLoading = true;
      _authMessage = null;
      _verificationMessage = null;
    });

    try {
      final result = await _auth.completePendingEmailSignIn();
      if (!mounted) return;
      if (result.user.role.toLowerCase() != 'user') {
        setState(() {
          _authMessage =
              'Only user accounts can log in on this app (current role: ${result.user.role}).';
          _requiresEmailVerification = false;
        });
        return;
      }
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => HomeShell(user: result.user)),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _authMessage = 'Could not continue: $error';
        _requiresEmailVerification =
            error is AuthFlowException && error.requiresEmailVerification;
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;

    return Scaffold(
      resizeToAvoidBottomInset: true,
      body: GradientBackground(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 28, 24, 32),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: SizedBox(
                width: double.infinity,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Carbon Tracker', style: t.titleLarge),
                    spacer(26),
                    Text('Welcome Back!', style: t.headlineMedium),
                    spacer(6),
                    const Text('Login to continue',
                        style: TextStyle(color: Colors.white70)),
                    spacer(22),
                    const Text('Username',
                        style: TextStyle(color: Colors.white)),
                    spacer(8),
                    TextField(
                      controller: _userCtrl,
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                      decoration: pillInput('Enter your email'),
                    ),
                    spacer(16),
                    const Text('Password',
                        style: TextStyle(color: Colors.white)),
                    spacer(8),
                    TextField(
                      controller: _passCtrl,
                      obscureText: _obscure,
                      textInputAction: TextInputAction.done,
                      onSubmitted: (_) {
                        if (!_isLoading) _handleLogin();
                      },
                      decoration: pillInput('Enter your password').copyWith(
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscure ? Icons.visibility_off : Icons.visibility,
                            color: Colors.white,
                          ),
                          onPressed: () => setState(() => _obscure = !_obscure),
                        ),
                      ),
                    ),
                    spacer(1),
                    Row(
                      children: [
                        Checkbox(
                          value: _remember,
                          onChanged: (v) =>
                              setState(() => _remember = v ?? false),
                          side: const BorderSide(color: Colors.white70),
                          checkColor: Colors.white,
                          activeColor: Colors.white30,
                        ),
                        const Text('remember me'),
                        const Spacer(),
                      ],
                    ),
                    spacer(1),
                    GradientButton(
                      label: _isLoading ? 'Logging in...' : 'Log in',
                      onPressed: () {
                        if (_isLoading) return; // đang loading thì bỏ qua
                        _handleLogin();
                      },
                    ),
                    if (_authMessage != null) ...[
                      spacer(16),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: const Color(0x22FFFFFF),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: const Color(0x55FFFFFF)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(
                                  Icons.info_outline,
                                  color: Colors.white,
                                  size: 20,
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    _authMessage!,
                                    style: const TextStyle(color: Colors.white),
                                  ),
                                ),
                              ],
                            ),
                            if (_requiresEmailVerification) ...[
                              const SizedBox(height: 8),
                              const Text(
                                'Open the verification email, including your spam folder. After verifying, return here and continue below.',
                                style: TextStyle(color: Colors.white70),
                              ),
                              Align(
                                alignment: Alignment.centerLeft,
                                child: TextButton.icon(
                                  onPressed: _isLoading
                                      ? null
                                      : _continueAfterEmailVerification,
                                  icon: _isLoading
                                      ? const SizedBox(
                                          width: 16,
                                          height: 16,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            color: Colors.white,
                                          ),
                                        )
                                      : const Icon(
                                          Icons.verified_outlined,
                                          color: Colors.white,
                                        ),
                                  label: Text(
                                    _isLoading
                                        ? 'Checking verification...'
                                        : "I've verified — continue",
                                    style: const TextStyle(color: Colors.white),
                                  ),
                                ),
                              ),
                              Align(
                                alignment: Alignment.centerLeft,
                                child: TextButton.icon(
                                  onPressed:
                                      _isResendingVerification || _isLoading
                                          ? null
                                          : _resendEmailVerification,
                                  icon: _isResendingVerification
                                      ? const SizedBox(
                                          width: 16,
                                          height: 16,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            color: Colors.white,
                                          ),
                                        )
                                      : const Icon(
                                          Icons.mark_email_read_outlined,
                                          color: Colors.white,
                                        ),
                                  label: Text(
                                    _isResendingVerification
                                        ? 'Sending...'
                                        : 'Resend verification email',
                                    style: const TextStyle(color: Colors.white),
                                  ),
                                ),
                              ),
                            ],
                            if (_verificationMessage != null) ...[
                              const SizedBox(height: 4),
                              Text(
                                _verificationMessage!,
                                style: const TextStyle(color: Colors.white),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                    spacer(12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text("Don't have an account? ",
                            style: TextStyle(color: Colors.white70)),
                        GestureDetector(
                          onTap: () => Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (_) => const SignupScreen()),
                          ),
                          child: const Text(
                            'Sign Up',
                            style: TextStyle(
                              color: Color(0xFF85E489),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
