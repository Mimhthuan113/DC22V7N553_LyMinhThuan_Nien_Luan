import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_chatbot_app/main.dart';

void main() {
  Future<void> _openInfoForm(WidgetTester tester) async {
    await tester.tap(find.byIcon(Icons.chat_bubble));
    await tester.pumpAndSettle();
    expect(find.text('Thông tin của bạn'), findsOneWidget);
  }

  testWidgets('Validate: thieu thong tin', (WidgetTester tester) async {
    await tester.pumpWidget(const ChatbotApp());
    await _openInfoForm(tester);

    await tester.tap(find.widgetWithText(FilledButton, 'Bắt đầu chat'));
    await tester.pump();

    expect(find.text('Vui lòng điền đầy đủ thông tin'), findsOneWidget);
  });

  testWidgets('Validate: ten khong hop le', (WidgetTester tester) async {
    await tester.pumpWidget(const ChatbotApp());
    await _openInfoForm(tester);

    await tester.enterText(find.byType(TextField).at(0), 'A1');
    await tester.enterText(find.byType(TextField).at(1), '0912345678');
    await tester.enterText(find.byType(TextField).at(2), 'a@test.com');
    await tester.tap(find.widgetWithText(FilledButton, 'Bắt đầu chat'));
    await tester.pump();

    expect(find.text('Họ và tên không hợp lệ'), findsOneWidget);
  });

  testWidgets('Validate: sdt khong hop le', (WidgetTester tester) async {
    await tester.pumpWidget(const ChatbotApp());
    await _openInfoForm(tester);

    await tester.enterText(find.byType(TextField).at(0), 'Nguyen Van A');
    await tester.enterText(find.byType(TextField).at(1), '12345');
    await tester.enterText(find.byType(TextField).at(2), 'a@test.com');
    await tester.tap(find.widgetWithText(FilledButton, 'Bắt đầu chat'));
    await tester.pump();

    expect(find.textContaining('Số điện thoại không hợp lệ'), findsOneWidget);
  });

  testWidgets('Validate: email khong hop le', (WidgetTester tester) async {
    await tester.pumpWidget(const ChatbotApp());
    await _openInfoForm(tester);

    await tester.enterText(find.byType(TextField).at(0), 'Nguyen Van A');
    await tester.enterText(find.byType(TextField).at(1), '0912345678');
    await tester.enterText(find.byType(TextField).at(2), 'abc');
    await tester.tap(find.widgetWithText(FilledButton, 'Bắt đầu chat'));
    await tester.pump();

    expect(find.text('Email không hợp lệ'), findsOneWidget);
  });

  testWidgets('Nhap dung thong tin thi vao chat', (WidgetTester tester) async {
    await tester.pumpWidget(const ChatbotApp());
    await _openInfoForm(tester);

    await tester.enterText(find.byType(TextField).at(0), 'Nguyen Van A');
    await tester.enterText(find.byType(TextField).at(1), '0912345678');
    await tester.enterText(find.byType(TextField).at(2), 'a@test.com');
    await tester.tap(find.widgetWithText(FilledButton, 'Bắt đầu chat'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Xin chào Nguyen Van A'), findsOneWidget);
    expect(find.byType(FloatingActionButton), findsNothing);
  });
}
