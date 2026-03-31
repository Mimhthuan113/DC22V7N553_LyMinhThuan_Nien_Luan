import 'package:flutter/material.dart';
import 'screens/chat_page.dart';

void main() {
  runApp(const ChatbotApp());
}

class ChatbotApp extends StatelessWidget {
  const ChatbotApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Chatbot Tư vấn Tuyển sinh CTU',
      theme: ThemeData(
        // Màu chủ đạo từ website CTU: Xanh dương đậm + Vàng cam
        useMaterial3: true,
        colorScheme: const ColorScheme(
          brightness: Brightness.light,
          primary: Color(0xFF004FC0), // Xanh dương đậm (CTU chính)
          onPrimary: Colors.white,
          secondary: Color(0xFFFFD700), // Vàng cam sáng (accent)
          onSecondary: Color(0xFF001A33), // Xanh sẫm
          surface: Colors.white,
          onSurface: Color(0xFF001A33),
          error: Color(0xFFFF4D4D),
          onError: Colors.white,
          outline: Color(0xFFE0E8FF),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF004FC0),
          foregroundColor: Colors.white,
          elevation: 0,
          centerTitle: true,
        ),
        floatingActionButtonTheme: const FloatingActionButtonThemeData(
          backgroundColor: Color(0xFFFFD700),
          foregroundColor: Color(0xFF001A33),
          elevation: 8,
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            backgroundColor: const Color(0xFFFFD700),
            foregroundColor: const Color(0xFF001A33),
            elevation: 4,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            side: const BorderSide(color: Color(0xFF004FC0), width: 2),
            foregroundColor: const Color(0xFF004FC0),
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
      ),
      home: const ChatPage(),
    );
  }
}
