import 'package:flutter/material.dart';

class InputBar extends StatefulWidget {
  final TextEditingController controller;
  final bool isLoading;
  final VoidCallback onSend;

  const InputBar({
    required this.controller,
    required this.isLoading,
    required this.onSend,
    super.key,
  });

  @override
  State<InputBar> createState() => _InputBarState();
}

class _InputBarState extends State<InputBar>
    with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _scaleAnimation;
  bool _isFocused = false;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 1.05).animate(
      CurvedAnimation(parent: _animController, curve: Curves.easeInOut),
    );
    widget.controller.addListener(_onTextChanged);
  }

  void _onTextChanged() {
    if (!mounted) return;
    if (widget.controller.text.isNotEmpty && !_isFocused) {
      _animController.forward();
      _isFocused = true;
    } else if (widget.controller.text.isEmpty && _isFocused) {
      _animController.reverse();
      _isFocused = false;
    }
  }

  @override
  void didUpdateWidget(InputBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller != widget.controller) {
      oldWidget.controller.removeListener(_onTextChanged);
      widget.controller.addListener(_onTextChanged);
    }
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onTextChanged);
    _animController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Colors.white.withOpacity(0.9),
              Colors.white.withOpacity(0.95),
            ],
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF004FC0).withOpacity(0.1),
              blurRadius: 12,
              offset: const Offset(0, -4),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
          child: Row(
            children: [
              Expanded(
                child: AnimatedBuilder(
                  animation: _scaleAnimation,
                  builder: (context, child) {
                    return Transform.scale(
                      scale: _scaleAnimation.value,
                      child: Container(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(12),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF004FC0).withOpacity(0.15),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: TextField(
                          controller: widget.controller,
                          enabled: !widget.isLoading,
                          textInputAction: TextInputAction.send,
                          onSubmitted: (_) => widget.onSend(),
                          decoration: InputDecoration(
                            hintText: 'Nhập câu hỏi...',
                            hintStyle: TextStyle(
                              color: Colors.grey[400],
                              fontSize: 15,
                            ),
                            filled: true,
                            fillColor: Colors.white,
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: const BorderSide(
                                color: Color(0xFFFFD700),
                                width: 2,
                              ),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(
                                color: Colors.grey[300]!,
                                width: 1.5,
                              ),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: const BorderSide(
                                color: Color(0xFF004FC0),
                                width: 2,
                              ),
                            ),
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 14,
                            ),
                            isDense: true,
                          ),
                          style: const TextStyle(
                            fontSize: 15,
                            color: Color(0xFF001A33),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(width: 10),
              ScaleTransition(
                scale: Tween<double>(begin: 1.0, end: 1.1).animate(
                  CurvedAnimation(
                    parent: _animController,
                    curve: Curves.elasticOut,
                  ),
                ),
                child: FilledButton(
                  onPressed: widget.isLoading ? null : widget.onSend,
                  style: FilledButton.styleFrom(
                    backgroundColor: widget.isLoading
                        ? Colors.grey[300]
                        : const Color(0xFFFFD700),
                    foregroundColor: const Color(0xFF001A33),
                    disabledBackgroundColor: Colors.grey[300],
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 12,
                    ),
                    elevation: 4,
                  ),
                  child: widget.isLoading
                      ? SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              Colors.grey[600]!,
                            ),
                          ),
                        )
                      : const Icon(Icons.send_rounded, size: 20),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
