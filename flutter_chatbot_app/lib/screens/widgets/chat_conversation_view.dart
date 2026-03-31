import 'package:flutter/material.dart';

import '../../models/chat_message.dart';
import '../../widgets/chat_bubble.dart';
import '../../widgets/input_bar.dart';

class ChatConversationView extends StatelessWidget {
  const ChatConversationView({
    super.key,
    required this.messages,
    required this.scrollController,
    required this.inputController,
    required this.isLoading,
    required this.onSend,
  });

  final List<ChatMessage> messages;
  final ScrollController scrollController;
  final TextEditingController inputController;
  final bool isLoading;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final containerWidth = width >= 1280
        ? 980.0
        : width >= 900
        ? 860.0
        : width >= 600
        ? 720.0
        : width;

    return Column(
      children: [
        Expanded(
          child: Center(
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: containerWidth),
              child: messages.isEmpty
                  ? Center(
                      child: Text(
                        'Hãy bắt đầu cuộc tư vấn',
                        style: TextStyle(color: Colors.grey[400], fontSize: 16),
                      ),
                    )
                  : ListView.builder(
                      controller: scrollController,
                      padding: EdgeInsets.symmetric(
                        horizontal: width >= 900 ? 20 : 12,
                        vertical: 12,
                      ),
                      itemCount: messages.length,
                      itemBuilder: (context, index) {
                        final msg = messages[index];
                        return ChatBubble(
                          text: msg.text,
                          isUser: msg.isUser,
                          infoUrl: msg.infoUrl,
                        );
                      },
                    ),
            ),
          ),
        ),
        if (isLoading)
          Center(
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: containerWidth),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  vertical: 12,
                  horizontal: 16,
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _dot(),
                    _dot(),
                    _dot(),
                    const SizedBox(width: 8),
                    Text(
                      'AI đang soạn tin...',
                      style: TextStyle(color: Colors.grey[600], fontSize: 13),
                    ),
                  ],
                ),
              ),
            ),
          ),
        Center(
          child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: containerWidth),
            child: InputBar(
              controller: inputController,
              isLoading: isLoading,
              onSend: onSend,
            ),
          ),
        ),
      ],
    );
  }

  Widget _dot() {
    return Container(
      width: 8,
      height: 8,
      margin: const EdgeInsets.symmetric(horizontal: 2),
      decoration: BoxDecoration(
        color: Colors.grey[400],
        shape: BoxShape.circle,
      ),
    );
  }
}
