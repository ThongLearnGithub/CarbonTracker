import 'package:firebase_auth/firebase_auth.dart' as firebase_auth;
import 'package:flutter/foundation.dart';

import '../models/api_user.dart';
import 'api_service.dart';

class AuthFlowException implements Exception {
  final String message;
  final bool requiresEmailVerification;

  const AuthFlowException(
    this.message, {
    this.requiresEmailVerification = false,
  });

  @override
  String toString() => message;
}

class AuthService {
  AuthService({
    firebase_auth.FirebaseAuth? firebaseAuth,
    ApiService? apiService,
  })  : _firebaseAuth = firebaseAuth,
        _apiService = apiService ?? ApiService();

  final firebase_auth.FirebaseAuth? _firebaseAuth;
  final ApiService _apiService;

  firebase_auth.FirebaseAuth get _auth =>
      _firebaseAuth ?? firebase_auth.FirebaseAuth.instance;

  Future<void> signUpWithEmail({
    required String name,
    required String email,
    required String password,
  }) async {
    try {
      final credential = await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );
      final user = credential.user;
      if (user == null) {
        throw const AuthFlowException('Firebase did not return a user.');
      }

      await user.updateDisplayName(name);
      await user.sendEmailVerification();
      await _auth.signOut();
    } on firebase_auth.FirebaseAuthException catch (error) {
      throw AuthFlowException(_messageForFirebaseError(error));
    }
  }

  Future<LoginResult> signInWithEmail({
    required String email,
    required String password,
  }) async {
    try {
      final credential = await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );
      final user = credential.user;
      if (user == null) {
        throw const AuthFlowException('Firebase did not return a user.');
      }
      return await _completeSignIn(user);
    } on firebase_auth.FirebaseAuthException catch (error) {
      throw AuthFlowException(_messageForFirebaseError(error));
    }
  }

  Future<LoginResult> signInWithGoogle() async {
    try {
      final provider = firebase_auth.GoogleAuthProvider();
      if (kIsWeb) {
        provider.setCustomParameters({'prompt': 'select_account'});
      }
      final credential = kIsWeb
          ? await _auth.signInWithPopup(provider)
          : await _auth.signInWithProvider(provider);
      final user = credential.user;
      if (user == null) {
        throw const AuthFlowException('Google sign-in did not return a user.');
      }
      return await _completeSignIn(user);
    } on firebase_auth.FirebaseAuthException catch (error) {
      throw AuthFlowException(_messageForFirebaseError(error));
    }
  }

  Future<void> signOut() => _auth.signOut();

  Future<LoginResult> completePendingEmailSignIn() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const AuthFlowException(
        'Your sign-in session expired. Please enter your email and password again.',
      );
    }
    return _completeSignIn(user);
  }

  Future<bool> resendEmailVerification() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const AuthFlowException(
        'The sign-in session expired. Please log in again.',
      );
    }

    try {
      await user.reload();
      final currentUser = _auth.currentUser;
      if (currentUser == null) {
        throw const AuthFlowException(
          'The sign-in session expired. Please log in again.',
        );
      }
      if (currentUser.emailVerified) return true;

      await currentUser.sendEmailVerification();
      return false;
    } on firebase_auth.FirebaseAuthException catch (error) {
      throw AuthFlowException(_messageForFirebaseError(error));
    }
  }

  Future<LoginResult> _completeSignIn(firebase_auth.User user) async {
    await user.reload();
    final currentUser = _auth.currentUser;
    if (currentUser == null) {
      throw const AuthFlowException('The sign-in session is no longer active.');
    }
    if (!currentUser.emailVerified) {
      throw const AuthFlowException(
        'This email is not verified yet. Check your inbox for the verification link, or use Resend verification link below.',
        requiresEmailVerification: true,
      );
    }

    final idToken = await currentUser.getIdToken(true);
    if (idToken == null) {
      throw const AuthFlowException('Firebase did not return an ID token.');
    }
    return _apiService.loginWithFirebase(idToken);
  }

  String _messageForFirebaseError(firebase_auth.FirebaseAuthException error) {
    final errorMessage = error.message?.toLowerCase() ?? '';
    if (errorMessage.contains('blocked all requests from this device') ||
        errorMessage.contains('unusual activity')) {
      return 'Firebase temporarily blocked sign-in requests from this device. Stop retrying and try again later. This is a Firebase security restriction, not an incorrect password or app database error.';
    }

    switch (error.code) {
      case 'email-already-in-use':
        return 'An account already exists for this email. Please log in.';
      case 'weak-password':
        return 'Choose a stronger password (at least 6 characters).';
      case 'invalid-email':
        return 'Please enter a valid email address.';
      case 'user-not-found':
        return 'No Firebase account was found. Sign up with this email first; verified accounts can be linked to existing app data.';
      case 'wrong-password':
      case 'invalid-credential':
        return 'The email or password is incorrect.';
      case 'too-many-requests':
        return 'Firebase temporarily blocked sign-in after too many attempts. Wait before trying again; repeated retries may extend the block.';
      case 'quota-exceeded':
        return 'Firebase Authentication has reached a request limit. Try again later or check the Firebase project limits.';
      case 'network-request-failed':
        return 'Could not connect to Firebase. Check your internet connection.';
      case 'popup-closed-by-user':
      case 'cancelled-popup-request':
        return 'Google sign-in was cancelled.';
      default:
        return error.message ?? 'Authentication failed. Please try again.';
    }
  }
}
