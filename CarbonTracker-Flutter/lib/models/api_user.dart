class User {
  final int id;
  final String email;
  final String fullName;
  final String role;

  User({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
  });

  factory User.fromJson(Map<String, dynamic> json) => User(
    id: json['id'] as int,
    email: json['email'] as String,
    fullName: json['full_name'] as String,
    role: json['role'] as String,
  );
}

class LoginResult {
  final String accessToken;
  final User user;

  LoginResult({required this.accessToken, required this.user});

  factory LoginResult.fromJson(Map<String, dynamic> json) => LoginResult(
    accessToken: json['access_token'] as String,
    user: User.fromJson(json['user']),
  );
}
