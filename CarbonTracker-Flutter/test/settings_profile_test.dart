import 'package:carbon_credits_app/models/api_user.dart';
import 'package:carbon_credits_app/screens/settings_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('profile displays the signed-in user', (tester) async {
    final user = User(
      id: 42,
      email: 'thong@example.com',
      fullName: 'Thong Tran',
      role: 'user',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: SettingsPage(user: user),
      ),
    );

    expect(find.text('Thong Tran'), findsOneWidget);
    expect(find.text('thong@example.com'), findsOneWidget);
    expect(find.text('TT'), findsOneWidget);
    expect(find.text('Khoa Mai'), findsNothing);
  });
}
