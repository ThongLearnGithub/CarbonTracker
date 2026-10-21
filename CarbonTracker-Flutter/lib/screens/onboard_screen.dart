import 'package:flutter/material.dart';
import '../main.dart';
import '../services/auth_service.dart';
import 'home_shell.dart';
import 'login.dart';
import 'signup.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final AuthService _auth = AuthService();
  bool _isGoogleLoading = false;

  Future<void> _handleGoogleSignIn() async {
    if (_isGoogleLoading) return;
    setState(() => _isGoogleLoading = true);

    try {
      final result = await _auth.signInWithGoogle();
      if (!mounted) return;
      if (result.user.role.toLowerCase() != 'user') {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Only user accounts can log in on this app (current role: ${result.user.role})',
            ),
          ),
        );
        return;
      }
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => HomeShell(user: result.user),
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Google sign-in failed: $error')),
      );
    } finally {
      if (mounted) setState(() => _isGoogleLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: GradientBackground(
        child: SafeArea(
          child: SingleChildScrollView(
            physics: const BouncingScrollPhysics(),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 25, vertical: 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  // Top
                  Align(
                    alignment: Alignment.topLeft,
                    child: Text(
                      'Carbon Tracker',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Mid
                  Column(
                    children: [
                      // Logo
                      SizedBox(
                        width: 250,
                        height: 250,
                        child: DecoratedBox(
                          decoration: const BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: LinearGradient(
                              colors: [Color(0xFF85E489), Color(0xFF0B660F)],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                          ),
                          child: const Icon(
                            Icons.eco,
                            color: Colors.white,
                            size: 140,
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Hello, Welcome!',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Track your journey,\nsave the planet',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 18,
                          height: 1.4,
                        ),
                      ),
                      const SizedBox(height: 26),

                      // Buttons
                      GradientButton(
                        label: 'Log in',
                        onPressed: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const LoginScreen()),
                        ),
                      ),
                      const SizedBox(height: 14),
                      GradientButton(
                        label: 'Sign up',
                        onPressed: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const SignupScreen()),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 30),

                  // Bottom
                  Column(
                    children: [
                      Text(
                        'Or sign in with',
                        style: TextStyle(color: Colors.white70, fontSize: 16),
                      ),
                      SizedBox(height: 10),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          _SocialIcon(
                            label: 'Google',
                            icon: const Icon(
                              Icons.g_mobiledata,
                              color: Colors.white,
                              size: 34,
                            ),
                            onTap: _isGoogleLoading ? null : _handleGoogleSignIn,
                            isLoading: _isGoogleLoading,
                          ),
                          const SizedBox(width: 18),
                          _SocialIcon(
                            label: 'Email',
                            icon: const Icon(
                              Icons.email_outlined,
                              color: Colors.white,
                              size: 26,
                            ),
                            onTap: () => Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => const LoginScreen(),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SocialIcon extends StatelessWidget {
  final String label;
  final Widget icon;
  final VoidCallback? onTap;
  final bool isLoading;

  const _SocialIcon({
    required this.label,
    required this.icon,
    required this.onTap,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: '$label sign in',
      child: Material(
        color: Colors.greenAccent.shade400,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: SizedBox(
            width: 48,
            height: 48,
            child: Center(
              child: isLoading
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : icon,
            ),
          ),
        ),
      ),
    );
  }
}
