import 'dart:convert';

import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kDebugMode, kIsWeb, TargetPlatform;
import 'package:http/http.dart' as http;

class ApiService {
  /// Ghi đè khi cần: `flutter run --dart-define=API_BASE_URL=http://192.168.1.10:8000`
  static const String _envBase = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );

  static String get apiUrl {
    if (kIsWeb && !kDebugMode) {
      return _webReleaseChatUrl();
    }
    if (_envBase.isNotEmpty) {
      final b = _envBase.endsWith('/')
          ? _envBase.substring(0, _envBase.length - 1)
          : _envBase;
      return '$b/chat';
    }
    if (kIsWeb && kDebugMode) {
      // Máy chủ `flutter run` không có /chat → gọi thẳng FastAPI.
      return 'http://localhost:8000/chat';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000/chat';
    }
    return 'http://127.0.0.1:8000/chat';
  }

  /// Web release: Docker/nginx phục vụ app ở :80 và proxy [path]/chat → backend.
  /// Nếu build nhầm `API_BASE_URL=http://localhost:8001` thì browser gọi chéo cổng → CORS / failed to fetch.
  /// Cùng host + scheme nhưng khác cổng với trang → luôn dùng `/chat` (cùng origin).
  static String _webReleaseChatUrl() {
    if (_envBase.isEmpty) {
      return '/chat';
    }
    final root = _envBase.endsWith('/')
        ? _envBase.substring(0, _envBase.length - 1)
        : _envBase;
    Uri apiUri;
    try {
      apiUri = Uri.parse(root);
    } catch (_) {
      return '/chat';
    }
    if (!apiUri.hasScheme || apiUri.host.isEmpty) {
      return '/chat';
    }
    final page = Uri.base;
    if (page.hasScheme &&
        page.host.isNotEmpty &&
        page.scheme == apiUri.scheme &&
        page.host == apiUri.host &&
        page.port != apiUri.port) {
      return '/chat';
    }
    return '$root/chat';
  }

  static Future<Map<String, String>> sendQuestion({
    required String question,
    required String userName,
    required String email,
    required String phone,
  }) async {
    final uri = Uri.parse(apiUrl);
    final res = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'question': question,
        'user_name': userName.trim(),
        'email': email.trim(),
        'phone': phone.trim(),
      }),
    );

    if (res.statusCode != 200) {
      final body = res.body;
      final short = body.length > 280 ? '${body.substring(0, 280)}…' : body;
      throw Exception(
        'Không kết nối được máy chủ (HTTP ${res.statusCode}). '
        'Thử lại sau hoặc xem https://tuyensinh.ctu.edu.vn/ — 0292.3.756.756.\n$short',
      );
    }

    final data = jsonDecode(res.body) as Map<String, dynamic>;
    final answer = (data['answer'] ?? '').toString();
    final moreInfoUrl = (data['more_info_url'] ?? '').toString();

    return {
      'answer': answer.isEmpty ? '(Bot không trả lời được)' : answer,
      'more_info_url': moreInfoUrl,
    };
  }
}
