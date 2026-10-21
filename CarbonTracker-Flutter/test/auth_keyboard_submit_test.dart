import 'package:carbon_credits_app/screens/login.dart';
import 'package:carbon_credits_app/screens/signup.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('Enter on login password submits the login form', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: LoginScreen()));

    await tester.enterText(find.byType(TextField).at(0), 'user@example.com');
    await tester.tap(find.byType(TextField).at(1));
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();

    expect(find.text('Please enter email and password.'), findsOneWidget);
  });

  testWidgets('login form stays readable on wide browser screens', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const MaterialApp(home: LoginScreen()));

    expect(tester.getSize(find.byType(TextField).first).width,
        lessThanOrEqualTo(520));
  });

  testWidgets('Enter on signup confirmation submits the signup form', (
    tester,
  ) async {
    await tester.pumpWidget(const MaterialApp(home: SignupScreen()));

    await tester.tap(find.byType(TextField).at(3));
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();

    expect(find.text('Please fill in all fields'), findsOneWidget);
  });
}
