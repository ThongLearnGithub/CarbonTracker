import 'package:flutter/material.dart';
import '../main.dart';
import '../services/auth_service.dart';

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  bool _ob1 = true, _ob2 = true;
  bool _isLoading = false;

  final _auth = AuthService();

  @override
  void dispose() {
    _nameCtrl.dispose();
    _emailCtrl.dispose();
    _passCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  Future<void> _onSignup() async {
    final name = _nameCtrl.text.trim();
    final email = _emailCtrl.text.trim();
    final pass = _passCtrl.text;
    final confirm = _confirmCtrl.text;

    if (name.isEmpty || email.isEmpty || pass.isEmpty || confirm.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all fields')),
      );
      return;
    }

    if (!email.contains('@')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid email')),
      );
      return;
    }

    if (pass.length < 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Password must be at least 6 characters')),
      );
      return;
    }

    if (pass != confirm) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Passwords do not match')),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      await _auth.signUpWithEmail(
        name: name,
        email: email,
        password: pass,
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Account created. Verify your email, then log in to continue.',
          ),
        ),
      );

      Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Sign up failed: $e')),
      );
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
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
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Carbon Tracker', style: t.titleLarge),
              spacer(26),
              Text('Create Account Now!', style: t.headlineMedium),
              spacer(18),
              const Text('Full Name', style: TextStyle(color: Colors.white)),
              spacer(8),
              TextField(
                controller: _nameCtrl,
                textInputAction: TextInputAction.next,
                decoration: pillInput('Your name'),
              ),
              spacer(14),
              const Text('Email', style: TextStyle(color: Colors.white)),
              spacer(8),
              TextField(
                controller: _emailCtrl,
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.next,
                decoration: pillInput('name@gmail.com'),
              ),
              spacer(14),
              const Text('Password', style: TextStyle(color: Colors.white)),
              spacer(8),
              TextField(
                controller: _passCtrl,
                obscureText: _ob1,
                textInputAction: TextInputAction.next,
                decoration: pillInput('Enter password').copyWith(
                  suffixIcon: IconButton(
                    icon: Icon(
                      _ob1 ? Icons.visibility_off : Icons.visibility,
                      color: Colors.white,
                    ),
                    onPressed: () => setState(() => _ob1 = !_ob1),
                  ),
                ),
              ),
              spacer(14),
              const Text('Confirm Password', style: TextStyle(color: Colors.white)),
              spacer(8),
              TextField(
                controller: _confirmCtrl,
                obscureText: _ob2,
                textInputAction: TextInputAction.done,
                onSubmitted: (_) {
                  if (!_isLoading) _onSignup();
                },
                decoration: pillInput('Re-enter password').copyWith(
                  suffixIcon: IconButton(
                    icon: Icon(
                      _ob2 ? Icons.visibility_off : Icons.visibility,
                      color: Colors.white,
                    ),
                    onPressed: () => setState(() => _ob2 = !_ob2),
                  ),
                ),
              ),
              spacer(20),
          GradientButton(
            label: _isLoading ? 'Signing up...' : 'Sign up',
            onPressed: () {
              if (_isLoading) return;
              _onSignup();
            },
          )
          ],
          ),
        ),
      ),
    );
  }
}
