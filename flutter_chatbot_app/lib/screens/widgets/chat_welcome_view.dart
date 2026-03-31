import 'package:flutter/material.dart';

class ChatWelcomeView extends StatelessWidget {
  const ChatWelcomeView({
    super.key,
    required this.fadeAnimation,
    required this.fadeController,
    required this.quickQuestions,
    required this.onQuickQuestionTap,
  });

  final Animation<double> fadeAnimation;
  final AnimationController fadeController;
  final List<String> quickQuestions;
  final ValueChanged<String> onQuickQuestionTap;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;

    return FadeTransition(
      opacity: fadeAnimation,
      child: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.white, Color(0xFFF5F9FF), Color(0xFFEEF5FF)],
          ),
        ),
        child: SingleChildScrollView(
          child: Center(
            child: Padding(
              padding: EdgeInsets.symmetric(
                horizontal: width >= 900 ? 40 : 24,
                vertical: 24,
              ),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 860),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(height: 40),
                    ScaleTransition(
                      scale: Tween<double>(begin: 0.5, end: 1.0).animate(
                        CurvedAnimation(
                          parent: fadeController,
                          curve: Curves.elasticOut,
                        ),
                      ),
                      child: SizedBox(
                        width: 120,
                        height: 120,
                        child: Image.asset(
                          'assets/images/logo-ctu.png',
                          fit: BoxFit.contain, // Không bị tràn hay méo
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    SlideTransition(
                      position:
                          Tween<Offset>(
                            begin: const Offset(0, 0.3),
                            end: Offset.zero,
                          ).animate(
                            CurvedAnimation(
                              parent: fadeController,
                              curve: const Interval(0.2, 0.8),
                            ),
                          ),
                      child: const Text(
                        'Tư vấn Tuyển sinh 2026',
                        style: TextStyle(
                          fontSize: 30,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF004FC0),
                          letterSpacing: 0.5,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Trường Đại học Cần Thơ',
                      style: TextStyle(
                        fontSize: 16,
                        color: Colors.grey[700],
                        fontWeight: FontWeight.w500,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 40),
                    const Text(
                      'Câu hỏi thường gặp',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF001A33),
                        letterSpacing: 0.3,
                      ),
                    ),
                    const SizedBox(height: 16),
                    ...quickQuestions.asMap().entries.map((entry) {
                      final idx = entry.key;
                      final q = entry.value;
                      return SlideTransition(
                        position:
                            Tween<Offset>(
                              begin: const Offset(-0.5, 0),
                              end: Offset.zero,
                            ).animate(
                              CurvedAnimation(
                                parent: fadeController,
                                curve: Interval(
                                  (0.1 + (idx * 0.15)).clamp(0.0, 1.0),
                                  (0.7 + (idx * 0.15)).clamp(0.0, 1.0),
                                  curve: Curves.easeOut,
                                ),
                              ),
                            ),
                        child: Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: SizedBox(
                            width: double.infinity,
                            child: MouseRegion(
                              cursor: SystemMouseCursors.click,
                              child: OutlinedButton(
                                onPressed: () => onQuickQuestionTap(q),
                                style: OutlinedButton.styleFrom(
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 14,
                                  ),
                                  side: const BorderSide(
                                    color: Color(0xFF004FC0),
                                    width: 2,
                                  ),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                ),
                                child: Text(
                                  q,
                                  style: const TextStyle(
                                    color: Color(0xFF004FC0),
                                    fontSize: 14,
                                    fontWeight: FontWeight.w500,
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                              ),
                            ),
                          ),
                        ),
                      );
                    }),
                    const SizedBox(height: 40),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
