import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/chat_message.dart';
import '../services/api_service.dart';
import 'widgets/chat_bottom_sheets.dart';
import 'widgets/chat_conversation_view.dart';
import 'widgets/chat_welcome_view.dart';

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> with TickerProviderStateMixin {
  final List<ChatMessage> _messages = [];
  final TextEditingController _controller = TextEditingController();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final ScrollController _scroll = ScrollController();

  late AnimationController _fadeController;
  late Animation<double> _fadeAnimation;

  bool _isLoading = false;
  bool _infoSubmitted = false;
  Timer? _noticeTimer;
  OverlayEntry? _noticeEntry;

  void _dismissNotice() {
    _noticeTimer?.cancel();
    _noticeEntry?.remove();
    _noticeEntry = null;
  }

  void _showNotice(String message, {bool isError = true}) {
    final overlay = Overlay.of(context);

    _dismissNotice();

    final bgColor = isError ? const Color(0xFFFFF7E8) : const Color(0xFFF2F8FF);
    final fgColor = isError ? const Color(0xFF8A5A00) : const Color(0xFF004FC0);
    final borderColor = isError
        ? const Color(0xFFFFD98A)
        : const Color(0xFFBBD4FF);
    final icon = isError
        ? Icons.warning_amber_rounded
        : Icons.check_circle_outline_rounded;

    _noticeEntry = OverlayEntry(
      builder: (context) {
        final topInset = MediaQuery.of(context).padding.top + 12;
        return Positioned(
          top: topInset,
          left: 12,
          right: 12,
          child: IgnorePointer(
            ignoring: false,
            child: Center(
              child: Material(
                color: Colors.transparent,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 560),
                  child: Container(
                    decoration: BoxDecoration(
                      color: bgColor,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: borderColor),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(
                            0xFF004FC0,
                          ).withValues(alpha: 0.12),
                          blurRadius: 14,
                          offset: const Offset(0, 6),
                        ),
                      ],
                    ),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    child: Row(
                      children: [
                        Icon(icon, color: fgColor, size: 20),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            message,
                            style: TextStyle(
                              color: fgColor,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        IconButton(
                          onPressed: _dismissNotice,
                          splashRadius: 18,
                          icon: Icon(
                            Icons.close_rounded,
                            color: fgColor,
                            size: 18,
                          ),
                          tooltip: 'Đóng',
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );

    overlay.insert(_noticeEntry!);

    _noticeTimer = Timer(const Duration(seconds: 3), () {
      if (mounted) _dismissNotice();
    });
  }

  // Quick questions mẫu
  final List<String> _quickQuestions = [
    'Điểm chuẩn 2026 là bao nhiêu?',
    'Học phí ngành Công nghệ thông tin?',
    'Hình thức xét tuyển năm nay?',
    'Cách liên hệ hotline tư vấn?',
  ];

  @override
  void initState() {
    super.initState();
    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _fadeController, curve: Curves.easeInOut),
    );
    _fadeController.forward();
    _loadSavedInfo();
  }

  Future<void> _loadSavedInfo() async {
    final prefs = await SharedPreferences.getInstance();
    final name = prefs.getString('user_name') ?? '';
    final email = prefs.getString('user_email') ?? '';
    final phone = prefs.getString('user_phone') ?? '';

    if (name.isNotEmpty && email.isNotEmpty && phone.isNotEmpty && mounted) {
      setState(() {
        _nameController.text = name;
        _emailController.text = email;
        _phoneController.text = phone;
        _infoSubmitted = true;
        _messages.add(
          ChatMessage(
            text: 'Chào mừng $name quay trở lại! Bạn cần hỗ trợ gì thêm không?',
            isUser: false,
          ),
        );
      });
      Future.delayed(const Duration(milliseconds: 100), _scrollToBottom);
    }
  }

  @override
  void dispose() {
    _dismissNotice();
    _controller.dispose();
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _scroll.dispose();
    _fadeController.dispose();
    super.dispose();
  }

  Future<void> _scrollToBottom() async {
    await Future<void>.delayed(const Duration(milliseconds: 50));
    if (!_scroll.hasClients) return;
    await _scroll.animateTo(
      _scroll.position.maxScrollExtent,
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeOut,
    );
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _isLoading) return;

    setState(() {
      _messages.add(ChatMessage(text: text, isUser: true));
      _isLoading = true;
      _controller.clear();
    });
    await _scrollToBottom();

    try {
      final response = await ApiService.sendQuestion(
        question: text,
        userName: _nameController.text.trim(),
        email: _emailController.text.trim(),
        phone: _phoneController.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _messages.add(
          ChatMessage(
            text: response['answer']!,
            isUser: false,
            infoUrl: response['more_info_url']?.isEmpty ?? true
                ? null
                : response['more_info_url'],
          ),
        );
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _messages.add(ChatMessage(text: 'Lỗi gọi API: $e', isUser: false));
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
        await _scrollToBottom();
      }
    }
  }

  bool _isValidName(String name) {
    // Chấp nhận chữ cái tiếng Việt, khoảng trắng và một số ký tự tên phổ biến.
    final nameRegex = RegExp(r"^[A-Za-zÀ-ỹ\s'.-]{2,60}$");
    return nameRegex.hasMatch(name) &&
        name.trim().split(RegExp(r"\s+")).length >= 2;
  }

  bool _isValidPhone(String phone) {
    // Hỗ trợ định dạng nội địa 0xxxxxxxxx hoặc quốc tế +84xxxxxxxxx.
    final phoneRegex = RegExp(r'^(0\d{9}|\+84\d{9})$');
    return phoneRegex.hasMatch(phone);
  }

  bool _isValidEmail(String email) {
    final emailRegex = RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$');
    return emailRegex.hasMatch(email);
  }

  void _submitInfo() {
    final name = _nameController.text.trim();
    final email = _emailController.text.trim();
    final phone = _phoneController.text.trim();

    if (name.isEmpty || email.isEmpty || phone.isEmpty) {
      _showNotice('Vui lòng điền đầy đủ thông tin');
      return;
    }

    if (!_isValidName(name)) {
      _showNotice('Họ và tên không hợp lệ');
      return;
    }

    if (!_isValidPhone(phone)) {
      _showNotice(
        'Số điện thoại không hợp lệ (vd: 0912345678 hoặc +84912345678)',
      );
      return;
    }

    if (!_isValidEmail(email)) {
      _showNotice('Email không hợp lệ');
      return;
    }

    setState(() {
      _infoSubmitted = true;
      final greeting = 'Xin chào $name, bạn cần giúp gì?';
      _messages.add(ChatMessage(text: greeting, isUser: false));
    });

    SharedPreferences.getInstance().then((prefs) {
      prefs.setString('user_name', name);
      prefs.setString('user_email', email);
      prefs.setString('user_phone', phone);
    });

    Navigator.pop(context); // Đóng modal
    Future.delayed(const Duration(milliseconds: 100), _scrollToBottom);
  }

  void _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('user_name');
    await prefs.remove('user_email');
    await prefs.remove('user_phone');

    if (mounted) {
      setState(() {
        _infoSubmitted = false;
        _messages.clear();
        _nameController.clear();
        _emailController.clear();
        _phoneController.clear();
      });
    }
  }

  void _showInfoForm() {
    showInfoFormSheet(
      context: context,
      nameController: _nameController,
      phoneController: _phoneController,
      emailController: _emailController,
      onSubmit: _submitInfo,
    );
  }

  void _showInfoScreen() {
    showContactInfoSheet(context);
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final isDesktop = width >= 1024;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Chatbot Tư vấn Tuyển sinh CTU'),
        titleSpacing: isDesktop ? 0 : null,
        centerTitle: true,
        actions: _infoSubmitted
            ? [
                IconButton(
                  icon: const Icon(Icons.info_outline),
                  onPressed: _showInfoScreen,
                  tooltip: 'Thông tin liên hệ',
                ),
                IconButton(
                  icon: const Icon(Icons.logout),
                  onPressed: _logout,
                  tooltip: 'Đăng xuất',
                ),
              ]
            : [],
      ),
      body: _infoSubmitted
          ? ChatConversationView(
              messages: _messages,
              scrollController: _scroll,
              inputController: _controller,
              isLoading: _isLoading,
              onSend: _send,
            )
          : ChatWelcomeView(
              fadeAnimation: _fadeAnimation,
              fadeController: _fadeController,
              quickQuestions: _quickQuestions,
              onQuickQuestionTap: (q) {
                _controller.text = q;
                _showInfoForm();
              },
            ),
      floatingActionButton: !_infoSubmitted
          ? FloatingActionButton(
              onPressed: _showInfoForm,
              tooltip: 'Bắt đầu chat',
              child: const Icon(Icons.chat_bubble),
            )
          : null,
    );
  }
}
